import os
from decimal import Decimal
from dotenv import load_dotenv

# Ładujemy zmienne z pliku .env (zakładamy, że jest w folderze nadrzędnym względem src lub w root projektu)
# Szukamy .env w folderze ReceiptParser (gdzie jest requirements.txt)
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(os.path.dirname(current_dir), ".env")

load_dotenv(env_path)


class Config:
    # OLLAMA_HOST - automatycznie wykrywa czy jesteśmy w Dockerze
    # W Dockerze używa nazwy serwisu "ollama", lokalnie "localhost"
    _default_ollama_host = (
        "http://ollama:11434" if os.getenv("DOCKER_CONTAINER") == "true" 
        else "http://localhost:11434"
    )
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", _default_ollama_host)
    VISION_MODEL = os.getenv("VISION_MODEL", "llava:latest")
    TEXT_MODEL = os.getenv("TEXT_MODEL", "SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
    # Timeout dla zapytań do Ollama (w sekundach)
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # Domyślnie 5 minut
    
    # --- Konfiguracja Cloud vs Local ---
    # Domyślnie używamy Cloud (Mistral OCR + OpenAI) dla łatwości użycia
    USE_CLOUD_AI = os.getenv("USE_CLOUD_AI", "true").lower() == "true"
    USE_CLOUD_OCR = os.getenv("USE_CLOUD_OCR", "true").lower() == "true"
    
    # Klucze API dla Cloud
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Modele OpenAI (domyślne)
    OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")  # Tani i szybki
    OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")  # Tani i szybki
    
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

    @staticmethod
    def print_config():
        print("--- Konfiguracja ---")
        print(f"USE_CLOUD_AI: {Config.USE_CLOUD_AI}")
        print(f"USE_CLOUD_OCR: {Config.USE_CLOUD_OCR}")
        if Config.USE_CLOUD_AI:
            print(f"OPENAI_VISION_MODEL: {Config.OPENAI_VISION_MODEL}")
            print(f"OPENAI_TEXT_MODEL: {Config.OPENAI_TEXT_MODEL}")
        else:
            print(f"OLLAMA_HOST: {Config.OLLAMA_HOST}")
            print(f"VISION_MODEL: {Config.VISION_MODEL}")
            print(f"TEXT_MODEL:  {Config.TEXT_MODEL}")
        print("--------------------")
