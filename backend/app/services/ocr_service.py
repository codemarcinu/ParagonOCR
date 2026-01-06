import os
import io
from google.cloud import vision
from app.config import settings

# Setup Google Cloud Credential path
KEY_PATH = os.path.join(os.getcwd(), "gcp_key.json")
if os.path.exists(KEY_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_PATH

class OCRService:
    def parse_receipt(self, file_path: str) -> str:
        """
        Sends image to Google Cloud Vision and returns detected text.
        Obsługuje JPG/PNG bezpośrednio.
        PDF konwertuje w locie na obraz (pierwszą stronę).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check for credentials
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ and not os.path.exists(KEY_PATH):
             print("WARNING: GOOGLE_APPLICATION_CREDENTIALS not set and gcp_key.json not found.")

        try:
            client = vision.ImageAnnotatorClient()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Cloud Vision client. Ensure 'gcp_key.json' is present. Error: {str(e)}")

        content = None

        # 1. Obsługa PDF (Konwersja do bajtów obrazu)
        if file_path.lower().endswith('.pdf'):
            try:
                from pdf2image import convert_from_path
                # Konwertujemy pierwszą stronę PDF na obraz
                images = convert_from_path(file_path, first_page=1, last_page=1)
                if not images:
                    raise Exception("Pusty plik PDF")
                
                # Zapisujemy obraz do bufora w pamięci (RAM) jako JPEG
                img_byte_arr = io.BytesIO()
                images[0].save(img_byte_arr, format='JPEG')
                content = img_byte_arr.getvalue()
            except Exception as e:
                raise Exception(f"Błąd konwersji PDF: {e}")

        # 2. Obsługa Obrazów (JPG, PNG)
        else:
            with io.open(file_path, 'rb') as image_file:
                content = image_file.read()

        # 3. Wysyłka do Google
        image = vision.Image(content=content)

        # DOCUMENT_TEXT_DETECTION is optimized for dense text (receipts, documents)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(f'GCP Vision Error: {response.error.message}')

        full_text = response.full_text_annotation.text
        return full_text
