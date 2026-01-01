
import os
import sys
import logging
import asyncio
from typing import List
from pathlib import Path
from decimal import Decimal

# Setup path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock database session for normalization
from unittest.mock import MagicMock
mock_db = MagicMock()

# Imports
from app.services.ocr_service import extract_from_image, extract_from_pdf, settings
from app.services.llm_service import parse_receipt_text
from app.services.receipt_parser import ReceiptParser
from app.services.normalization import normalize_product_name, simple_polish_stemmer

# Determine Tesseract path
possible_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Users\marci\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
]
for p in possible_paths:
    if os.path.exists(p):
        settings.TESSERACT_CMD = p
        break

import pytesseract
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

# Logging
logging.basicConfig(level=logging.ERROR) # Only errors to keep output clean
logger = logging.getLogger("VERIFY")
logger.setLevel(logging.INFO)

async def verify_file(file_path: str):
    print(f"\n{'='*60}")
    print(f"PROCESSING: {Path(file_path).name}")
    print(f"{'='*60}")
    
    # 1. OCR
    print("1. [OCR] Extracting text...", end=" ", flush=True)
    try:
        if file_path.lower().endswith(".pdf"):
            ocr_result = extract_from_pdf(file_path)
        else:
            ocr_result = extract_from_image(file_path)
            
        if ocr_result.error:
            print(f"FAILED: {ocr_result.error}")
            return
            
        print(f"DONE ({len(ocr_result.text)} chars)")
        # detailed debug
        print("--- OCR TEXT ---")
        print(ocr_result.text)
        print("----------------")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return

    # 2. Regex Parser
    print("2. [REGEX] Parsing...", end=" ", flush=True)
    parser = ReceiptParser()
    regex_res = parser.parse(ocr_result.text, shop_id=0)
    print("DONE")
    
    print(f"   -> Date: {regex_res.purchase_date}")
    print(f"   -> Total: {regex_res.total_amount}")
    print(f"   -> Items Found: {len(regex_res.items)}")
    if regex_res.items:
        print("      Sample Regex Items:")
        for i in regex_res.items[:3]:
            print(f"      - {i.raw_name} | {i.quantity} {i.unit} | {i.total_price}")

    # 3. LLM Parser
    print("3. [LLM] Parsing (Bielik)...", end=" ", flush=True)
    llm_res = parse_receipt_text(ocr_result.text)
    print("DONE")
    
    if llm_res.error:
        print(f"   -> ERROR: {llm_res.error}")
    else:
        print(f"   -> Shop: {llm_res.shop}")
        print(f"   -> Date: {llm_res.date}")
        print(f"   -> Total: {llm_res.total}")
        print(f"   -> Items Found: {len(llm_res.items)}")
        if llm_res.items:
             print("      Sample LLM Items:")
             for i in llm_res.items[:3]:
                 # Access as dict or object depending on implementation? 
                 # llm_service.py returns ParsedReceipt.items which is List[Dict] usually
                 if isinstance(i, dict):
                     print(f"      - {i.get('name')} | {i.get('quantity')} {i.get('unit')} | {i.get('total_price')}")
                 else:
                     print(f"      - {i.name} | {i.quantity} {i.unit} | {i.total_price}")

    # 4. Comparison & Normalization (Simulation)
    print("4. [HYBRID & NORMALIZATION]")
    
    # Simulate logic from router
    final_total = regex_res.total_amount if regex_res.total_amount > 0 else (llm_res.total or 0.0)
    final_shop = llm_res.shop or "Unknown"
    
    regex_total_sum = sum(i.total_price for i in regex_res.items)
    
    print(f"   -> FINAL DECISION:")
    print(f"      Shop: {final_shop}")
    print(f"      Total: {final_total}")
    
    using_regex_items = False
    if regex_res.items and abs(regex_total_sum - final_total) < 5.0:
        print(f"      Items Source: REGEX (Checksum valid: {regex_total_sum} ~ {final_total})")
        using_regex_items = True
        items_to_norm = regex_res.items
    else:
        print(f"      Items Source: LLM (Regex gap: abs({regex_total_sum} - {final_total}) > 5.0)")
        items_to_norm = llm_res.items

    # Test normalization on first few items
    if items_to_norm:
        print("      Normalization Sample:")
        count = 0
        for item in items_to_norm:
            if count >= 3: break
            
            # extract name
            if isinstance(item, dict): name = item.get('name')
            else: name = item.raw_name
            
            # Run normalization logic (mock DB)
            # We can't really test DB interaction but we can test logic flow
            # or try to use real normalization function if we had a real session.
            # Here we just use the stemmer/logic check.
            
            clean_name = name.strip()
            stem = simple_polish_stemmer(clean_name)
            print(f"      '{clean_name}' -> Stem: '{stem}'")
            count += 1
            

async def main():
    root = Path("d:/projekty/ParagonOCR/paragony")
    files = list(root.glob("*.png")) + list(root.glob("*.pdf")) + list(root.glob("*.jpg"))
    
    # Filter only if interesting files exist, else take first few
    # user mentioned verify 'lidl.png' specifically in history, lets try that and a generic one
    targets = [f for f in files if "lidl" in f.name.lower()]
    if not targets: targets = files[:2]
    else: targets = targets[:2] # take max 2 lidl receipts
    
    if not targets:
        print("No receipts found in paragony/")
        return

    for f in targets:
        await verify_file(str(f))

if __name__ == "__main__":
    asyncio.run(main())
