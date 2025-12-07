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
from app.services.ocr_service import extract_from_pdf, extract_from_image, OCRResult
from app.services.llm_service import parse_receipt_text, ParsedReceipt
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Create upload directory if it doesn't exist
upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
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
    
    # Process receipt in background
    # Note: In production, use a proper task queue (Celery, RQ, etc.)
    asyncio.create_task(process_receipt_async(receipt.id, str(file_path)))
    
    return {
        "receipt_id": receipt.id,
        "status": "processing",
        "message": "Receipt uploaded, processing in background",
    }


async def process_receipt_async(receipt_id: int, file_path: str):
    """
    Async task to process receipt: OCR → LLM → Save to database.
    """
    from app.database import get_db_context
    
    with get_db_context() as db:
        try:
            # Update receipt status
            receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return
        
        # Step 1: OCR
        logger.info(f"Processing OCR for receipt {receipt_id}")
        if file_path.lower().endswith(".pdf"):
            ocr_result = extract_from_pdf(file_path)
        else:
            ocr_result = extract_from_image(file_path)
        
        if ocr_result.error:
            receipt.ocr_text = f"OCR Error: {ocr_result.error}"
            db.commit()
            return
        
        receipt.ocr_text = ocr_result.text
        
        # Step 2: LLM Parsing
        logger.info(f"Parsing receipt {receipt_id} with LLM")
        parsed_receipt = parse_receipt_text(ocr_result.text)
        
        if parsed_receipt.error:
            receipt.ocr_text = f"LLM Error: {parsed_receipt.error}"
            db.commit()
            return
        
        # Step 3: Save to database
        # Get or create shop
        shop = db.query(Shop).filter(Shop.name == parsed_receipt.shop).first()
        if not shop:
            shop = Shop(name=parsed_receipt.shop)
            db.add(shop)
            db.flush()
        
        # Update receipt
        receipt.shop_id = shop.id
        receipt.purchase_date = datetime.strptime(parsed_receipt.date, "%Y-%m-%d").date()
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
                alias = db.query(ProductAlias).filter(
                    ProductAlias.raw_name == item_data["name"]
                ).first()
                
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
            logger.info(f"Successfully processed receipt {receipt_id}")
            
        except Exception as e:
            logger.error(f"Error processing receipt {receipt_id}: {e}")
            db.rollback()
            # Update receipt with error
            receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
            if receipt:
                receipt.ocr_text = f"Processing Error: {str(e)}"
                db.commit()


@router.get("")
async def list_receipts(
    skip: int = 0,
    limit: int = 50,
    shop_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
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
    
    receipts = query.order_by(desc(Receipt.purchase_date)).offset(skip).limit(limit).all()
    total = query.count()
    
    return {
        "receipts": [
            {
                "id": r.id,
                "shop": r.shop.name if r.shop else None,
                "purchase_date": r.purchase_date.isoformat() if r.purchase_date else None,
                "purchase_time": r.purchase_time,
                "total_amount": float(r.total_amount) if r.total_amount else 0.0,
                "items_count": len(r.items),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in receipts
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{receipt_id}")
async def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
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
    
    return {
        "id": receipt.id,
        "shop": {
            "id": receipt.shop.id if receipt.shop else None,
            "name": receipt.shop.name if receipt.shop else None,
            "location": receipt.shop.location if receipt.shop else None,
        },
        "purchase_date": receipt.purchase_date.isoformat() if receipt.purchase_date else None,
        "purchase_time": receipt.purchase_time,
        "total_amount": float(receipt.total_amount) if receipt.total_amount else 0.0,
        "subtotal": float(receipt.subtotal) if receipt.subtotal else None,
        "tax": float(receipt.tax) if receipt.tax else None,
        "items": [
            {
                "id": item.id,
                "product": {
                    "id": item.product.id if item.product else None,
                    "name": item.product.normalized_name if item.product else None,
                },
                "raw_name": item.raw_name,
                "quantity": float(item.quantity) if item.quantity else 0.0,
                "unit": item.unit,
                "unit_price": float(item.unit_price) if item.unit_price else None,
                "total_price": float(item.total_price) if item.total_price else 0.0,
                "discount": float(item.discount) if item.discount else None,
            }
            for item in receipt.items
        ],
        "source_file": receipt.source_file,
        "created_at": receipt.created_at.isoformat() if receipt.created_at else None,
    }


@router.websocket("/ws/processing/{receipt_id}")
async def websocket_processing(websocket: WebSocket, receipt_id: int):
    """
    WebSocket endpoint for real-time processing updates.
    """
    await websocket.accept()
    
    try:
        # Send initial message
        await websocket.send_json({
            "type": "connected",
            "receipt_id": receipt_id,
        })
        
        # TODO: Implement real-time progress updates
        # This would require refactoring process_receipt_async to send updates
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "pong",
                "message": "Connection alive",
            })
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for receipt {receipt_id}")

