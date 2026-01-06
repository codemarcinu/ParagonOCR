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
import pypdf

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


import cv2
import numpy as np

def preprocess_image(image_path: str) -> Image.Image:
    """
    Preprocess image for better OCR accuracy using OpenCV.
    Includes Rescaling, CLAHE/Thresholding, and Deskewing.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Preprocessed PIL Image
    """
    # Read image using OpenCV
    img = cv2.imread(image_path)
    
    # Check if image was loaded successfully
    if img is None:
        return Image.open(image_path)
    
    # 1. Resize/Upscale if too small (Tesseract needs ~300 DPI)
    # Receipts are often long but narrow. Width is key.
    target_width = 1600
    h, w = img.shape[:2]
    
    if w < target_width:
        scale = target_width / w
        new_w = target_width
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
    # 2. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Optimization for Digital Screens / Screenshots
    unique_colors = np.unique(gray)
    is_digital = len(unique_colors) < 100 
    
    if is_digital:
        # Simple thresholding for clean digital images
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        # Standard processing for Photos/Scans
        
        # Denoise first
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Adaptive Thresholding is often better for receipts with shadows/uneven light
        # Block size 31, C=10 seems robust for documents
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 31, 12
        )
        
    # 3. Deskewing
    try:
        coords = np.column_stack(np.where(thresh > 0)) # White text on black? Adaptive gives Black text on White usually.
        # Check background color - usually receipts are white (255)
        # If mean pixel value > 127, it's black text on white bg (normal)
        if np.mean(thresh) > 127:
            # Invert for contour detection
            coords = np.column_stack(np.where(thresh == 0))
        else:
             coords = np.column_stack(np.where(thresh > 0))
             
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
                
            if abs(angle) > 0.5 and abs(angle) < 45: # Limit rotation to avoid flipping
                (h, w) = img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                # Fill border with white (255)
                thresh = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
    except Exception as e:
        pass
    
    # Save debug image if needed
    if settings.DEBUG:
         cv2.imwrite("last_preprocessed.jpg", thresh)

    return Image.fromarray(thresh)


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
        # Set tesseract command
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

        # OPTIMIZATION: Try native PDF extraction first
        try:
            reader = pypdf.PdfReader(file_path)
            text_content = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content += extracted + "\n"
            
            # If we got meaningful text, return it immediately
            if len(text_content.strip()) > 20:
                return OCRResult(
                    text=text_content.strip(),
                    confidence=1.0, # Native text is exact
                    engine="pypdf",
                )
        except Exception as e:
            # Fallback to OCR if pypdf fails
            pass
        
        # Convert PDF to image(s)
        images = convert_from_path(
            file_path,
            poppler_path=settings.POPPLER_PATH
        )
        
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
    Extract text using Tesseract OCR with layout preservation.
    
    Args:
        img: PIL Image object
        
    Returns:
        OCRResult with extracted text
    """
    try:
        # Set tesseract command
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        
        # Use --psm 4 (Assume a single column of text of variable sizes) - best for receipts
        custom_config = r'--psm 4'
        
        # Get verbose data (boxes, confidences, line numbers)
        data = pytesseract.image_to_data(img, lang="pol+eng", config=custom_config, output_type=pytesseract.Output.DICT)
        
        # Debug Tesseract output
        # print(f"DEBUG: Found {len(data['text'])} items")
        # print(f"DEBUG: Sample texts: {data['text'][:20]}")
        
        # Reconstruct text line by line
        # data keys: level, page_num, block_num, par_num, line_num, word_num, left, top, width, height, conf, text
        
        lines = {}
        confidences = []
        
        num_boxes = len(data['text'])
        for i in range(num_boxes):
            if int(data['conf'][i]) > -1:
                # Store confidence
                confidences.append(int(data['conf'][i]))
                
                # Group by (block, paragraph, line)
                # However, for receipts, simple Y-coordinate clustering might be better if PSM 4 fails,
                # but let's trust Tesseract's line detection first.
                key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
                
                if key not in lines:
                    lines[key] = []
                    
                text_val = data['text'][i].strip()
                if text_val:
                    lines[key].append(text_val)
        
        # Sort lines by vertical position (block/par/line numbers mostly usually sequential)
        # But let's verify visual order if needed. Tesseract output is usually in reading order.
        sorted_keys = sorted(lines.keys())
        
        final_text_parts = []
        for key in sorted_keys:
            line_text = " ".join(lines[key])
            if line_text:
                final_text_parts.append(line_text)
                
        text = "\n".join(final_text_parts)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
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

