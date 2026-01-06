import logging
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from pdf2image import convert_from_path
import pypdf
import io
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        # Upewnij się, że ścieżka do tesseract jest poprawna w kontenerze/systemie
        # pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract' 
        pass

    async def extract_text(self, file_content: bytes, filename: str) -> str:
        """
        Główna metoda orkiestrująca. Rozpoznaje typ pliku i dobiera metodę.
        """
        try:
            filename = filename.lower()
            
            if filename.endswith('.pdf'):
                return await self._process_pdf_hybrid(file_content)
            elif filename.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
                return await self._process_image(file_content)
            else:
                raise ValueError(f"Nieobsługiwany format pliku: {filename}")

        except Exception as e:
            logger.error(f"Błąd OCR dla pliku {filename}: {str(e)}")
            raise

    async def _process_pdf_hybrid(self, file_content: bytes) -> str:
        """
        Strategia Hybrydowa dla PDF:
        1. Próba Text Extraction (pypdf) - dla e-paragonów (Biedronka, Lidl app, Auchan).
           Jest 100x szybsza i 100% dokładna.
        2. Fallback do OCR (pdf2image) - dla skanów/zdjęć w PDF.
        """
        # Krok 1: Próba wyciągnięcia tekstu cyfrowego
        try:
            with io.BytesIO(file_content) as pdf_file:
                reader = pypdf.PdfReader(pdf_file)
                text_content = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text_content += extracted + "\n"
                
                # Heurystyka: Jeśli mamy dużo tekstu, to prawdopodobnie e-paragon
                if len(text_content.strip()) > 50:
                    logger.info("Wykryto e-paragon (warstwa tekstowa). Pomijam OCR obrazkowy.")
                    return text_content
        except Exception as e:
            logger.warning(f"Nieudana ekstrakcja tekstu z PDF (może to skan?): {e}")

        # Krok 2: Fallback do renderowania obrazów i OCR (dla skanów)
        logger.info("Uruchamiam pełny OCR (renderowanie obrazu z PDF)...")
        try:
            images = convert_from_path(io.BytesIO(file_content)) # Wymaga poppler-utils w systemie
            full_text = ""
            for i, image in enumerate(images):
                # Preprocessing dla każdej strony
                processed_img = self._preprocess_image_cv2(image)
                text = pytesseract.image_to_string(processed_img, lang='pol+eng')
                full_text += text + "\n"
            return full_text
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania obrazów z PDF: {e}")
            # Ostatnia deska ratunku - pusty string lub błąd
            raise ValueError("Nie udało się przetworzyć pliku PDF ani tekstowo, ani obrazkowo.")

    async def _process_image(self, file_content: bytes) -> str:
        """
        Przetwarzanie obrazów (PNG/JPG) z zaawansowanym preprocessingiem (Lidl, pogniecione paragony).
        """
        image = Image.open(io.BytesIO(file_content))
        processed_image = self._preprocess_image_cv2(image)
        
        # Konfiguracja Tesseracta pod tabelki paragonowe
        custom_config = r'--oem 3 --psm 4' 
        return pytesseract.image_to_string(processed_image, lang='pol+eng', config=custom_config)

    def _preprocess_image_cv2(self, pil_image):
        """
        Czyści szumy, cienie i poprawia kontrast używając OpenCV.
        Kluczowe dla zdjęć z telefonu (np. Lidl).
        """
        # Konwersja PIL -> OpenCV
        img_np = np.array(pil_image)
        
        # Obsługa kanału alfa (przezroczystości) jeśli istnieje
        if len(img_np.shape) == 3 and img_np.shape[2] == 4:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
            
        # Konwersja na odcienie szarości
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_np

        # Odszumianie (zachowuje krawędzie liter)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        # Progowanie adaptacyjne (Adaptive Threshold) - kluczowe dla nierównego oświetlenia
        # Sprawia, że tekst jest czarny, tło białe, nawet jak pada cień
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        return Image.fromarray(binary)
