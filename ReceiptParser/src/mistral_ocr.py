import os
from mistralai import Mistral
from .config import Config


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

        if not os.path.exists(image_path):
            print(f"BŁĄD: Plik nie istnieje: {image_path}")
            return None

        try:
            print(f"INFO: Wysyłanie pliku do Mistral OCR: {image_path}")

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

        except Exception as e:
            print(f"BŁĄD: Wystąpił błąd podczas komunikacji z Mistral OCR: {e}")
            return None
