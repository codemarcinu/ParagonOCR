import os
import tempfile
from pdf2image import convert_from_path
from typing import Optional


def convert_pdf_to_image(pdf_path: str) -> Optional[str]:
    """
    Konwertuje pierwszą stronę pliku PDF na obraz (JPEG) i zwraca ścieżkę do pliku tymczasowego.
    Wymaga zainstalowanego w systemie 'poppler-utils'.

    Args:
        pdf_path: Ścieżka do pliku PDF.

    Returns:
        Ścieżka do tymczasowego pliku obrazu lub None w przypadku błędu.
    """
    try:
        # Konwertujemy tylko pierwszą stronę
        images = convert_from_path(pdf_path, first_page=1, last_page=1)

        if not images:
            print(f"BŁĄD: Nie udało się skonwertować PDF: {pdf_path}")
            return None

        # Zapisujemy obraz do pliku tymczasowego
        # Używamy delete=False, aby plik nie zniknął od razu po zamknięciu (będziemy go potrzebować w innym miejscu)
        # Użytkownik (caller) jest odpowiedzialny za usunięcie tego pliku.
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            images[0].save(tmp_file.name, "JPEG")
            return tmp_file.name

    except Exception as e:
        print(f"BŁĄD Krytyczny podczas konwersji PDF na obraz: {e}")
        return None


import pytesseract
from PIL import Image


def extract_text_from_image(image_path: str) -> str:
    """
    Wyciąga surowy tekst z obrazu za pomocą Tesseract OCR.
    Służy do wstępnej analizy nagłówka paragonu (wykrywanie sklepu).

    Args:
        image_path: Ścieżka do pliku obrazu.

    Returns:
        Wyciągnięty tekst jako string.
    """
    try:
        # Otwieramy obraz
        img = Image.open(image_path)
        # Używamy pytesseract do ekstrakcji tekstu (język polski + angielski)
        text = pytesseract.image_to_string(img, lang="pol+eng")
        return text
    except Exception as e:
        print(f"BŁĄD: Nie udało się wyciągnąć tekstu z obrazu za pomocą Tesseract: {e}")
        return ""
