from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db
from app.models.receipt import Receipt, ReceiptItem
from app.models.user import User
from app.schemas import ReceiptCreate, ReceiptResponse
from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.inventory_service import InventoryService
from app.dependencies import get_current_user

# Konfiguracja loggera
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/receipts",
    tags=["receipts"]
)

# Instancje serwisów
ocr_service = OCRService()
llm_service = LLMService()
inventory_service = InventoryService()

@router.post("/analyze", response_model=ReceiptResponse)
async def analyze_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    1. Odbiera plik.
    2. Robi OCR (OCRService).
    3. Analizuje tekst przez AI (LLMService).
    4. Zapisuje wynik w bazie danych.
    """
    logger.info(f"Otrzymano plik do analizy: {file.filename}")
    
    # Walidacja formatu
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
        raise HTTPException(status_code=400, detail="Nieobsługiwany format pliku. Użyj PDF lub obrazu.")

    try:
        # 1. Odczyt pliku
        content = await file.read()
        
        # 2. OCR (Nowa klasa OCRService)
        logger.info("Rozpoczynanie OCR...")
        raw_text = await ocr_service.extract_text(content, file.filename)
        
        if not raw_text or len(raw_text.strip()) < 10:
            raise HTTPException(status_code=422, detail="Nie udało się odczytać tekstu z paragonu.")

        # 3. LLM Processing
        logger.info("Rozpoczynanie analizy LLM...")
        parsed_data = await llm_service.process_receipt(raw_text)
        
        # 4. Zapis do bazy danych
        # Tworzenie paragonu
        new_receipt = Receipt(
            user_id=current_user.id,
            shop_name=parsed_data.get("shop_name", "Nieznany"),
            date=parsed_data.get("date"),
            total_amount=parsed_data.get("total_amount", 0.0),
            raw_text=raw_text
        )
        db.add(new_receipt)
        db.commit()
        db.refresh(new_receipt)

        # Tworzenie pozycji (items) i aktualizacja spiżarni
        items_data = parsed_data.get("items", [])
        inventory_service.process_receipt_items(db, new_receipt, items_data)
        
        db.commit()
        
        return new_receipt

    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania paragonu: {str(e)}")
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
