import os
import tempfile
from pdf2image import convert_from_path
from typing import Optional
from PIL import Image


def convert_pdf_to_image(pdf_path: str) -> Optional[str]:
    """
    Konwertuje WSZYSTKIE strony pliku PDF i skleja je w jeden długi obraz (JPEG).
    """
    try:
        # Pobieramy wszystkie strony (usuwamy first_page/last_page)
        images = convert_from_path(pdf_path)

        if not images:
            print(f"BŁĄD: Nie udało się skonwertować PDF: {pdf_path}")
            return None

        # Jeśli jest jedna strona, zapisujemy jak dawniej
        if len(images) == 1:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                images[0].save(tmp_file.name, "JPEG")
                return tmp_file.name

        # Jeśli jest więcej stron, sklejamy je w pionie
        print(f"INFO: PDF ma {len(images)} stron. Sklejam w jeden obraz...")

        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)

        # Tworzymy pusty, długi obraz
        merged_image = Image.new("RGB", (total_width, total_height), (255, 255, 255))

        y_offset = 0
        for img in images:
            # Jeśli strony mają różną szerokość, centrujemy lub wyrównujemy do lewej (tu: lewa)
            merged_image.paste(img, (0, y_offset))
            y_offset += img.height

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            merged_image.save(tmp_file.name, "JPEG")
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
