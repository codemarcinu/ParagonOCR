"""
FastAPI backend dla ParagonWeb.

Endpointy API:
- POST /api/upload - przetwarzanie paragonu
- GET /api/receipts - lista paragonów
- GET /api/stats - statystyki zakupów
- GET /api/inventory - stan magazynu
- POST /api/chat - czat z Bielikiem
- GET/POST /api/settings - ustawienia aplikacji
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import sessionmaker, joinedload

# Dodaj ReceiptParser do ścieżki
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ReceiptParser'))

from ReceiptParser.src.database import (
    engine, init_db,
    Paragon, Produkt, StanMagazynowy, Sklep, KategoriaProduktu, AliasProduktu
)
from ReceiptParser.src.main import run_processing_pipeline
from ReceiptParser.src.bielik import BielikAssistant
from ReceiptParser.src.purchase_analytics import PurchaseAnalytics
from ReceiptParser.src.config import Config

# Inicjalizacja FastAPI
app = FastAPI(title="ParagonWeb API", version="1.0.0")

# CORS - pozwól na dostęp z frontendu
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # W produkcji ustaw konkretne domeny
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sesja bazy danych
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Przechowywanie zadań przetwarzania (w produkcji użyj Redis/DB)
processing_tasks: Dict[str, Dict[str, Any]] = {}


# --- Modele Pydantic ---

class ReceiptResponse(BaseModel):
    paragon_id: int
    sklep: str
    data_zakupu: date
    suma_paragonu: Decimal
    liczba_pozycji: int
    plik_zrodlowy: str

class InventoryItem(BaseModel):
    produkt_id: int
    nazwa: str
    ilosc: Decimal
    jednostka: str
    data_waznosci: Optional[date]
    zamrozone: bool
    kategoria: Optional[str]

class ChatMessage(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

class SettingsResponse(BaseModel):
    use_cloud_ai: bool
    use_cloud_ocr: bool
    openai_api_key_set: bool
    mistral_api_key_set: bool

class SettingsUpdate(BaseModel):
    use_cloud_ai: Optional[bool] = None
    use_cloud_ocr: Optional[bool] = None
    openai_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None


# --- Endpointy API ---

@app.on_event("startup")
async def startup_event():
    """Inicjalizacja przy starcie aplikacji."""
    # Upewnij się, że baza danych istnieje
    init_db()
    print("ParagonWeb API uruchomione!")


@app.get("/")
async def root():
    """Endpoint główny."""
    return {"message": "ParagonWeb API", "version": "1.0.0"}


@app.post("/api/upload")
async def upload_receipt(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Przetwarza przesłany paragon.
    
    Zwraca ID zadania do śledzenia postępu.
    """
    import uuid
    import tempfile
    
    # Generuj unikalne ID zadania
    task_id = str(uuid.uuid4())
    
    # Zapisz plik tymczasowo
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.png', '.jpg', '.jpeg', '.pdf']:
        raise HTTPException(status_code=400, detail="Nieobsługiwany format pliku")
    
    # Utwórz katalog na uploady jeśli nie istnieje
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Zapisz plik
    file_path = upload_dir / f"{task_id}{file_ext}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Inicjalizuj zadanie
    processing_tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Rozpoczynam przetwarzanie...",
        "file_path": str(file_path),
    }
    
    # Uruchom przetwarzanie w tle
    def process_receipt():
        try:
            def log_callback(message: str, progress: Optional[float] = None, status: Optional[str] = None):
                if task_id in processing_tasks:
                    # Zawsze zachowaj szczegółową wiadomość
                    processing_tasks[task_id]["message"] = message
                    if progress is not None:
                        processing_tasks[task_id]["progress"] = int(progress)
                    if status is not None:
                        # Status jest dodatkową informacją, przechowuj osobno
                        # Nie nadpisuj wiadomości, która zawiera szczegóły
                        processing_tasks[task_id]["status_label"] = status
            
            def prompt_callback(prompt_text: str, default_value: str, raw_name: str) -> str:
                # Dla web app, używamy wartości domyślnej (można później dodać interakcję)
                return default_value
            
            def review_callback(parsed_data: dict) -> dict:
                # Dla web app, akceptujemy dane bez weryfikacji (można później dodać UI)
                return parsed_data
            
            # Wybierz model w zależności od konfiguracji
            if Config.USE_CLOUD_OCR:
                llm_model = "mistral-ocr"
            else:
                llm_model = Config.VISION_MODEL
            
            run_processing_pipeline(
                str(file_path),
                llm_model,
                log_callback,
                prompt_callback,
                review_callback,
            )
            
            processing_tasks[task_id]["status"] = "completed"
            processing_tasks[task_id]["progress"] = 100
            processing_tasks[task_id]["message"] = "Przetwarzanie zakończone!"
        except Exception as e:
            processing_tasks[task_id]["status"] = "error"
            processing_tasks[task_id]["message"] = f"Błąd: {str(e)}"
    
    # Uruchom w osobnym wątku
    import threading
    thread = threading.Thread(target=process_receipt)
    thread.daemon = True
    thread.start()
    
    return {"task_id": task_id, "status": "processing"}


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """Sprawdza status zadania przetwarzania."""
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Zadanie nie znalezione")
    
    return processing_tasks[task_id]


