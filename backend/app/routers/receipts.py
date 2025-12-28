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
from app.services.normalization import normalize_product_name, classify_product_category, normalize_unit
from app.config import settings
from app.schemas import ReceiptResponse, ReceiptListResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Upload directory - ensure it exists
upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)


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
        status="processing",  # Set initial status
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
            db.commit()  # Save OCR text to database
            await send_update("ocr", 50, "OCR completed, text extracted")
            
            # Log OCR result for debugging
            logger.info(f"Receipt {receipt_id}: OCR extracted {len(ocr_result.text)} characters")
            if not ocr_result.text or not ocr_result.text.strip():
                logger.warning(f"Receipt {receipt_id}: OCR text is empty or whitespace only")
                await send_update("error", 0, "OCR Failed", error="No text extracted from receipt")
                return

            # Step 2: Hybrid Parsing (Regex + LLM)
            await send_update("llm", 60, "Analyzing with AI & Normalizers...")
            logger.info(f"Receipt {receipt_id}: Starting Hybrid parsing...")

            # 2a. Run Regex Parser for precision (Dates, Totals, Normalized Items)
            from app.services.receipt_parser import ReceiptParser
            parser = ReceiptParser()
            # Pass 0 as dummy shop_id, we'll confirm it with LLM
            parsed_regex = parser.parse(ocr_result.text, shop_id=0)

            # 2b. Run LLM for semantic understanding (Shop Name, Categories, tricky layouts)
            parsed_llm = parse_receipt_text(ocr_result.text)

            if parsed_llm.error and not parsed_regex.items:
                 # Both failed
                error_msg = f"Analysis Error: {parsed_llm.error}"
                logger.error(f"Receipt {receipt_id}: {error_msg}")
                receipt.ocr_text = f"{receipt.ocr_text}\n\n{error_msg}"
                receipt.status = "error"
                db.commit()
                await send_update("error", 0, "AI Analysis Failed", error=parsed_llm.error)
                return

            await send_update("llm", 80, "Analysis complete, merging results...")
            
            # Step 3: Save to database (Merge Strategy)
            await send_update("saving", 90, "Saving normalized data...")

            # Shop: Trust LLM first (Regex can't catch "Biedronka" easily from logo text), fallback to default
            shop_name = parsed_llm.shop if parsed_llm.shop else "Nieznany Sklep"
            
            # Get or create shop
            shop = db.query(Shop).filter(Shop.name == shop_name).first()
            if not shop:
                shop = Shop(name=shop_name)
                db.add(shop)
                db.flush()
                logger.info(f"Receipt {receipt_id}: Created new shop: {shop.name}")

            # Update receipt
            receipt.shop_id = shop.id
            
            # Date: Trust Regex (Precise) > LLM > Today
            if parsed_regex.purchase_date and parsed_regex.purchase_date != date.today():
                 receipt.purchase_date = parsed_regex.purchase_date
            else:
                try:
                    receipt.purchase_date = datetime.strptime(parsed_llm.date, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    receipt.purchase_date = date.today()

            receipt.purchase_time = parsed_llm.time
            
            # Total: Trust Regex (Precise) > LLM
            if parsed_regex.total_amount > 0:
                receipt.total_amount = parsed_regex.total_amount
            else:
                receipt.total_amount = parsed_llm.total if parsed_llm.total is not None else 0.0
                
            receipt.subtotal = parsed_llm.subtotal # Regex simplified this, check if we want parser's
            receipt.tax = parsed_llm.tax
            receipt.status = "completed"

            # Items: Prefer Regex items if they captured a good list (checking count/quality)
            # Otherwise fall back to LLM items
            items_source = []
            
            # Simple heuristic: If regex found items with prices that sum up close to total, use them.
            regex_total = sum(i.total_price for i in parsed_regex.items)
            
            if parsed_regex.items and abs(regex_total - receipt.total_amount) < 5.0:
                 # Regex list seems valid and validates against total
                 logger.info(f"Receipt {receipt_id}: Using Regex items (checksum valid)")
                 items_to_process = parsed_regex.items
                 source_type = "regex"
            else:
                 # Fallback to LLM items
                 logger.info(f"Receipt {receipt_id}: Using LLM items (Regex checksum gap: {abs(regex_total - receipt.total_amount)})")
                 # Convert LLM dicts to objects for uniform processing loop below would be nice,
                 # but for now let's just use the LLM dict structure and adapt the loop.
                 items_to_process = parsed_llm.items
                 source_type = "llm"

            # Save items
            for item_data in items_to_process:
                # Handle different data structures (Object vs Dict)
                if source_type == "regex":
                    name = item_data.raw_name
                    qty = item_data.quantity
                    unit = item_data.unit
                    unit_price = item_data.unit_price
                    total_price = item_data.total_price
                else:
                    name = item_data.get("name", "")
                    qty = item_data.get("quantity", 1.0)
                    unit = item_data.get("unit")
                    unit_price = item_data.get("unit_price")
                    total_price = item_data.get("total_price", 0.0)

                # Get or create product
                product = None
                if name:
                    # Normalize unit
                    unit = normalize_unit(unit)
                    
                    # Find or create product using fuzzy matching
                    product, is_new = normalize_product_name(db, name)
                    
                    if is_new:
                        # Auto-classify category for new products
                        cat_id = classify_product_category(db, product)
                        if cat_id:
                            product.category_id = cat_id
                            db.add(product)
                        
                        logger.info(f"Classified new product '{product.normalized_name}' -> Category ID: {cat_id}")

                # Create receipt item
                receipt_item = ReceiptItem(
                    receipt_id=receipt.id,
                    product_id=product.id if product else None,
                    raw_name=name,
                    quantity=qty,
                    unit=unit,
                    unit_price=unit_price,
                    total_price=total_price,
                )
                db.add(receipt_item)
            
            db.commit()

            await send_update("completed", 100, "Processing successfully completed!")
            logger.info(f"Successfully processed receipt {receipt_id}")

        except Exception as e:
            logger.error(f"Error processing receipt {receipt_id}: {e}", exc_info=True)
            try:
                db.rollback()
                # Update receipt with error
                receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
                if receipt:
                    receipt.status = "error"
                    if receipt.ocr_text:
                        receipt.ocr_text = f"{receipt.ocr_text}\n\nProcessing Error: {str(e)}"
                    else:
                        receipt.ocr_text = f"Processing Error: {str(e)}"
                    db.commit()
            except Exception as db_error:
                logger.error(f"Error updating receipt status in error handler: {db_error}")
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
