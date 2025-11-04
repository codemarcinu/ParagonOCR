
import os
from pathlib import Path
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
from PIL import Image
from pdf2image import convert_from_path, pdfinfo_from_path
from typing import List

# --- Konfiguracja --- 
# Opcjonalnie: Jeśli Tesseract nie jest w Twojej ścieżce PATH, wskaż jego lokalizację.
# Przykład dla Windows: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Przykład dla Linux (jeśli zainstalowany w niestandardowym miejscu): pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract'

def extract_text_from_file(file_path: str) -> str:
    """
    Wyciąga tekst z pliku (PDF, PNG, JPG/JPEG) używając silnika Tesseract OCR.

    Args:
        file_path: Absolutna ścieżka do pliku.

    Returns:
        Wyciągnięty tekst jako pojedynczy, długi string. Tekst z każdej strony
        (w przypadku PDF) jest oddzielony znacznikiem.

    Raises:
        FileNotFoundError: Jeśli plik pod podaną ścieżką nie istnieje.
        ValueError: Jeśli format pliku nie jest obsługiwany (inny niż PDF, PNG, JPG, JPEG).
        pytesseract.TesseractNotFoundError: Jeśli Tesseract nie jest zainstalowany lub dostępny.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Plik nie został znaleziony pod ścieżką: {file_path}")

    file_extension = Path(file_path).suffix.lower()
    images: List[Image.Image] = []

    print(f"Przetwarzanie pliku: {file_path}")

    if file_extension == '.pdf':
        print("Wykryto plik PDF. Konwertowanie na obrazy...")
        try:
            # Sprawdzenie, czy PDF nie jest pusty/uszkodzony
            pdfinfo_from_path(file_path)
            images = convert_from_path(file_path, dpi=300) # Zwiększamy DPI dla lepszej jakości OCR
            print(f"Pomyślnie przekonwertowano {len(images)} stron PDF.")
        except Exception as e:
            print(f"Krytyczny błąd podczas konwersji PDF: {e}")
            print("Upewnij się, że biblioteka 'poppler' jest zainstalowana w systemie.")
            # Rzucamy błąd dalej, bo bez tego nie możemy kontynuować
            raise

    elif file_extension in ['.png', '.jpg', '.jpeg']:
        print("Wykryto plik obrazu. Wczytywanie...")
        images = [Image.open(file_path)]
    else:
        raise ValueError(
            f"""Nieobsługiwany format pliku: '{file_extension}'.
Obsługiwane formaty to: .pdf, .png, .jpg, .jpeg."""
        )

    if not images:
        print("Nie znaleziono obrazów do przetworzenia.")
        return ""

    # Przetwarzanie OCR dla każdego obrazu (strony)
    full_text_parts = []
    for i, image in enumerate(images):
        page_num = i + 1
        print(f"Przetwarzanie OCR dla strony/obrazu {page_num}/{len(images)}...")
        try:
            # Używamy języka polskiego (lang='pol') dla Tesseract
            text = pytesseract.image_to_string(image, lang='pol')
            full_text_parts.append(text)
        except pytesseract.TesseractNotFoundError as e:
            print("\nBŁĄD KRYTYCZNY: Nie znaleziono instalacji Tesseract OCR.")
            print("Upewnij się, że Tesseract jest zainstalowany i dostępny w systemowej ścieżce PATH.")
            print(f"Oryginalny błąd: {e}")
            raise
        except Exception as e:
            print(f"Nieoczekiwany błąd podczas przetwarzania OCR strony {page_num}: {e}")
            # Kontynuujemy, aby spróbować przetworzyć inne strony
            continue

    print("Zakończono przetwarzanie OCR.")
    # Złączenie tekstu ze wszystkich stron w jeden string
    return "\n\n--- Koniec Strony ---\n\n".join(full_text_parts)


if __name__ == '__main__':
    # --- PRZYKŁAD UŻYCIA (do celów testowych) ---
    # Aby ten kod zadziałał, musisz mieć:
    # 1. Zainstalowany silnik Tesseract OCR w systemie.
    # 2. Zainstalowany pakiet 'poppler' (dla obsługi PDF w pdf2image).
    # 3. Utworzony folder 'data/receipts' w głównym katalogu projektu.

    print("Uruchomiono skrypt ocr.py w trybie testowym.")

    # Przygotowanie środowiska testowego
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "data" / "receipts"
    test_dir.mkdir(exist_ok=True)

    # Tworzenie sztucznego obrazu paragonu do testów
    img_path = test_dir / "example_receipt.png"
    try:
        from PIL import ImageDraw, ImageFont

        img = Image.new('RGB', (600, 300), color='white')
        draw = ImageDraw.Draw(img)
        try:
            # Użyjmy popularnej czcionki, jeśli jest dostępna
            font = ImageFont.truetype("DejaVuSans.ttf", 18)
        except IOError:
            print("Czcionka DejaVuSans.ttf nie znaleziona, używam domyślnej.")
            font = ImageFont.load_default()
        
        receipt_text = ( 
            "Paragon Fiskalny\n" 
            "Sklep XYZ\n" 
            "ul. Testowa 1, 00-001 Warszawa\n" 
            "------------------------------\n" 
            "Mleko 3,2%         1 szt. x 3.50   3.50\n" 
            "Chleb              1 szt. x 4.20   4.20\n" 
            "SUMA PLN                         7.70\n"
        )
        draw.text((10, 10), receipt_text, fill='black', font=font)
        img.save(img_path)
        print(f"\nUtworzono testowy obraz paragonu: {img_path}")

        # Testowanie funkcji na stworzonym obrazie
        print("\n--- Test 1: Przetwarzanie pliku PNG ---")
        extracted_text = extract_text_from_file(str(img_path))
        print("\nWynik OCR:")
        print("------------------------------")
        print(extracted_text.strip())
        print("------------------------------")

    except ImportError:
        print("Pominięto tworzenie obrazu testowego: PIL/Pillow nie jest w pełni zainstalowany.")
    except Exception as e:
        print(f"Wystąpił błąd podczas testu z plikiem PNG: {e}")

    # Testowanie obsługi błędów
    print("\n--- Test 2: Nieistniejący plik ---")
    try:
        extract_text_from_file("sciezka/do/nieistniejacego/pliku.jpg")
    except FileNotFoundError as e:
        print(f"Złapano oczekiwany błąd: {e}")

    print("\n--- Test 3: Nieobsługiwany format pliku ---")
    unsupported_file = test_dir / "plik.txt"
    unsupported_file.write_text("To jest zwykły tekst.")
    try:
        extract_text_from_file(str(unsupported_file))
    except ValueError as e:
        print(f"Złapano oczekiwany błąd: {e}")
