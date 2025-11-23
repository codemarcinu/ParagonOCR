"""
Abstrakcje dla dostawców OCR.

Wspiera:
- Mistral OCR (Cloud)
- Tesseract (Local)
"""

from abc import ABC, abstractmethod
from typing import Optional
import pytesseract
from PIL import Image

from .config import Config
from .mistral_ocr import MistralOCRClient
from .ocr import extract_text_from_image
from .security import validate_file_path, sanitize_path


class OCRProvider(ABC):
    """Abstrakcyjna klasa bazowa dla dostawców OCR."""
    
    @abstractmethod
    def extract_text(self, image_path: str) -> str:
        """
        Wyciąga tekst z obrazu.
        
        Args:
            image_path: Ścieżka do pliku obrazu
            
        Returns:
            Wyekstrahowany tekst (markdown dla Mistral, zwykły tekst dla Tesseract)
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Sprawdza czy dostawca jest dostępny."""
        pass


class MistralCloudOCR(OCRProvider):
    """Dostawca OCR używający Mistral OCR API."""
    
    def __init__(self):
        """Inicjalizuje klienta Mistral OCR."""
        self.client = MistralOCRClient()
    
    def extract_text(self, image_path: str) -> str:
        """Wyciąga tekst używając Mistral OCR."""
        # Waliduj ścieżkę
        validated_path = validate_file_path(
            image_path,
            allowed_extensions=['.png', '.jpg', '.jpeg', '.pdf'],
            max_size=50 * 1024 * 1024  # 50 MB
        )
        
        result = self.client.process_image(str(validated_path))
        if not result:
            raise RuntimeError("Mistral OCR nie zwrócił wyniku")
        return result
    
    def is_available(self) -> bool:
        """Sprawdza czy Mistral OCR jest dostępne."""
        return self.client.client is not None


class LocalTesseractOCR(OCRProvider):
    """Dostawca OCR używający lokalnego Tesseract."""
    
    def extract_text(self, image_path: str) -> str:
        """Wyciąga tekst używając Tesseract."""
        # Waliduj ścieżkę
        validated_path = validate_file_path(
            image_path,
            allowed_extensions=['.png', '.jpg', '.jpeg'],
        )
        
        return extract_text_from_image(str(validated_path))
    
    def is_available(self) -> bool:
        """Sprawdza czy Tesseract jest dostępne."""
        try:
            # Proste sprawdzenie - próba wywołania pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False


def get_ocr_provider(use_cloud: bool = None) -> OCRProvider:
    """
    Factory function do tworzenia odpowiedniego dostawcy OCR.
    
    Args:
        use_cloud: True dla Mistral OCR, False dla Tesseract (domyślnie z Config)
        
    Returns:
        Instancja OCRProvider
    """
    if use_cloud is None:
        use_cloud = Config.USE_CLOUD_OCR
    
    if use_cloud:
        return MistralCloudOCR()
    else:
        return LocalTesseractOCR()





