"""
Receipt API endpoints for upload, processing, and retrieval.
"""

import os
import asyncio
import logging
from typing import List, Optional
from datetime import datetime, date
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.receipt import Receipt, ReceiptItem
from app.models.product import Product, ProductAlias
from app.models.category import Category
from app.models.shop import Shop
from app.dependencies import get_current_user
from app.services.ocr_service import extract_from_pdf, extract_from_image, OCRResult
from app.services.llm_service import parse_receipt_text, ParsedReceipt
from app.config import settings
from app.schemas import ReceiptResponse, ReceiptListResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        # Map receipt_id to list of active websockets
        self.active_connections: dict[int, List[WebSocket]] = {}

    async def connect(self, receipt_id: int, websocket: WebSocket):
        await websocket.accept()
        if receipt_id not in self.active_connections:
            self.active_connections[receipt_id] = []
        self.active_connections[receipt_id].append(websocket)
        logger.info(f"WebSocket connected for receipt {receipt_id}")

    def disconnect(self, receipt_id: int, websocket: WebSocket):
        if receipt_id in self.active_connections:
            if websocket in self.active_connections[receipt_id]:
                self.active_connections[receipt_id].remove(websocket)
            if not self.active_connections[receipt_id]:
                del self.active_connections[receipt_id]
        logger.info(f"WebSocket disconnected for receipt {receipt_id}")

    async def broadcast(self, receipt_id: int, message: dict):
        if receipt_id in self.active_connections:
            for connection in self.active_connections[receipt_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to websocket: {e}")
                    # Consider removing dead connection here


manager = ConnectionManager()


@router.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),  # Require auth
):
    """
    Upload and process a receipt file (PDF or image).

    Returns receipt_id immediately and processes in background.
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    # Validate file size
    file_content = await file.read()
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024} MB",
        )

    # Save uploaded file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = upload_dir / safe_filename

    with open(file_path, "wb") as f:
        f.write(file_content)

    # Create receipt record (will be updated after processing)
    receipt = Receipt(
        shop_id=1,  # Temporary, will be updated after parsing
        purchase_date=date.today(),
        total_amount=0.0,
        source_file=str(file_path),
    )
    db.add(receipt)
    db.flush()  # Get receipt.id
    db.commit()  # Commit to ensure ID is persisted for background task

    # Process receipt in background
    asyncio.create_task(process_receipt_async(receipt.id, str(file_path)))

    return {
        "receipt_id": receipt.id,
        "status": "processing",
        "message": "Receipt uploaded, processing in background",
    }


async def process_receipt_async(receipt_id: int, file_path: str):
    """
    Async task to process receipt: OCR → LLM → Save to database.
    Sends updates via WebSocket.
    """
    from app.database import get_db_context

    # Helper to send updates
    async def send_update(stage: str, progress: int, message: str, error: str = None):
        payload = {
            "type": "update",
            "stage": stage,
            "progress": progress,
            "message": message,
        }
        if error:
            payload["status"] = "error"
            payload["error"] = error

        await manager.broadcast(receipt_id, payload)
        logger.info(f"Receipt {receipt_id} update: {stage} ({progress}%) - {message}")

    with get_db_context() as db:
        try:
            # Wait a brief moment for WS connection to be established by frontend
            await asyncio.sleep(1)

            # Start
            await send_update("uploading", 10, "File uploaded, starting OCR...")

            # Update receipt status
            receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
            if not receipt:
                logger.error(f"Receipt {receipt_id} not found")
                await send_update(
                    "error", 0, "Receipt record not found", error="Receipt not found"
                )
                return

            # Step 1: OCR
            await send_update("ocr", 30, "Extracting text with OCR...")

            if file_path.lower().endswith(".pdf"):
                ocr_result = extract_from_pdf(file_path)
            else:
                ocr_result = extract_from_image(file_path)

            if ocr_result.error:
                receipt.ocr_text = f"OCR Error: {ocr_result.error}"
                db.commit()
                await send_update("error", 0, "OCR Failed", error=ocr_result.error)
                return

            receipt.ocr_text = ocr_result.text
            await send_update("ocr", 50, "OCR completed, text extracted")

            # Step 2: LLM Parsing
            await send_update("llm", 60, "Analyzing with AI (Bielik)...")
            parsed_receipt = parse_receipt_text(ocr_result.text)

            if parsed_receipt.error:
                receipt.ocr_text = f"LLM Error: {parsed_receipt.error}"
                db.commit()
                await send_update(
                    "error", 0, "AI Analysis Failed", error=parsed_receipt.error
                )
                return

            await send_update("llm", 80, "AI analysis complete")

            # Step 3: Save to database
            await send_update("saving", 90, "Saving data...")

            # Get or create shop
            shop = db.query(Shop).filter(Shop.name == parsed_receipt.shop).first()
            if not shop:
                shop = Shop(name=parsed_receipt.shop)
                db.add(shop)
                db.flush()

            # Update receipt
            receipt.shop_id = shop.id
            receipt.purchase_date = datetime.strptime(
                parsed_receipt.date, "%Y-%m-%d"
            ).date()
            receipt.purchase_time = parsed_receipt.time
            receipt.total_amount = parsed_receipt.total
            receipt.subtotal = parsed_receipt.subtotal
            receipt.tax = parsed_receipt.tax

            # Save items
            for item_data in parsed_receipt.items:
                # Get or create product
                product = None
                if item_data.get("name"):
                    # Try to find by alias first
                    alias = (
                        db.query(ProductAlias)
                        .filter(ProductAlias.raw_name == item_data["name"])
                        .first()
                    )

                    if alias:
                        product = alias.product
                    else:
                        # Create new product (simplified - in production, use normalization)
                        product = Product(normalized_name=item_data["name"])
                        db.add(product)
                        db.flush()

                        # Create alias
                        alias = ProductAlias(
                            product_id=product.id,
                            raw_name=item_data["name"],
                        )
                        db.add(alias)

                # Create receipt item
                receipt_item = ReceiptItem(
                    receipt_id=receipt.id,
                    product_id=product.id if product else None,
                    raw_name=item_data.get("name", ""),
                    quantity=item_data.get("quantity", 1.0),
                    unit=item_data.get("unit"),
                    unit_price=item_data.get("unit_price"),
                    total_price=item_data.get("total_price", 0.0),
                )
                db.add(receipt_item)

            db.commit()

            await send_update("completed", 100, "Processing successfully completed!")
            logger.info(f"Successfully processed receipt {receipt_id}")

        except Exception as e:
            logger.error(f"Error processing receipt {receipt_id}: {e}")
            db.rollback()
            # Update receipt with error
            receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
            if receipt:
                receipt.ocr_text = f"Processing Error: {str(e)}"
                db.commit()
            await send_update("error", 0, "Unexpected Error", error=str(e))


@router.get("", response_model=ReceiptListResponse)
async def list_receipts(
    skip: int = 0,
    limit: int = 50,
    shop_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    List receipts with optional filters.
    """
    query = db.query(Receipt)

    if shop_id:
        query = query.filter(Receipt.shop_id == shop_id)
    if start_date:
        query = query.filter(Receipt.purchase_date >= start_date)
    if end_date:
        query = query.filter(Receipt.purchase_date <= end_date)

    receipts = (
        query.order_by(desc(Receipt.purchase_date)).offset(skip).limit(limit).all()
    )
    total = query.count()

    return {
        "receipts": receipts,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get receipt details with items.
    """
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()

    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Receipt {receipt_id} not found",
        )

    return receipt


@router.websocket("/ws/processing/{receipt_id}")
async def websocket_processing(websocket: WebSocket, receipt_id: int):
    """
    WebSocket endpoint for real-time processing updates.
    """
    await manager.connect(receipt_id, websocket)

    try:
        # Send initial message
        await websocket.send_json(
            {
                "type": "connected",
                "receipt_id": receipt_id,
                "message": "Connected to real-time updates",
            }
        )

        # Keep connection alive
        while True:
            # We just listen for pings, but mainly this loop keeps the socket open
            # for server-sent events
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(receipt_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for receipt {receipt_id}: {e}")
        manager.disconnect(receipt_id, websocket)
