import sys
import os
import asyncio
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import Base, get_db
from app.models.receipt import Receipt
from app.models.pantry import PantryItem
from app.models.product import Product
from app.services.inventory_service import InventoryService
from app.config import settings

def test_pantry_logic():
    # Setup DB connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    print("--- Starting Pantry Verification ---")

    try:
        # 1. Create Mock Receipt
        print("1. Creating Mock Receipt...")
        receipt = Receipt(
            user_id=1,
            shop_id=1, # Assuming shop 1 exists or is created
            purchase_date=date.today(),
            total_amount=10.0,
            source_file="test_verification.pdf",
            status="completed"
        )
        db.add(receipt)
        db.flush() # Get ID
        
        # 2. Mock Items Data (as if from LLM)
        items_data = [
            {
                "name": "Mleko Łaciate 3.2%",
                "quantity": 2.0,
                "price": 3.50,
                "total_price": 7.00,
                "category": "Nabiał",
                "unit": "szt"
            },
            {
                "name": "Chleb Razowy",
                "quantity": 1.0,
                "price": 3.00,
                "total_price": 3.00,
                "category": "Pieczywo",
                "unit": "szt"
            }
        ]

        # 3. Process
        print("2. Processing Items via InventoryService...")
        inventory_service = InventoryService()
        inventory_service.process_receipt_items(db, receipt, items_data)
        
        db.commit()
        
        # 4. Verify Pantry
        print("3. Verifying Pantry State...")
        pantry_items = db.query(PantryItem).all()
        
        verified_count = 0
        for item in pantry_items:
            # Check if this is our item (by receipt_item link or just name)
            # We can check via product
            prod = item.product
            if prod.normalized_name in ["Mleko Łaciate 3.2%", "Chleb Razowy"]: # Assuming normalized name matches raw here roughly
                print(f"   [OK] Found in Pantry: {prod.normalized_name}")
                print(f"        Quantity: {item.quantity}")
                print(f"        Expiration: {item.expiration_date}")
                print(f"        Status: {item.status}")
                if item.expiration_date:
                     print(f"        Has Expiration? YES")
                verified_count += 1
        
        if verified_count >= 2:
            print("SUCCESS: Items added to Pantry correctly.")
        else:
            print(f"WARNING: Only found {verified_count} relevant items.")

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_pantry_logic()
