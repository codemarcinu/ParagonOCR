import os
from decimal import Decimal
from dotenv import load_dotenv

# Ładujemy zmienne z pliku .env (zakładamy, że jest w folderze nadrzędnym względem src lub w root projektu)
# Szukamy .env w folderze ReceiptParser (gdzie jest requirements.txt)
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(os.path.dirname(current_dir), ".env")

load_dotenv(env_path)


class Config:
    # --- Konfiguracja Cloud (wymuszona dla wersji webowej) ---
    # Wersja webowa działa TYLKO z Mistral OCR i OpenAI API
    # Ollama nie jest obsługiwane w tej wersji
    USE_CLOUD_AI = True  # Wymuszone na True
    USE_CLOUD_OCR = True  # Wymuszone na True
    
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
    
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
        print("--- Konfiguracja (Web - Cloud Only) ---")
        print(f"USE_CLOUD_AI: {Config.USE_CLOUD_AI} (wymuszone)")
        print(f"USE_CLOUD_OCR: {Config.USE_CLOUD_OCR} (wymuszone)")
        print(f"OPENAI_VISION_MODEL: {Config.OPENAI_VISION_MODEL}")
        print(f"OPENAI_TEXT_MODEL: {Config.OPENAI_TEXT_MODEL}")
        print("--------------------")
