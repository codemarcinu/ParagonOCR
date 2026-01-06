import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

import pytest
import logging
from app.services.ocr_service import OCRService
import pytesseract
from pdf2image import convert_from_path, pdfinfo_from_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ocr_dependencies():
    print("Testing dependencies...")
    
    # 1. Check Tesseract
    try:
        ver = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract found: {ver}")
    except Exception as e:
        print(f"❌ Tesseract ERROR: {e}")
        print("Tesseract is required for image OCR.")

    # 2. Check Poppler (via pdf2image)
    try:
        # We don't have a PDF here, but we can check if poppler is in path by catching the specific error
        # or just instantiating. pdf2image doesn't expose a simple 'check' function without a file.
        # But importing it worked.
        # Let's try to run a dummy command if possible? No.
        # We will assume it's okay if import works, but runtime might fail.
        # Check if 'pdftoppm' is in path
        import shutil
        if shutil.which("pdftoppm"):
             print(f"✅ Poppler (pdftoppm) found in PATH")
        else:
             print(f"⚠️ Poppler (pdftoppm) NOT found in PATH. PDF to Image conversion will fail.")
    except Exception as e:
        print(f"❌ Poppler Check ERROR: {e}")

    # 3. Initialize Service
    try:
        service = OCRService()
        print("✅ OCRService initialized successfully")
    except Exception as e:
        print(f"❌ OCRService initialization ERROR: {e}")

if __name__ == "__main__":
    test_ocr_dependencies()
