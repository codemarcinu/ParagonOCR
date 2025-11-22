import os
from mistralai import Mistral
from .config import Config
from .security import validate_file_path, sanitize_path, sanitize_log_message


class MistralOCRClient:
    def __init__(self):
        self.api_key = Config.MISTRAL_API_KEY
        if not self.api_key:
            print(
                "OSTRZEŻENIE: Brak klucza API Mistral (MISTRAL_API_KEY). OCR nie zadziała."
            )
            self.client = None
        else:
            self.client = Mistral(api_key=self.api_key)

    def process_image(self, image_path: str) -> str | None:
        """
        Wysyła obraz do Mistral OCR i zwraca wyekstrahowany tekst (markdown).
        """
        if not self.client:
            print("BŁĄD: Klient Mistral nie jest zainicjalizowany (brak klucza API).")
            return None

        try:
            # Waliduj ścieżkę pliku
            validated_path = validate_file_path(
                image_path,
                allowed_extensions=['.png', '.jpg', '.jpeg', '.pdf'],
                max_size=50 * 1024 * 1024  # 50 MB
            )
            image_path = str(validated_path)
            
            print(f"INFO: Wysyłanie pliku do Mistral OCR: {sanitize_path(image_path)}")

            uploaded_file = self.client.files.upload(
                file={
                    "file_name": os.path.basename(image_path),
                    "content": open(image_path, "rb"),
                },
                purpose="ocr",
            )

            signed_url = self.client.files.get_signed_url(file_id=uploaded_file.id)

            ocr_response = self.client.ocr.process(
                document={
                    "type": "document_url",
                    "document_url": signed_url.url,
                },
                model="mistral-ocr-latest",
                include_image_base64=False,
            )

            # Sklejamy markdown ze wszystkich stron
            full_markdown = ""
            for page in ocr_response.pages:
                full_markdown += page.markdown + "\n\n"

            return full_markdown

        except FileNotFoundError:
            print(f"BŁĄD: Plik nie istnieje: {sanitize_path(image_path)}")
            return None
        except ValueError as e:
            print(f"BŁĄD WALIDACJI: {sanitize_log_message(str(e))}")
            return None
        except Exception as e:
            print(f"BŁĄD: Wystąpił błąd podczas komunikacji z Mistral OCR: {sanitize_log_message(str(e))}")
            return None
