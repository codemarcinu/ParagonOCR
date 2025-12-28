
import asyncio
import sys
import os
import logging
from datetime import datetime, date
from pathlib import Path

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Verify imports work
try:
    from app.database import SessionLocal, init_db, engine
    from app.models.receipt import Receipt, ReceiptItem
    from app.models.shop import Shop
    from app.models.product import Product
    from app.services.ocr_service import extract_from_pdf, extract_from_image
    from app.services.receipt_parser import ReceiptParser
    from app.services.llm_service import parse_receipt_text
    from app.services.normalization import normalize_unit, normalize_product_name, classify_product_category
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    sys.exit(1)

def run_sync_verification():
    print("=== Starting Full Flow Verification ===")
    
    # 1. Initialize DB (ensure tables exist)
    print("Initializing Database...")
    init_db()
    
    # 2. Find receipts
    paragony_dir = os.path.join(os.path.dirname(__file__), "..", "paragony")
    files = [f for f in os.listdir(paragony_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf'))]
    print(f"Found {len(files)} receipt files in {paragony_dir}")
    
    db = SessionLocal()
    
    try:
        for filename in files:
            file_path = os.path.join(paragony_dir, filename)
            print(f"\n\n--- Processing: {filename} ---")
            
            # Create Receipt Entry
            receipt = Receipt(
                shop_id=1, 
                purchase_date=date.today(),
                total_amount=0.0,
                source_file=file_path,
                status="processing_test"
            )
            db.add(receipt)
            db.commit()
            receipt_id = receipt.id
            print(f"Created Receipt ID: {receipt_id}")

            # --- OCR PHASE ---
            print("[1] Running OCR...")
            ocr_text = ""
            ocr_error = None
            
            # Try Real OCR First
            try:
                if filename.lower().endswith(".pdf"):
                    ocr_result = extract_from_pdf(file_path)
                else:
                    ocr_result = extract_from_image(file_path)
                
                if ocr_result.error:
                    ocr_error = ocr_result.error
                    print(f"OCR Error: {ocr_error}")
                else:
                    ocr_text = ocr_result.text
                    print(f"OCR Success. Text length: {len(ocr_text)}")
            except Exception as e:
                ocr_error = str(e)
                print(f"OCR Exception: {e}")

            # Fallback to cached text if OCR failed
            if not ocr_text:
                print("Attempting to load cached OCR text...")
                stem = Path(filename).stem
                # Try candidates
                candidates = [
                    f"ocr_{filename}.txt", # e.g. ocr_file.png.txt
                    f"ocr_{stem}.txt"      # e.g. ocr_file.txt
                ]
                
                for cand in candidates:
                    cand_path = os.path.join(paragony_dir, cand)
                    if os.path.exists(cand_path):
                        try:
                            with open(cand_path, "r", encoding="utf-8") as f:
                                ocr_text = f.read()
                            print(f"Loaded cached text from {cand} (Length: {len(ocr_text)})")
                            break
                        except Exception as e:
                            print(f"Error reading {cand}: {e}")
            
            if not ocr_text:
                print(f"Skipping {filename} - No OCR text available (Real OCR failed and no cache found).")
                continue
                
            receipt.ocr_text = ocr_text
            if len(ocr_text) < 50:
                 print(f"WARNING: OCR text seems very short: {ocr_text.strip()}")
            
            # Wrap text in object for compatibility if needed, but we just use string below
            class MockOCR:
                text = ocr_text
            ocr_result = MockOCR()

            # --- PARSING PHASE ---
            print("[2] Running Hybrid Parsing...")
            
            # Regex
            parser = ReceiptParser()
            parsed_regex = parser.parse(ocr_result.text, shop_id=0)
            print(f"Regex Parser: Date={parsed_regex.purchase_date}, Total={parsed_regex.total_amount:.2f}, Items={len(parsed_regex.items)}")
            
            # LLM
            parsed_llm = parse_receipt_text(ocr_result.text)
            if parsed_llm.error:
                 print(f"LLM Parser Error: {parsed_llm.error}")
            else:
                 print(f"LLM Parser: Shop='{parsed_llm.shop}', Date={parsed_llm.date}, Total={parsed_llm.total}, Items={len(parsed_llm.items)}")

            # --- MERGE & NORMALIZE PHASE ---
            print("[3] Merging & Saving to DB...")
            
            # Shop Logic
            shop_name = parsed_llm.shop if parsed_llm.shop else "Nieznany Sklep"
            shop_obj = db.query(Shop).filter(Shop.name == shop_name).first()
            if not shop_obj:
                shop_obj = Shop(name=shop_name)
                db.add(shop_obj)
                db.flush()
                print(f"Created New Shop: {shop_name}")
            receipt.shop_id = shop_obj.id
            
            # Date Logic
            if parsed_regex.purchase_date and parsed_regex.purchase_date != date.today():
                 receipt.purchase_date = parsed_regex.purchase_date
            else:
                try:
                    receipt.purchase_date = datetime.strptime(parsed_llm.date, "%Y-%m-%d").date()
                except:
                    pass
            
            # Total Logic
            if parsed_regex.total_amount > 0:
                receipt.total_amount = parsed_regex.total_amount
            else:
                receipt.total_amount = parsed_llm.total if parsed_llm.total is not None else 0.0
            
            receipt.status = "completed"

            # Items Logic
            regex_total = sum(i.total_price for i in parsed_regex.items)
            items_source = []
            source_type = "llm"
            
            if parsed_regex.items and abs(regex_total - receipt.total_amount) < 5.0:
                 print("Using Regex Items (Checksum OK)")
                 items_source = parsed_regex.items
                 source_type = "regex"
            else:
                 print(f"Using LLM Items (Regex checksum gap: {abs(regex_total - receipt.total_amount):.2f})")
                 items_source = parsed_llm.items
            
            # Process Items
            added_items_count = 0
            for item_data in items_source:
                if source_type == "regex":
                    name = item_data.raw_name
                    qty = item_data.quantity
                    unit = item_data.unit
                    unit_price = item_data.unit_price
                    total_price = item_data.total_price
                else:
                    name = item_data.get("name", "")
                    qty = item_data.get("quantity", 1.0)
                    unit = item_data.get("unit")
                    unit_price = item_data.get("unit_price")
                    total_price = item_data.get("total_price", 0.0)

                if not name: continue

                # Normalization
                unit = normalize_unit(unit)
                product, is_new = normalize_product_name(db, name)
                
                if is_new:
                    cat_id = classify_product_category(db, product)
                    if cat_id:
                        product.category_id = cat_id
                        db.add(product) # Update product with category
                
                # Create Item
                receipt_item = ReceiptItem(
                    receipt_id=receipt.id,
                    product_id=product.id,
                    raw_name=name,
                    quantity=qty,
                    unit=unit,
                    unit_price=unit_price,
                    total_price=total_price
                )
                db.add(receipt_item)
                added_items_count += 1
            
            db.commit()
            print(f"Saved {added_items_count} items to DB.")

            # --- VERIFICATION PHASE ---
            print("[4] Database Verification")
            saved_receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
            print(f"DB Receipt: ID={saved_receipt.id}, ShopID={saved_receipt.shop_id}, Date={saved_receipt.purchase_date}, Total={saved_receipt.total_amount}")
            saved_items = db.query(ReceiptItem).filter(ReceiptItem.receipt_id == receipt_id).all()
            print(f"DB Items Count: {len(saved_items)}")
            if saved_items:
                print("Sample DB Items:")
                for i, item in enumerate(saved_items[:3]): # Show first 3
                    prod_name = item.product.normalized_name if item.product else "Unknown"
                    cat_name = item.product.category.name if (item.product and item.product.category) else "None"
                    print(f"  {i+1}. {item.raw_name} -> Norm: '{prod_name}' [Cat: {cat_name}] | {item.quantity}{item.unit} * {item.unit_price} = {item.total_price}")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print("\n=== Verification Complete ===")

if __name__ == "__main__":
    # Ensure env vars are set if needed (handled by app.config usually)
    run_sync_verification()
