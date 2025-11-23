import sys
import os

# Dodaj ścieżkę do modułów (scripts/ jest w głównym katalogu, ReceiptParser/ też)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ReceiptParser'))

from src.ocr import convert_pdf_to_image, extract_text_from_image

pdf_path = "/home/marcin/Projekty/ParagonOCR/data/paragony/Biedra20251118.pdf"

print(f"Testing PDF: {pdf_path}")
try:
    image_path = convert_pdf_to_image(pdf_path)
    print(f"Converted to image: {image_path}")

    text = extract_text_from_image(image_path)
    print(f"--- Extracted Text ({len(text)} chars) ---")
    print(text[:1000])  # Print first 1000 chars
    print("------------------------------------------")

    # Clean up
    if os.path.exists(image_path):
        os.remove(image_path)

except Exception as e:
    print(f"Error: {e}")
