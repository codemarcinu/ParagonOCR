
import asyncio
import sys
import os
import logging
from datetime import datetime, date

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

# Configure logging
logging.basicConfig(level=logging.INFO)

from app.services.ocr_service import extract_from_image
from app.services.receipt_parser import ReceiptParser
from app.services.llm_service import parse_receipt_text

def test_hybrid_logic():
    print("Testing Hybrid Logic...")
    
    # Path to real receipt
    image_path = os.path.join(os.path.dirname(__file__), "..", "paragony", "20250125lidl.png")
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return

    # 1. OCR
    print("1. Running OCR...")
    ocr_result = extract_from_image(image_path)
    if ocr_result.error:
        print(f"OCR Error: {ocr_result.error}")
        return
    print(f"OCR Text Length: {len(ocr_result.text)}")

    # 2a. Regex Parser
    print("2a. Running Regex Parser...")
    parser = ReceiptParser()
    parsed_regex = parser.parse(ocr_result.text, shop_id=0)
    print(f"Regex Date: {parsed_regex.purchase_date}")
    print(f"Regex Total: {parsed_regex.total_amount}")
    print(f"Regex Items: {len(parsed_regex.items)}")

    # 2b. LLM Parser
    print("2b. Running LLM Parser...")
    parsed_llm = parse_receipt_text(ocr_result.text)
    if parsed_llm.error:
        print(f"LLM Error: {parsed_llm.error}")
    else:
        print(f"LLM Shop: {parsed_llm.shop}")
        print(f"LLM Date: {parsed_llm.date}")
        print(f"LLM Total: {parsed_llm.total}")
        print(f"LLM Items: {len(parsed_llm.items)}")

    # 3. Merge Logic (Simulated from router)
    print("\n3. Merged Result:")
    
    # Shop: LLM wins
    shop_name = parsed_llm.shop if parsed_llm.shop else "Nieznany Sklep"
    print(f"Final Shop: {shop_name}")

    # Date: Regex <-> LLM
    final_date = date.today()
    if parsed_regex.purchase_date and parsed_regex.purchase_date != date.today():
         final_date = parsed_regex.purchase_date
         print("Date Source: Regex")
    else:
        try:
            final_date = datetime.strptime(parsed_llm.date, "%Y-%m-%d").date()
            print("Date Source: LLM")
        except:
            print("Date Source: Default (Today)")
    print(f"Final Date: {final_date}")

    # Total: Regex <-> LLM
    final_total = 0.0
    if parsed_regex.total_amount > 0:
        final_total = parsed_regex.total_amount
        print("Total Source: Regex")
    else:
        final_total = parsed_llm.total if parsed_llm.total is not None else 0.0
        print("Total Source: LLM")
    print(f"Final Total: {final_total}")
    
    # Items: Regex Heuristic
    regex_total = sum(i.total_price for i in parsed_regex.items)
    print(f"Regex Items Sum: {regex_total}")
    
    if parsed_regex.items and abs(regex_total - final_total) < 5.0:
        print("Items Source: Regex (Checksum OK)")
        final_items = parsed_regex.items
    else:
        print(f"Items Source: LLM (Regex checksum mismatch gap: {abs(regex_total - final_total)})")
        final_items = parsed_llm.items

    print(f"Final Item Count: {len(final_items)}")
    if len(final_items) > 0:
        first = final_items[0]
        if hasattr(first, 'raw_name'):
             print(f"Sample Item 1: {first.raw_name} - {first.total_price}")
        else:
             print(f"Sample Item 1: {first.get('name')} - {first.get('total_price')}")

if __name__ == "__main__":
    test_hybrid_logic()
