import logging
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import pypdf
import io
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        # Na WSL/Linux ścieżki są zazwyczaj standardowe, nie trzeba definiować tesseract_cmd
        pass

    async def extract_text(self, file_content: bytes, filename: str) -> str:
        """
        Główna metoda orkiestrująca OCR.
        """
        try:
            filename = filename.lower()
            
            if filename.endswith('.pdf'):
                return await self._process_pdf_hybrid(file_content)
            elif filename.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.heic')):
                return await self._process_image(file_content)
            else:
                logger.warning(f"Nieznany format pliku: {filename}, próba potraktowania jako obraz.")
                return await self._process_image(file_content)

        except Exception as e:
            logger.error(f"Krytyczny błąd OCR dla {filename}: {str(e)}")
            raise

    async def _process_pdf_hybrid(self, file_content: bytes) -> str:
        """
        Strategia: Najpierw tekst cyfrowy (pypdf). Jak go mało -> renderowanie obrazu (OCR).
        """
        # 1. Próba Text Extraction (Idealne dla e-paragonów Biedronka/Kaufland)
        try:
            with io.BytesIO(file_content) as pdf_file:
                reader = pypdf.PdfReader(pdf_file)
                text_content = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text_content += extracted + "\n"
                
                # Heurystyka: Jeśli mamy > 50 znaków sensownego tekstu, ufamy PDF-owi.
                # To eliminuje potrzebę wolnego OCR dla czystych plików.
                if len(text_content.strip()) > 50:
                    logger.info("OCR: Wykryto warstwę tekstową PDF (e-paragon). Pomijam Tesseract.")
                    return text_content
        except Exception as e:
            logger.warning(f"OCR: Błąd pypdf: {e}. Przechodzę do renderowania obrazu.")

        # 2. Fallback: Renderowanie do obrazka (Dla skanów np. Auchan)
        logger.info("OCR: Uruchamiam renderowanie PDF do obrazów (skan)...")
        try:
            # convert_from_bytes wymaga poppler-utils zainstalowanego w systemie (apt install poppler-utils)
            images = convert_from_path(io.BytesIO(file_content)) 
            full_text = ""
            for image in images:
                processed_img = self._preprocess_image_cv2(image)
                # config psm 4 = Assume a single column of text of variable sizes (dobre dla paragonów)
                text = pytesseract.image_to_string(processed_img, lang='pol+eng', config='--psm 4')
                full_text += text + "\n"
            return full_text
        except Exception as e:
            logger.error(f"OCR: Błąd przetwarzania obrazów PDF: {e}")
            raise ValueError("Nie udało się przetworzyć PDF ani jako tekstu, ani jako obrazu.")

    async def _process_image(self, file_content: bytes) -> str:
        """
        Obsługa plików graficznych (Lidl).
        """
        image = Image.open(io.BytesIO(file_content))
        processed_image = self._preprocess_image_cv2(image)
        return pytesseract.image_to_string(processed_image, lang='pol+eng', config='--psm 4')

    def _preprocess_image_cv2(self, pil_image):
        """
        CV2 Magic: Naprawia oświetlenie, cienie i zagięcia (Adaptive Threshold).
        Kluczowe dla zdjęć z telefonu.
        """
        img_np = np.array(pil_image)
        
        # Konwersja kolorów
        if len(img_np.shape) == 3:
            if img_np.shape[2] == 4: # RGBA
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np

        # Odszumianie (zachowuje krawędzie liter, usuwa ziarno)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Progowanie adaptacyjne - zamienia na czarno-białe (binarne), radzi sobie z cieniami
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return Image.fromarray(binary)
