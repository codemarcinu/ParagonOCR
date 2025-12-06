import os
from mistralai import Mistral
from .config import Config
from .security import validate_file_path, sanitize_path, sanitize_log_message
from .retry_handler import retry_with_backoff


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

    @retry_with_backoff(
        max_retries=Config.RETRY_MAX_ATTEMPTS,
        initial_delay=Config.RETRY_INITIAL_DELAY,
        backoff_factor=Config.RETRY_BACKOFF_FACTOR,
        max_delay=Config.RETRY_MAX_DELAY,
        jitter=Config.RETRY_JITTER,
    )
    def _upload_file(self, image_path: str):
        """Pomocnicza metoda do uploadu pliku z retry."""
        return self.client.files.upload(
            file={
                "file_name": os.path.basename(image_path),
                "content": open(image_path, "rb"),
            },
            purpose="ocr",
        )

    @retry_with_backoff(
        max_retries=Config.RETRY_MAX_ATTEMPTS,
        initial_delay=Config.RETRY_INITIAL_DELAY,
        backoff_factor=Config.RETRY_BACKOFF_FACTOR,
        max_delay=Config.RETRY_MAX_DELAY,
        jitter=Config.RETRY_JITTER,
    )
    def _get_signed_url(self, file_id: str):
        """Pomocnicza metoda do pobrania signed URL z retry."""
        return self.client.files.get_signed_url(file_id=file_id)

    @retry_with_backoff(
        max_retries=Config.RETRY_MAX_ATTEMPTS,
        initial_delay=Config.RETRY_INITIAL_DELAY,
        backoff_factor=Config.RETRY_BACKOFF_FACTOR,
        max_delay=Config.RETRY_MAX_DELAY,
        jitter=Config.RETRY_JITTER,
    )
    def _process_ocr(self, document_url: str):
        """Pomocnicza metoda do przetwarzania OCR z retry."""
        return self.client.ocr.process(
            document={
                "type": "document_url",
                "document_url": document_url,
            },
            model="mistral-ocr-latest",
            include_image_base64=False,
        )

    def process_image(self, image_path: str) -> str | None:
        """
        Wysyła obraz do Mistral OCR i zwraca wyekstrahowany tekst (markdown).
        Automatycznie retry'uje w przypadku błędów sieciowych.
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

            uploaded_file = self._upload_file(image_path)
            signed_url = self._get_signed_url(uploaded_file.id)
            ocr_response = self._process_ocr(signed_url.url)

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
