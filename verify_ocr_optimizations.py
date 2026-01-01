import os
import sys
import logging
from pathlib import Path

# Setup path to import app modules
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.ocr_service import preprocess_image, extract_from_image, settings
from app.services.llm_service import parse_receipt_text
from app.services.normalization import normalize_product_name, simple_polish_stemmer

# Setup Tesseract Path (detected on system)
settings.TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
import pytesseract
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def verify_pipeline():
    image_path = "d:\\projekty\\ParagonOCR\\paragony\\lidl.png"
    
    if not os.path.exists(image_path):
        print(f"File {image_path} not found.")
        return

    print(f"--- Verifying Preprocessing & OCR for {image_path} ---")
    
    # 1. Test Preprocessing
    try:
        processed_img = preprocess_image(image_path)
        print(f"Preprocessing successful. Image size: {processed_img.size}")
        processed_img.save("debug_preprocessed.png")
        print("Saved debug_preprocessed.png")
        
        # DEBUG: Try raw tesseract on original image
        import pytesseract
        from PIL import Image
        raw_img = Image.open(image_path)
        print("\n--- RAW TESSERACT DEBUG ---")
        try:
             text = pytesseract.image_to_string(raw_img, lang="pol+eng")
             print(f"Raw Tesseract (PSM 3) found {len(text)} chars info.")
             if len(text) < 100: print(f"Raw text: {text}")
        except Exception as e:
             print(f"Raw Tesseract failed: {e}")
        
        print("\n--- PREPROCESSED TESSERACT DEBUG ---")
        try:
             text = pytesseract.image_to_string(processed_img, lang="pol+eng", config="--psm 6")
             print(f"Preprocessed (PSM 6) found {len(text)} chars.")
        except Exception as e:
             print(f"Prep Tesseract failed: {e}")
             
    except Exception as e:
        print(f"Preprocessing failed: {e}")
        return

    # 2. Test OCR Extraction
    try:
        ocr_result = extract_from_image(image_path)
        print(f"\nOCR Result (Confidence: {ocr_result.confidence}):")
        if ocr_result.error:
            print(f"ERROR: {ocr_result.error}")
        print("-" * 40)
        print(ocr_result.text[:500] + "..." if len(ocr_result.text) > 500 else ocr_result.text)
        print("-" * 40)
    except Exception as e:
        print(f"OCR failed: {e}")
        return

    # 3. Test LLM Parsing
    print("\n--- Verifying LLM Parsing & Validation ---")
    try:
        # settings.TEXT_MODEL needs to be available
        parsed = parse_receipt_text(ocr_result.text)
        if parsed.error:
            print(f"LLM Parsing reported error: {parsed.error}")
        else:
            print("Parsed Data:")
            print(f"Shop: {parsed.shop}")
            print(f"Date: {parsed.date}")
            print(f"Total: {parsed.total}")
            print(f"Items: {len(parsed.items)}")
            for item in parsed.items[:3]: # Show first 3
                print(f" - {item['name']}: {item['quantity']} x {item['unit_price']} = {item['total_price']}")
    except Exception as e:
        print(f"LLM Parsing failed: {e}")

    # 4. Test Normalization Stemming
    print("\n--- Verifying Normalization Stemming ---")
    words = ["Bułka", "Bułki", "Bułkę", "Pomidory", "Pomidorów", "Mleko", "Mleka"]
    for w in words:
        print(f"{w} -> {simple_polish_stemmer(w)}")

if __name__ == "__main__":
    verify_pipeline()
