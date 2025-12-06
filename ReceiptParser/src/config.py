import os
from decimal import Decimal
from dotenv import load_dotenv

# Ładujemy zmienne z pliku .env (zakładamy, że jest w folderze nadrzędnym względem src lub w root projektu)
# Szukamy .env w folderze ReceiptParser (gdzie jest requirements.txt)
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(os.path.dirname(current_dir), ".env")

load_dotenv(env_path)


class Config:
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    VISION_MODEL = os.getenv("VISION_MODEL", "llava:latest")
    TEXT_MODEL = os.getenv("TEXT_MODEL", "SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
    # Timeout dla zapytań do Ollama (w sekundach)
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # Domyślnie 5 minut

    # --- Stałe matematyczne dla weryfikacji paragonów ---
    # Tolerancja dla błędów zaokrągleń w weryfikacji matematycznej (w PLN)
    MATH_TOLERANCE = Decimal("0.01")
    # Znacząca różnica w cenach, która wymaga korekty (w PLN)
    SIGNIFICANT_DIFFERENCE = Decimal("1.00")
    # Minimalna cena produktu, poniżej której pozycja jest traktowana jako błąd OCR (w PLN)
    MIN_PRODUCT_PRICE = Decimal("0.01")

    # --- Stałe dla strategii Kaufland ---
    # Typowe rabaty z karty Kaufland Card (w PLN)
    KAUFLAND_TYPICAL_DISCOUNTS = [Decimal("5.0"), Decimal("10.0"), Decimal("15.0")]
    # Tolerancja dla wykrywania rabatów z karty (w PLN)
    KAUFLAND_DISCOUNT_TOLERANCE = Decimal("1.0")

    # --- Konfiguracja logowania ---
    # Włącza logowanie do pliku (domyślnie wyłączone)
    ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true"

    # --- Konfiguracja OCR ---
    # Silnik OCR: 'tesseract' (CPU) lub 'easyocr' (GPU/CPU)
    OCR_ENGINE = os.getenv("OCR_ENGINE", "tesseract")
    # Czy używać GPU dla EasyOCR (jeśli dostępne)
    USE_GPU_OCR = os.getenv("USE_GPU_OCR", "true").lower() == "true"

    # --- Konfiguracja Retry Logic ---
    # Maksymalna liczba prób retry dla wywołań API
    RETRY_MAX_ATTEMPTS = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
    # Początkowe opóźnienie przed retry (w sekundach)
    RETRY_INITIAL_DELAY = float(os.getenv("RETRY_INITIAL_DELAY", "1.0"))
    # Maksymalne opóźnienie przed retry (w sekundach)
    RETRY_MAX_DELAY = float(os.getenv("RETRY_MAX_DELAY", "30.0"))
    # Mnożnik exponential backoff
    RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))
    # Czy używać jitter (losowe opóźnienie ±20% dla uniknięcia thundering herd)
    RETRY_JITTER = os.getenv("RETRY_JITTER", "true").lower() == "true"

    # --- Konfiguracja Batch Processing LLM ---
    # Rozmiar batcha dla normalizacji produktów (5-10 to sweet spot)
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
    # Maksymalna liczba równoległych batchy (ThreadPoolExecutor workers)
    BATCH_MAX_WORKERS = int(os.getenv("BATCH_MAX_WORKERS", "3"))

    @staticmethod
    def print_config():
        print("--- Konfiguracja ---")
        print(f"OLLAMA_HOST: {Config.OLLAMA_HOST}")
        print(f"VISION_MODEL: {Config.VISION_MODEL}")
        print(f"TEXT_MODEL:  {Config.TEXT_MODEL}")
        print(f"OCR_ENGINE:  {Config.OCR_ENGINE}")
        print(f"USE_GPU_OCR: {Config.USE_GPU_OCR}")
        print("--------------------")
