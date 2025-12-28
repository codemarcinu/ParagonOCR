
import asyncio
import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

# Configure logging
logging.basicConfig(level=logging.INFO)

from app.services.llm_service import parse_receipt_text

def test_llm_parsing():
    print("Testing LLM Parsing...")
    
    # Sample OCR text
    sample_text = """
    LIDL
    Data: 2025-01-25 14:30
    
    PARAGON FISKALNY
    
    Mleko UHT 3.2%    1 x 3.49    3.49 A
    Chleb wiejski    1 x 4.29    4.29 A
    Maslo Extra      2 x 6.99   13.98 A
    
    SUMA PLN                    21.76
    
    Podatek A 23%    4.07
    """
    
    print("-" * 20)
    print("Input Text:")
    print(sample_text)
    print("-" * 20)
    
    try:
        result = parse_receipt_text(sample_text)
        
        if result.error:
            print(f"Error: {result.error}")
        else:
            print("\nSuccess! Parsed Data:")
            print(f"Shop: {result.shop}")
            print(f"Date: {result.date}")
            print(f"Total: {result.total}")
            print("Items:")
            for item in result.items:
                print(f" - {item['name']}: {item['quantity']} x {item.get('unit_price')} = {item['total_price']}")
                
    except Exception as e:
        print(f"Exception during test: {e}")

if __name__ == "__main__":
    test_llm_parsing()
