
import sys
import os
from pathlib import Path

# Add backend to path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root / 'backend'))

from app.services.ocr_service import extract_from_image
from app.config import settings

# Path to the uploaded image
image_path = r"C:/Users/marci/.gemini/antigravity/brain/0bfa5708-5f2f-4351-a31d-eb49ee22dc0e/uploaded_image_1767693508227.png"

print(f"Testing OCR on: {image_path}")

try:
    result = extract_from_image(image_path)
    print("\n--- OCR Text Start ---")
    print(result.text)
    print("--- OCR Text End ---")
    print(f"\nTotal characters: {len(result.text)}")
    print(f"Confidence: {result.confidence}")
    print(f"Error: {result.error}")
except Exception as e:
    print(f"Error running OCR: {e}")
