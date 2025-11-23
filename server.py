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
import time
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
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

# CORS - konfiguracja z obsługą produkcji
environment = os.getenv("ENVIRONMENT", "development").lower()
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")

if allowed_origins_env == "*":
    if environment == "production":
        raise ValueError(
            "CORS allow_origins=['*'] nie jest dozwolone w produkcji! "
            "Ustaw zmienną środowiskową ALLOWED_ORIGINS z listą dozwolonych domen."
        )
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sesja bazy danych
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Przechowywanie zadań przetwarzania (w produkcji użyj Redis/DB)
processing_tasks: Dict[str, Dict[str, Any]] = {}
# Lock dla bezpiecznego dostępu do processing_tasks z wielu wątków
processing_tasks_lock = threading.Lock()

# Stałe konfiguracyjne
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
TASK_TIMEOUT = 600  # 10 minut w sekundach


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
    
    @validator('question')
    def validate_question(cls, v: str) -> str:
        """Waliduje pytanie użytkownika."""
        if not v or not v.strip():
            raise ValueError("Pytanie nie może być puste")
        if len(v) > 2000:
            raise ValueError("Pytanie jest za długie (max 2000 znaków)")
        return v.strip()

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
    
    @validator('openai_api_key')
    def validate_openai_key(cls, v: Optional[str]) -> Optional[str]:
        """Waliduje format klucza OpenAI API."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not v.startswith("sk-"):
            raise ValueError("Nieprawidłowy format klucza OpenAI API (powinien zaczynać się od 'sk-')")
        return v
    
    @validator('mistral_api_key')
    def validate_mistral_key(cls, v: Optional[str]) -> Optional[str]:
        """Waliduje format klucza Mistral API."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) < 20:
            raise ValueError("Nieprawidłowy format klucza Mistral API (za krótki)")
        return v


# --- Endpointy API ---

def cleanup_old_tasks():
    """Usuwa stare zadania z processing_tasks i pliki upload (starsze niż 1 godzina)."""
    current_time = time.time()
    tasks_to_remove = []
    files_removed = 0
    
    # Użyj locka i skopiuj klucze przed iteracją, aby uniknąć RuntimeError
    # gdy słownik jest modyfikowany przez inne wątki
    with processing_tasks_lock:
        # Skopiuj klucze przed iteracją, aby uniknąć "dictionary changed size during iteration"
        task_ids = list(processing_tasks.keys())
    
    # Iteruj po skopiowanych kluczach (bez locka, aby nie blokować innych operacji)
    for task_id in task_ids:
        # Pobierz dane zadania z lockiem
        with processing_tasks_lock:
            task_data = processing_tasks.get(task_id)
            if not task_data:
                continue  # Zadanie już zostało usunięte przez inny wątek
        
        start_time = task_data.get("start_time", current_time)
        elapsed = current_time - start_time
        
        # Usuń zadania starsze niż 1 godzina lub zakończone (completed/error/timeout) starsze niż 10 minut
        if elapsed > 3600:  # 1 godzina
            tasks_to_remove.append(task_id)
        elif task_data.get("status") in ["completed", "error", "timeout"]:
            end_time = task_data.get("end_time", start_time)
            if current_time - end_time > 600:  # 10 minut po zakończeniu
                tasks_to_remove.append(task_id)
    
    # Usuń zadania z lockiem
    for task_id in tasks_to_remove:
        # Usuń plik jeśli istnieje
        with processing_tasks_lock:
            task_data = processing_tasks.get(task_id)
            if task_data:
                file_path = task_data.get("file_path")
                if file_path and os.path.exists(file_path):
                    try:
                        os.unlink(file_path)
                        files_removed += 1
                    except Exception:
                        pass
                del processing_tasks[task_id]
    
    # Dodatkowo: usuń stare pliki z katalogu uploads (starsze niż 24 godziny)
    upload_dir = Path("uploads")
    if upload_dir.exists():
        for file_path in upload_dir.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > 86400:  # 24 godziny
                    try:
                        file_path.unlink()
                        files_removed += 1
                    except Exception:
                        pass
    
    if tasks_to_remove or files_removed > 0:
        print(f"INFO: Usunięto {len(tasks_to_remove)} starych zadań i {files_removed} plików")


@app.on_event("startup")
async def startup_event():
    """Inicjalizacja przy starcie aplikacji."""
    # Upewnij się, że baza danych istnieje
    init_db()
    
    # Uruchom cleanup starych zadań co 5 minut
    def periodic_cleanup():
        while True:
            time.sleep(300)  # 5 minut
            cleanup_old_tasks()
    
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    
    print("ParagonWeb API uruchomione!")


