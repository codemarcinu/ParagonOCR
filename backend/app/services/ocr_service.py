import os
import io
from app.config import settings

# Setup Google Cloud Credential path
POSSIBLE_KEYS = [
    os.path.join(os.getcwd(), "gcp_key.json"),
    os.path.join(os.path.dirname(os.getcwd()), "gcp_key.json"),
    "gcp_key.json"
]

KEY_PATH = None
for path in POSSIBLE_KEYS:
    if os.path.exists(path):
        KEY_PATH = path
        break

if KEY_PATH:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = KEY_PATH

class OCRService:
    async def extract_text(self, file_content: bytes, filename: str) -> str:
        """
        Sends image content directly to Google Cloud Vision and returns detected text.
        Obsługuje JPG/PNG oraz PDF (konwersja w locie).
        """
        # [LAZY LOAD] Import here to verify environment only when needed
        from google.cloud import vision

        # Check for credentials
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ and not os.path.exists(KEY_PATH):
             print("WARNING: GOOGLE_APPLICATION_CREDENTIALS not set and gcp_key.json not found.")

        try:
            client = vision.ImageAnnotatorClient()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Cloud Vision client. Ensure 'gcp_key.json' is present. Error: {str(e)}")

        content_to_send = None

        # 1. Obsługa PDF (Konwersja bajtów PDF na obraz)
        if filename.lower().endswith('.pdf'):
            try:
                from pdf2image import convert_from_bytes
                # Konwertujemy pierwszą stronę PDF z bajtów
                images = convert_from_bytes(file_content, first_page=1, last_page=1)
                if not images:
                    raise Exception("Pusty plik PDF")
                
                # Zapisujemy obraz do bufora w pamięci (RAM) jako JPEG
                # Resize if needed (reuse import from pdf2image dependency which uses PIL)
                from PIL import Image
                pil_image = images[0]
                width, height = pil_image.size
                max_dim = max(width, height)
                if max_dim > 4096:
                    scale = 4096 / max_dim
                    pil_image = pil_image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

                img_byte_arr = io.BytesIO()
                pil_image.save(img_byte_arr, format='JPEG', quality=85)
                content_to_send = img_byte_arr.getvalue()
            except Exception as e:
                # Fallback: Jeśli pdf2image zawiedzie, rzuć błąd (wymaga poppler-utils)
                raise Exception(f"Błąd konwersji PDF: {e}. Upewnij się, że masz zainstalowany poppler-utils.")

        # 2. Obsługa Obrazów (JPG, PNG) - bierzemy bajty jak leci
        else:
            content_to_send = self._preprocess_image(file_content)

        # 3. Wysyłka do Google
        image = vision.Image(content=content_to_send)

        # DOCUMENT_TEXT_DETECTION is optimized for dense text (receipts, documents)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(f'GCP Vision Error: {response.error.message}')

        full_text = response.full_text_annotation.text
        return full_text

    def _preprocess_image(self, image_content: bytes) -> bytes:
        """
        Resizes image if it exceeds 4096px on long edge.
        Converts to JPEG if not already.
        """
        from PIL import Image
        
        try:
            img = Image.open(io.BytesIO(image_content))
            
            # Check dimensions
            width, height = img.size
            max_dim = max(width, height)
            
            if max_dim > 4096:
                scale = 4096 / max_dim
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
            # Convert to RGB (remove alpha) and save as JPEG if needed
            # Always saving as JPEG with 85 quality to standardize and compress
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                
            out_buffer = io.BytesIO()
            img.save(out_buffer, format='JPEG', quality=85)
            return out_buffer.getvalue()
            
        except Exception as e:
            print(f"Warning: Image preprocessing failed: {e}")
            return image_content # Fallback to original