"""
OCR Service for extracting text from PDFs and images.

Supports Tesseract and EasyOCR engines with image preprocessing.
"""

import os
import tempfile
from typing import Optional
from pathlib import Path
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

from app.config import settings


class OCRResult:
    """Structured OCR result with text and confidence scores."""
    
    def __init__(
        self,
        text: str,
        confidence: float = 0.0,
        engine: str = "tesseract",
        error: Optional[str] = None,
    ):
        self.text = text
        self.confidence = confidence
        self.engine = engine
        self.error = error
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "engine": self.engine,
            "error": self.error,
        }


def preprocess_image(image_path: str) -> Image.Image:
    """
    Preprocess image for better OCR accuracy.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Preprocessed PIL Image
    """
    img = Image.open(image_path)
    
    # Convert to RGB if necessary
    if img.mode != "RGB":
        img = img.convert("RGB")
    
    # Optional: Add more preprocessing here
    # - Deskewing
    # - Denoising
    # - Contrast enhancement
    
    return img


def extract_from_pdf(file_path: str) -> OCRResult:
    """
    Extract text from PDF file using Tesseract OCR.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        OCRResult with extracted text
    """
    temp_image_path = None
    try:
        # Convert PDF to image(s)
        images = convert_from_path(file_path)
        
        if not images:
            return OCRResult(
                text="",
                confidence=0.0,
                engine="tesseract",
                error="Failed to convert PDF to images",
            )
        
        # If multiple pages, merge them vertically
        if len(images) == 1:
            image = images[0]
        else:
            # Merge multiple pages
            total_width = max(img.width for img in images)
            total_height = sum(img.height for img in images)
            
            merged_image = Image.new("RGB", (total_width, total_height), (255, 255, 255))
            y_offset = 0
            for img in images:
                merged_image.paste(img, (0, y_offset))
                y_offset += img.height
            image = merged_image
        
        # Save to temporary file for OCR
        temp_fd, temp_image_path = tempfile.mkstemp(suffix=".jpg")
        os.close(temp_fd)
        image.save(temp_image_path, "JPEG")
        
        # Extract text using Tesseract
        return extract_from_image(temp_image_path)
        
    except Exception as e:
        return OCRResult(
            text="",
            confidence=0.0,
            engine="tesseract",
            error=f"Error processing PDF: {str(e)}",
        )
    finally:
        # Cleanup temporary file
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.unlink(temp_image_path)
            except Exception:
                pass


def extract_from_image(file_path: str) -> OCRResult:
    """
    Extract text from image file using configured OCR engine.
    
    Args:
        file_path: Path to image file
        
    Returns:
        OCRResult with extracted text
    """
    try:
        # Preprocess image
        img = preprocess_image(file_path)
        
        # Use configured OCR engine
        if settings.OCR_ENGINE.lower() == "easyocr":
            return _extract_with_easyocr(file_path)
        else:
            return _extract_with_tesseract(img)
            
    except Exception as e:
        return OCRResult(
            text="",
            confidence=0.0,
            engine=settings.OCR_ENGINE,
            error=f"Error processing image: {str(e)}",
        )


def _extract_with_tesseract(img: Image.Image) -> OCRResult:
    """
    Extract text using Tesseract OCR.
    
    Args:
        img: PIL Image object
        
    Returns:
        OCRResult with extracted text
    """
    try:
        # Extract text with Polish and English language support
        text = pytesseract.image_to_string(img, lang="pol+eng")
        
        # Try to get confidence scores (if available)
        try:
            data = pytesseract.image_to_data(img, lang="pol+eng", output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data["conf"] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        except Exception:
            avg_confidence = 0.0
        
        return OCRResult(
            text=text.strip(),
            confidence=avg_confidence / 100.0,  # Normalize to 0-1
            engine="tesseract",
        )
    except Exception as e:
        return OCRResult(
            text="",
            confidence=0.0,
            engine="tesseract",
            error=f"Tesseract error: {str(e)}",
        )


def _extract_with_easyocr(file_path: str) -> OCRResult:
    """
    Extract text using EasyOCR (GPU/CPU).
    
    Args:
        file_path: Path to image file
        
    Returns:
        OCRResult with extracted text
    """
    try:
        import easyocr
        import torch
        
        use_gpu = settings.USE_GPU_OCR and torch.cuda.is_available()
        reader = easyocr.Reader(["pl", "en"], gpu=use_gpu, verbose=False)
        result = reader.readtext(file_path, detail=0, paragraph=True)
        
        text = "\n".join(result)
        
        return OCRResult(
            text=text.strip(),
            confidence=0.8,  # EasyOCR doesn't provide easy confidence access
            engine="easyocr",
        )
    except ImportError:
        return OCRResult(
            text="",
            confidence=0.0,
            engine="easyocr",
            error="EasyOCR not installed. Install with: pip install easyocr",
        )
    except Exception as e:
        return OCRResult(
            text="",
            confidence=0.0,
            engine="easyocr",
            error=f"EasyOCR error: {str(e)}",
        )