@app.get("/api/receipts")
async def get_receipts(skip: int = 0, limit: int = 50):
    """Zwraca listę paragonów."""
    session = SessionLocal()
    try:
        paragony = (
            session.query(Paragon)
            .join(Sklep)
            .order_by(Paragon.data_zakupu.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        results = []
        for paragon in paragony:
            results.append({
                "paragon_id": paragon.paragon_id,
                "sklep": paragon.sklep.nazwa_sklepu,
                "data_zakupu": paragon.data_zakupu.isoformat() if paragon.data_zakupu else None,
                "suma_paragonu": float(paragon.suma_paragonu),
                "liczba_pozycji": len(paragon.pozycje),
                "plik_zrodlowy": paragon.plik_zrodlowy,
            })
        
        return {"receipts": results, "total": len(results)}
    finally:
        session.close()


@app.get("/api/stats")
async def get_stats():
    """Zwraca statystyki zakupów."""
    try:
        with PurchaseAnalytics() as analytics:
            stats = analytics.get_total_statistics()
            stores = analytics.get_spending_by_store(limit=10)
            categories = analytics.get_spending_by_category(limit=10)
            products = analytics.get_top_products(limit=10)
            monthly = analytics.get_monthly_statistics()
            
            return {
                "total_statistics": {
                    "total_receipts": stats["total_receipts"],
                    "total_spent": float(stats["total_spent"]),
                    "total_items": stats["total_items"],
                    "avg_receipt": float(stats["avg_receipt"]),
                },
                "by_store": [{"name": s[0], "amount": float(s[1])} for s in stores],
                "by_category": [{"name": c[0], "amount": float(c[1])} for c in categories],
                "top_products": [
                    {"name": p[0], "count": p[1], "total": float(p[2])}
                    for p in products
                ],
                "monthly": [
                    {
                        "month": m["month_name"],
                        "receipts": m["receipts_count"],
                        "spent": float(m["total_spent"]),
                    }
                    for m in monthly[:12]
                ],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd podczas pobierania statystyk: {str(e)}")


@app.get("/api/inventory")
async def get_inventory():
    """Zwraca stan magazynu."""
    session = SessionLocal()
    try:
        stany = (
            session.query(StanMagazynowy)
            .join(Produkt)
            .options(joinedload(StanMagazynowy.produkt).joinedload(Produkt.kategoria))
            .filter(StanMagazynowy.ilosc > 0)
            .order_by(StanMagazynowy.data_waznosci)
            .all()
        )
        
        results = []
        for stan in stany:
            results.append({
                "produkt_id": stan.produkt_id,
                "nazwa": stan.produkt.znormalizowana_nazwa,
                "ilosc": float(stan.ilosc),
                "jednostka": stan.jednostka_miary or "szt",
                "data_waznosci": stan.data_waznosci.isoformat() if stan.data_waznosci else None,
                "zamrozone": stan.zamrozone or False,
                "kategoria": stan.produkt.kategoria.nazwa_kategorii if stan.produkt.kategoria else None,
            })
        
        return {"inventory": results}
    finally:
        session.close()


@app.post("/api/chat")
async def chat_with_bielik(message: ChatMessage):
    """Wysyła wiadomość do asystenta Bielik."""
    assistant = None
    try:
        assistant = BielikAssistant()
        answer = assistant.answer_question(message.question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd podczas komunikacji z Bielikiem: {str(e)}")
    finally:
        if assistant is not None:
            assistant.close()


@app.get("/api/settings")
async def get_settings():
    """Zwraca aktualne ustawienia aplikacji."""
    return {
        "use_cloud_ai": Config.USE_CLOUD_AI,
        "use_cloud_ocr": Config.USE_CLOUD_OCR,
        "openai_api_key_set": bool(Config.OPENAI_API_KEY),
        "mistral_api_key_set": bool(Config.MISTRAL_API_KEY),
    }


@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    """
    Aktualizuje ustawienia aplikacji.
    
    Uwaga: W produkcji zapisz to w bazie danych lub pliku konfiguracyjnym.
    """
    # Tymczasowo aktualizujemy tylko zmienne środowiskowe
    # W produkcji powinno to być zapisane w bazie danych lub pliku .env
    
    if settings.use_cloud_ai is not None:
        Config.USE_CLOUD_AI = settings.use_cloud_ai
        os.environ["USE_CLOUD_AI"] = str(settings.use_cloud_ai).lower()
    
    if settings.use_cloud_ocr is not None:
        Config.USE_CLOUD_OCR = settings.use_cloud_ocr
        os.environ["USE_CLOUD_OCR"] = str(settings.use_cloud_ocr).lower()
    
    if settings.openai_api_key is not None:
        Config.OPENAI_API_KEY = settings.openai_api_key
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    
    if settings.mistral_api_key is not None:
        Config.MISTRAL_API_KEY = settings.mistral_api_key
        os.environ["MISTRAL_API_KEY"] = settings.mistral_api_key
    
    return {"message": "Ustawienia zaktualizowane"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

