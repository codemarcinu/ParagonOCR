import os
import tempfile
from pdf2image import convert_from_path
from typing import Optional
from PIL import Image
from .security import create_secure_temp_file, validate_file_path


def convert_pdf_to_image(pdf_path: str) -> Optional[str]:
    """
    Konwertuje WSZYSTKIE strony pliku PDF i skleja je w jeden długi obraz (JPEG).
    Używa bezpiecznych plików tymczasowych z odpowiednimi uprawnieniami.
    """
    temp_file_path = None
    try:
        # Waliduj ścieżkę PDF
        pdf_path_validated = validate_file_path(
            pdf_path,
            allowed_extensions=['.pdf'],
            max_size=100 * 1024 * 1024  # 100 MB dla PDF
        )
        
        # Pobieramy wszystkie strony (usuwamy first_page/last_page)
        images = convert_from_path(str(pdf_path_validated))

        if not images:
            print(f"BŁĄD: Nie udało się skonwertować PDF: {pdf_path}")
            return None

        # Jeśli jest jedna strona, zapisujemy jak dawniej
        if len(images) == 1:
            fd, temp_file_path = create_secure_temp_file(suffix=".jpg")
            try:
                with os.fdopen(fd, 'wb') as tmp_file:
                    images[0].save(tmp_file.name, "JPEG")
                return temp_file_path
            except Exception:
                os.close(fd)
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                raise

        # Jeśli jest więcej stron, sklejamy je w pionie
        print(f"INFO: PDF ma {len(images)} stron. Sklejam w jeden obraz...")

        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)

        # Sprawdź czy wynikowy obraz nie jest za duży
        MAX_MERGED_IMAGE_SIZE = 20000  # Max wymiar
        if total_width > MAX_MERGED_IMAGE_SIZE or total_height > MAX_MERGED_IMAGE_SIZE:
            raise ValueError(
                f"Wynikowy obraz po sklejeniu jest za duży: {total_width}x{total_height} "
                f"(max {MAX_MERGED_IMAGE_SIZE}x{MAX_MERGED_IMAGE_SIZE})"
            )

        # Tworzymy pusty, długi obraz
        merged_image = Image.new("RGB", (total_width, total_height), (255, 255, 255))

        y_offset = 0
        for img in images:
            # Jeśli strony mają różną szerokość, centrujemy lub wyrównujemy do lewej (tu: lewa)
            merged_image.paste(img, (0, y_offset))
            y_offset += img.height

        fd, temp_file_path = create_secure_temp_file(suffix=".jpg")
        try:
            with os.fdopen(fd, 'wb') as tmp_file:
                merged_image.save(tmp_file.name, "JPEG")
            return temp_file_path
        except Exception:
            os.close(fd)
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise

    except Exception as e:
        # Cleanup w przypadku błędu
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
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
        # Waliduj ścieżkę i obraz przed przetwarzaniem
        from .security import validate_image
        validate_image(image_path)
        
        # Otwieramy obraz
        img = Image.open(image_path)
        # Używamy pytesseract do ekstrakcji tekstu (język polski + angielski)
        text = pytesseract.image_to_string(img, lang="pol+eng")
        return text
    except Exception as e:
        print(f"BŁĄD: Nie udało się wyciągnąć tekstu z obrazu za pomocą Tesseract: {e}")
        return ""
