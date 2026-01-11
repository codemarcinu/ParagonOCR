from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict
import logging
import asyncio
import os
import uuid
from datetime import datetime

from app.database import get_db, SessionLocal
from app.models.receipt import Receipt, ReceiptItem
from app.models.user import User
from app.models.shop import Shop
from app.schemas import ReceiptCreate, ReceiptResponse, IngestReceiptRequest
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.inventory_service import InventoryService
from app.dependencies import get_current_user

# Konfiguracja loggera
logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["receipts"]
)

# Instancje serwisów
ocr_service = OCRService()
llm_service = LLMService()
inventory_service = InventoryService()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, receipt_id: int):
        await websocket.accept()
        if receipt_id not in self.active_connections:
            self.active_connections[receipt_id] = []
        self.active_connections[receipt_id].append(websocket)

    def disconnect(self, websocket: WebSocket, receipt_id: int):
        if receipt_id in self.active_connections:
            self.active_connections[receipt_id].remove(websocket)
            if not self.active_connections[receipt_id]:
                del self.active_connections[receipt_id]

    async def send_update(self, receipt_id: int, message: dict):
        if receipt_id in self.active_connections:
            for connection in self.active_connections[receipt_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WS update: {e}")

manager = ConnectionManager()

async def process_receipt_task(receipt_id: int, file_content: bytes, filename: str):
    """Background task to process receipt."""
    db = SessionLocal()
    try:
        # 1. OCR
        await manager.send_update(receipt_id, {
            "type": "update", "stage": "ocr", "progress": 20, "message": "Wyodrębnianie tekstu (OCR)..."
        })
        raw_text = await ocr_service.extract_text(file_content, filename)
        
        if not raw_text or len(raw_text.strip()) < 10:
            await manager.send_update(receipt_id, {
                "type": "error", "stage": "error", "message": "Nie udało się odczytać tekstu z paragonu."
            })
            db.query(Receipt).filter(Receipt.id == receipt_id).update({"status": "failed"})
            db.commit()
            return

        # 2. LLM Processing
        await manager.send_update(receipt_id, {
            "type": "update", "stage": "llm", "progress": 50, "message": "Analiza AI..."
        })
        parsed_data = await llm_service.process_receipt(raw_text)
        
        # 3. Save results
        await manager.send_update(receipt_id, {
            "type": "update", "stage": "saving", "progress": 80, "message": "Zapisywanie danych..."
        })
        
        # A. Shop
        shop_name = parsed_data.get("shop_name", "Nieznany Sklep")
        shop = db.query(Shop).filter(Shop.name == shop_name).first()
        if not shop:
            shop = Shop(name=shop_name)
            db.add(shop)
            db.flush()
        
        # B. Update Receipt
        purchase_date = parsed_data.get("date")
        if isinstance(purchase_date, str):
            try:
                 purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
            except:
                 purchase_date = datetime.utcnow().date()
        if not purchase_date:
             purchase_date = datetime.utcnow().date()

        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        receipt.shop_id = shop.id
        receipt.purchase_date = purchase_date
        receipt.total_amount = parsed_data.get("total_amount", 0.0)
        receipt.ocr_text = raw_text
        receipt.status = "completed"
        
        # C. Items & Pantry
        items_data = parsed_data.get("items", [])
        inventory_service.process_receipt_items(db, receipt, items_data)
        
        db.commit()
        
        await manager.send_update(receipt_id, {
            "type": "update", "stage": "completed", "progress": 100, "message": "Gotowe!"
        })

    except Exception as e:
        logger.error(f"Error in background task for receipt {receipt_id}: {e}")
        db.query(Receipt).filter(Receipt.id == receipt_id).update({"status": "error"})
        db.commit()
        await manager.send_update(receipt_id, {
            "type": "error", "stage": "error", "message": f"Błąd: {str(e)}"
        })
    finally:
        db.close()

async def process_receipt_from_text_task(receipt_id: int, text: str):
    """Background task to process receipt from raw text (skipping OCR)."""
    db = SessionLocal()
    try:
        # 1. Skip OCR
        
        # 2. LLM Processing
        await manager.send_update(receipt_id, {
            "type": "update", "stage": "llm", "progress": 50, "message": "Analiza AI (z tekstu)..."
        })
        parsed_data = await llm_service.process_receipt(text)
        
        # 3. Save results (Logic duplicated from process_receipt_task - candidates for refactoring)
        await manager.send_update(receipt_id, {
            "type": "update", "stage": "saving", "progress": 80, "message": "Zapisywanie danych..."
        })
        
        # A. Shop
        shop_name = parsed_data.get("shop_name", "Nieznany Sklep")
        shop = db.query(Shop).filter(Shop.name == shop_name).first()
        if not shop:
            shop = Shop(name=shop_name)
            db.add(shop)
            db.flush()
        
        # B. Update Receipt
        purchase_date = parsed_data.get("date")
        if isinstance(purchase_date, str):
            try:
                 purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d").date()
            except:
                 purchase_date = datetime.utcnow().date()
        if not purchase_date:
             purchase_date = datetime.utcnow().date()

        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        receipt.shop_id = shop.id
        receipt.purchase_date = purchase_date
        receipt.total_amount = parsed_data.get("total_amount", 0.0)
        receipt.ocr_text = text
        receipt.status = "completed"
        
        # C. Items & Pantry
        items_data = parsed_data.get("items", [])
        inventory_service.process_receipt_items(db, receipt, items_data)
        
        db.commit()
        
        await manager.send_update(receipt_id, {
            "type": "update", "stage": "completed", "progress": 100, "message": "Gotowe!"
        })

    except Exception as e:
        logger.error(f"Error in background task for receipt {receipt_id}: {e}")
        db.query(Receipt).filter(Receipt.id == receipt_id).update({"status": "error"})
        db.commit()
        await manager.send_update(receipt_id, {
            "type": "error", "stage": "error", "message": f"Błąd: {str(e)}"
        })
    finally:
        db.close()

@router.websocket("/ws/processing/{receipt_id}")
async def websocket_endpoint(websocket: WebSocket, receipt_id: int):
    await manager.connect(websocket, receipt_id)
    try:
        while True:
            # Keep connection open, wait for client to close or task to finish
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(websocket, receipt_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, receipt_id)

@router.post("/ingest-text", response_model=ReceiptResponse)
async def ingest_receipt_text(
    request: IngestReceiptRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Accepts raw text (e.g. from client-side PDF extraction), creates a receipt, and processes it via LLM.
    """
    try:
        # Create placeholder receipt
        unknown_shop = db.query(Shop).filter(Shop.name == "Przetwarzanie...").first()
        if not unknown_shop:
            unknown_shop = Shop(name="Przetwarzanie...")
            db.add(unknown_shop)
            db.commit()
            db.refresh(unknown_shop)

        new_receipt = Receipt(
            user_id=current_user.id,
            shop_id=unknown_shop.id,
            purchase_date=request.date or datetime.utcnow().date(),
            total_amount=0.0,
            source_file="client_text_ingest",
            ocr_text=request.text,
            status="processing"
        )
        db.add(new_receipt)
        db.commit()
        db.refresh(new_receipt)

        # Add background task
        background_tasks.add_task(process_receipt_from_text_task, new_receipt.id, request.text)

        return new_receipt

    except Exception as e:
        logger.error(f"Error in ingest_receipt_text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=ReceiptResponse)
async def analyze_receipt(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    1. Odbiera plik.
    2. Tworzy wstępny rekord w bazie (status: processing).
    3. Uruchamia zadanie w tle.
    4. Zwraca ID paragonu.
    """
    logger.info(f"Otrzymano plik do analizy: {file.filename}")
    
    # Walidacja formatu
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
        raise HTTPException(status_code=400, detail="Nieobsługiwany format pliku. Użyj PDF lub obrazu.")

    try:
        content = await file.read()
        
        # 1. Create Initial Receipt (Placeholder)
        # We need a temporary shop_id or make it nullable. 
        # For now, let's find or create an "In processing" shop or just use ID 1 if exists.
        # Better: let's ensure shop_id can be nullable in the model, or use a default.
        # Looking at previous code, shop_id was NOT NULL.
        
        unknown_shop = db.query(Shop).filter(Shop.name == "Przetwarzanie...").first()
        if not unknown_shop:
            unknown_shop = Shop(name="Przetwarzanie...")
            db.add(unknown_shop)
            db.commit()
            db.refresh(unknown_shop)

        new_receipt = Receipt(
            user_id=current_user.id,
            shop_id=unknown_shop.id,
            purchase_date=datetime.utcnow().date(),
            total_amount=0.0,
            source_file=file.filename,
            status="processing"
        )
        db.add(new_receipt)
        db.commit()
        db.refresh(new_receipt)

        # 2. Add Background Task
        background_tasks.add_task(process_receipt_task, new_receipt.id, content, file.filename)
        
        return new_receipt

    except Exception as e:
        logger.error(f"Błąd podczas inicjacji analizy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Błąd serwera: {str(e)}")

@router.get("/", response_model=List[ReceiptResponse])
async def get_receipts(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    receipts = db.query(Receipt).filter(Receipt.user_id == current_user.id).offset(skip).limit(limit).all()
    return receipts

@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.user_id == current_user.id
    ).first()
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Nie znaleziono paragonu.")
    
    return receipt
