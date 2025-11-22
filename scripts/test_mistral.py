import os
import sys

# Dodaj ścieżkę do modułów (scripts/ jest w głównym katalogu, ReceiptParser/ też)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ReceiptParser'))

from src.mistral_ocr import MistralOCRClient
from src.llm import parse_receipt_from_text
from src.config import Config


def test_mistral_integration(image_path):
    print(f"--- Testowanie integracji Mistral OCR ---")
    print(f"Plik: {image_path}")

    if not Config.MISTRAL_API_KEY:
        print("BŁĄD: Brak klucza API Mistral w konfiguracji.")
        return

    client = MistralOCRClient()
    print("1. Wysyłanie obrazu do Mistral OCR...")
    markdown = client.process_image(image_path)

    if not markdown:
        print("BŁĄD: Nie udało się uzyskać tekstu z Mistral OCR.")
        return

    print("\n--- WYNIK OCR (Markdown) ---")
    print(markdown[:500] + "..." if len(markdown) > 500 else markdown)
    print("----------------------------\n")

    print("2. Parsowanie tekstu przez LLM (Bielik)...")
    parsed_data = parse_receipt_from_text(markdown)

    if parsed_data:
        print("\n--- WYNIK PARSOWANIA (JSON) ---")
        import json

        # Konwersja Decimal/datetime do stringa dla wyświetlenia
        def default_serializer(obj):
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            return str(obj)

        print(
            json.dumps(
                parsed_data, indent=2, default=default_serializer, ensure_ascii=False
            )
        )
        print("-------------------------------")
        print("SUKCES: Integracja działa poprawnie.")
    else:
        print("BŁĄD: Nie udało się sparsować danych.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Użycie: python test_mistral.py <sciezka_do_obrazu>")
        sys.exit(1)

    image_path = sys.argv[1]
    test_mistral_integration(image_path)
