"""
Moduł bezpieczeństwa - funkcje walidacji i bezpiecznych operacji.
"""
import os
import stat
import tempfile
from pathlib import Path
from typing import Optional, List
from PIL import Image


# --- Stałe bezpieczeństwa ---
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_IMAGE_DIMENSIONS = (10000, 10000)  # Max szerokość/wysokość
ALLOWED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.pdf']
ALLOWED_LLM_MODELS = [
    "llava:latest",
    "SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M",
    "mistral-ocr",
]


# --- Walidacja ścieżek plików ---
def validate_file_path(
    file_path: str,
    allowed_extensions: Optional[List[str]] = None,
    check_exists: bool = True,
    max_size: Optional[int] = None
) -> Path:
    """
    Waliduje ścieżkę pliku i normalizuje ją.
    
    Args:
        file_path: Ścieżka do pliku
        allowed_extensions: Lista dozwolonych rozszerzeń (None = wszystkie)
        check_exists: Czy sprawdzać istnienie pliku
        max_size: Maksymalny rozmiar pliku w bajtach (None = użyj domyślnego)
    
    Returns:
        Znormalizowana ścieżka jako Path
    
    Raises:
        FileNotFoundError: Jeśli plik nie istnieje
        ValueError: Jeśli ścieżka jest nieprawidłowa
    """
    if not file_path:
        raise ValueError("Ścieżka pliku nie może być pusta")
    
    # Normalizuj ścieżkę (rozwiązuje .., ., symlinki)
    path = Path(file_path).resolve()
    
    # Sprawdź czy plik istnieje (jeśli wymagane)
    if check_exists:
        if not path.exists():
            raise FileNotFoundError(f"Plik nie istnieje: {file_path}")
        
        # Sprawdź czy to plik (nie katalog)
        if not path.is_file():
            raise ValueError(f"Ścieżka nie wskazuje na plik: {file_path}")
    
    # Sprawdź rozszerzenie (jeśli podano)
    if allowed_extensions:
        if path.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
            raise ValueError(
                f"Nieobsługiwane rozszerzenie pliku: {path.suffix}. "
                f"Dozwolone: {', '.join(allowed_extensions)}"
            )
    
    # Sprawdź rozmiar pliku (jeśli istnieje)
    if check_exists and path.exists():
        file_size = path.stat().st_size
        max_file_size = max_size if max_size is not None else MAX_FILE_SIZE
        if file_size > max_file_size:
            raise ValueError(
                f"Plik jest za duży: {file_size / 1024 / 1024:.2f} MB "
                f"(max {max_file_size / 1024 / 1024} MB)"
            )
    
    return path


def validate_image(image_path: str) -> None:
    """
    Waliduje obraz przed przetwarzaniem.
    
    Args:
        image_path: Ścieżka do obrazu
    
    Raises:
        ValueError: Jeśli obraz jest nieprawidłowy
    """
    path = validate_file_path(
        image_path,
        allowed_extensions=['.png', '.jpg', '.jpeg'],
        max_size=MAX_IMAGE_SIZE
    )
    
    # Sprawdź wymiary obrazu
    try:
        with Image.open(path) as img:
            width, height = img.size
            if width > MAX_IMAGE_DIMENSIONS[0] or height > MAX_IMAGE_DIMENSIONS[1]:
                raise ValueError(
                    f"Obraz za duży: {width}x{height} "
                    f"(max {MAX_IMAGE_DIMENSIONS[0]}x{MAX_IMAGE_DIMENSIONS[1]})"
                )
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Nie można otworzyć obrazu: {e}") from e


def validate_llm_model(model_name: str) -> str:
    """
    Waliduje nazwę modelu LLM.
    
    Args:
        model_name: Nazwa modelu
    
    Returns:
        Zwalidowana nazwa modelu
    
    Raises:
        ValueError: Jeśli model nie jest dozwolony
    """
    if not model_name:
        raise ValueError("Nazwa modelu nie może być pusta")
    
    if model_name not in ALLOWED_LLM_MODELS:
        raise ValueError(
            f"Model '{model_name}' nie jest dozwolony. "
            f"Dozwolone modele: {', '.join(ALLOWED_LLM_MODELS)}"
        )
    
    return model_name


# --- Bezpieczne pliki tymczasowe ---
def create_secure_temp_file(suffix: str = ".jpg") -> tuple[int, str]:
    """
    Tworzy bezpieczny plik tymczasowy z odpowiednimi uprawnieniami.
    
    Args:
        suffix: Rozszerzenie pliku
    
    Returns:
        Tuple (file_descriptor, path)
    """
    # Użyj mkstemp zamiast NamedTemporaryFile dla większej kontroli
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        # Ustaw uprawnienia: tylko właściciel może czytać/zapisywać
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        return fd, path
    except Exception:
        os.close(fd)
        os.unlink(path)
        raise


# --- Sanityzacja logów ---
def sanitize_path(path: str) -> str:
    """
    Usuwa wrażliwe informacje ze ścieżki.
    
    Args:
        path: Pełna ścieżka
    
    Returns:
        Tylko nazwa pliku (bez ścieżki)
    """
    return Path(path).name


def sanitize_log_message(message: str, max_length: int = 200) -> str:
    """
    Ogranicza długość wiadomości logowania i usuwa znaki kontrolne.
    
    Args:
        message: Wiadomość do sanityzacji
        max_length: Maksymalna długość
    
    Returns:
        Zsanityzowana wiadomość
    """
    import re
    
    # Usuń znaki kontrolne (oprócz \n, \t)
    message = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', message)
    
    # Ogranicz długość
    if len(message) > max_length:
        return message[:max_length] + f"... [obcięte, długość: {len(message)}]"
    
    return message


def sanitize_ocr_text(text: str, max_length: int = 200) -> str:
    """
    Sanityzuje tekst OCR do logowania.
    
    Args:
        text: Tekst OCR
        max_length: Maksymalna długość do wyświetlenia
    
    Returns:
        Zsanityzowany tekst
    """
    if not text:
        return ""
    
    if len(text) > max_length:
        return f"{text[:max_length]}... [obcięte, długość: {len(text)}]"
    
    return text






