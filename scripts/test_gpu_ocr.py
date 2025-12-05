import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../ReceiptParser"))
)

from ReceiptParser.src.config import Config
from ReceiptParser.src.ocr import (
    extract_text_from_image_gpu,
    extract_text_from_image_tesseract,
)


def test_gpu_ocr():
    print("--- Testing GPU OCR (EasyOCR) ---")

    try:
        import torch

        print(f"Torch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU Name: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("Torch not installed!")
        return

    try:
        import easyocr

        print(f"EasyOCR version: {easyocr.__version__}")
    except ImportError:
        print("EasyOCR not installed!")
        return

    # Create a dummy image for testing if no image provided
    image_path = "test_image.png"
    if not os.path.exists(image_path):
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (400, 200), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Test Paragonu\nBiedronka\nSuma: 123.45", fill=(0, 0, 0))
        img.save(image_path)
        print(f"Created dummy image: {image_path}")

    # Test EasyOCR
    print("\nRunning EasyOCR...")
    start_time = time.time()
    text_easy = extract_text_from_image_gpu(image_path)
    end_time = time.time()
    print(f"EasyOCR Time: {end_time - start_time:.4f}s")
    print(f"EasyOCR Result (first 50 chars): {text_easy[:50].replace('\n', ' ')}...")

    # Test Tesseract
    print("\nRunning Tesseract...")
    start_time = time.time()
    text_tess = extract_text_from_image_tesseract(image_path)
    end_time = time.time()
    print(f"Tesseract Time: {end_time - start_time:.4f}s")
    print(f"Tesseract Result (first 50 chars): {text_tess[:50].replace('\n', ' ')}...")

    # Cleanup
    if os.path.exists("test_image.png"):
        os.remove("test_image.png")


if __name__ == "__main__":
    test_gpu_ocr()
