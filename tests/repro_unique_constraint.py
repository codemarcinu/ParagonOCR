import sys
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.database import Base, AliasProduktu, Produkt, KategoriaProduktu
from src.main import resolve_product_with_suggestion

def test_resolve_product_with_suggestion_duplicate_alias():
    # Setup in-memory DB
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Mock callbacks
    log_callback = lambda msg, *args: print(msg)
    prompt_callback = lambda prompt, default, raw: default

    try:
        # 1. First call - should succeed
        print("Calling resolve_product_with_suggestion 1st time...")
        resolve_product_with_suggestion(
            session, 
            "Test Product A", 
            "Normalized Product A", 
            log_callback, 
            prompt_callback
        )
        session.flush()

        # 2. Second call with SAME raw_name - should fail currently
        print("Calling resolve_product_with_suggestion 2nd time (duplicate)...")
        resolve_product_with_suggestion(
            session, 
            "Test Product A", 
            "Normalized Product A", 
            log_callback, 
            prompt_callback
        )
        session.flush()
        
        print("Success! No crash.")

    except Exception as e:
        print(f"Caught expected exception: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    try:
        test_resolve_product_with_suggestion_duplicate_alias()
    except Exception:
        sys.exit(1)