@app.get("/")
async def root():
    """Endpoint główny."""
    return {"message": "ParagonWeb API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint - sprawdza stan aplikacji."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Sprawdź bazę danych
    try:
        from sqlalchemy import text
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        session.close()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"
    
    # Sprawdź dostępność AI provider
    try:
        from ReceiptParser.src.ai_providers import get_ai_provider
        provider = get_ai_provider()
        if provider.is_available():
            health_status["checks"]["ai_provider"] = "ok"
        else:
            health_status["checks"]["ai_provider"] = "unavailable"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["ai_provider"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Sprawdź liczbę aktywnych zadań
    active_tasks = sum(1 for task in processing_tasks.values() if task.get("status") == "processing")
    health_status["checks"]["active_tasks"] = active_tasks
    health_status["checks"]["total_tasks"] = len(processing_tasks)
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


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
    
    # Walidacja formatu pliku
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.png', '.jpg', '.jpeg', '.pdf']:
        raise HTTPException(status_code=400, detail="Nieobsługiwany format pliku")
    
    # Wczytaj zawartość pliku do pamięci (do walidacji rozmiaru)
    content = await file.read()
    
    # Walidacja rozmiaru pliku
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Plik za duży. Maksymalny rozmiar: {MAX_UPLOAD_SIZE / 1024 / 1024:.0f} MB. Otrzymano: {len(content) / 1024 / 1024:.2f} MB"
        )
    
    # Utwórz katalog na uploady jeśli nie istnieje
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Zapisz plik
    file_path = upload_dir / f"{task_id}{file_ext}"
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Inicjalizuj zadanie z timestamp (z lockiem)
    with processing_tasks_lock:
        processing_tasks[task_id] = {
            "status": "processing",
            "progress": 0,
            "message": "Rozpoczynam przetwarzanie...",
            "file_path": str(file_path),
            "start_time": time.time(),
        }
    
    # Uruchom przetwarzanie w tle
    def process_receipt():
        start_time = time.time()
        try:
            def log_callback(message: str, progress: Optional[float] = None, status: Optional[str] = None):
                with processing_tasks_lock:
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
            
            # Sprawdź timeout przed oznaczeniem jako completed
            elapsed_time = time.time() - start_time
            with processing_tasks_lock:
                if task_id in processing_tasks:
                    if elapsed_time > TASK_TIMEOUT:
                        processing_tasks[task_id]["status"] = "timeout"
                        processing_tasks[task_id]["message"] = f"Przetwarzanie przekroczyło limit czasu ({TASK_TIMEOUT}s)"
                    else:
                        processing_tasks[task_id]["status"] = "completed"
                        processing_tasks[task_id]["progress"] = 100
                        processing_tasks[task_id]["message"] = "Przetwarzanie zakończone!"
        except Exception as e:
            with processing_tasks_lock:
                if task_id in processing_tasks:
                    processing_tasks[task_id]["status"] = "error"
                    processing_tasks[task_id]["message"] = f"Błąd: {str(e)}"
        finally:
            # Oznacz czas zakończenia
            with processing_tasks_lock:
                if task_id in processing_tasks:
                    processing_tasks[task_id]["end_time"] = time.time()
    
    # Uruchom w osobnym wątku
    import threading
    thread = threading.Thread(target=process_receipt)
    thread.daemon = True
    thread.start()
    
    return {"task_id": task_id, "status": "processing"}


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """Sprawdza status zadania przetwarzania."""
    # Walidacja formatu UUID (podstawowa)
    if len(task_id) != 36 or task_id.count("-") != 4:
        raise HTTPException(status_code=400, detail="Nieprawidłowy format ID zadania")
    
    # Pobierz dane zadania z lockiem
    with processing_tasks_lock:
        if task_id not in processing_tasks:
            raise HTTPException(status_code=404, detail="Zadanie nie znalezione")
        
        task_data = processing_tasks[task_id].copy()
    
    # Sprawdź timeout dla aktywnych zadań (bez locka, bo tylko czytamy kopię)
    if task_data.get("status") == "processing":
        start_time = task_data.get("start_time", time.time())
        elapsed = time.time() - start_time
        if elapsed > TASK_TIMEOUT:
            task_data["status"] = "timeout"
            task_data["message"] = f"Przetwarzanie przekroczyło limit czasu ({TASK_TIMEOUT}s)"
            # Zaktualizuj status w słowniku (z lockiem)
            with processing_tasks_lock:
                if task_id in processing_tasks:
                    processing_tasks[task_id]["status"] = "timeout"
                    processing_tasks[task_id]["message"] = task_data["message"]
    
    return task_data


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
    # Walidacja jest już wykonana przez Pydantic
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
    # Walidacja jest już wykonana przez Pydantic
    
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

