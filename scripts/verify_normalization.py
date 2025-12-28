
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))

from app.services.normalization import normalize_unit, normalize_product_name, classify_product_category
# Import models to ensure SQLAlchemy registry is populated
from app.models.user import User
from app.models.webauthn_key import WebAuthnKey
from app.models.product import Product
from app.models.category import Category
from app.database import SessionLocal, Base, engine

# Mock DB Session for simple testing without full DB
class MockSession:
    def __init__(self):
        self.added = []
        self.flushed = False
    
    def add(self, obj):
        self.added.append(obj)
        if not hasattr(obj, 'id'):
            obj.id = len(self.added) # Artificial ID
            
    def flush(self):
        self.flushed = True
        
    def query(self, *args):
        return self
        
    def filter(self, *args):
        return self
        
    def first(self):
        return None # Simulate no existing records for now
        
    def all(self):
        return []

def test_normalization():
    print("=== Testing Unit Normalization ===")
    units = ["szt", "szt.", "st", "opak.", "kg", "g.", "unknown"]
    for u in units:
        print(f"Input: '{u}' -> Normalized: '{normalize_unit(u)}'")
        
    print("\n=== Testing Category Classification (Keywords) ===")
    products = [
        Product(normalized_name="Mleko 2%"),
        Product(normalized_name="Chleb wiejski"),
        Product(normalized_name="Szynka konserwowa"),
        Product(normalized_name="Woda Mineralna"),
        Product(normalized_name="Nierozpoznany Produkt X")
    ]
    
    # We need a real session for normalize_product_name to query DB, 
    # but classify_product_category only needs DB to add categories.
    # We can probably trust the keyword logic without full DB for this quick test.
    # However, classify_product_category calls _assign_category_by_name which does DB queries.
    
    # Let's verify imports work and unit norm works. 
    # For DB dependent tests, we might need a running DB or mock it better.
    # Given we are in production-like env, let's try to run against local DB if possible, 
    # or just unit test the pure logic functions.
    
    # Keyword logic check (white-box testing the map)
    # import logic to check map
    from app.services.normalization import CATEGORY_KEYWORDS
    print(f"Keywords loaded: {list(CATEGORY_KEYWORDS.keys())}")
    
    
    print("\n=== Testing Category Classification (LLM) ===")
    mock_db = MockSession()
    # Test with a product that matches a keyword
    p1 = Product(normalized_name="Mleko 2%")
    cat1 = classify_product_category(mock_db, p1)
    print(f"Product: {p1.normalized_name} -> Category ID: {cat1}")
    
    # Test with a product needing LLM
    p2 = Product(normalized_name="Nierozpoznany Produkt X") # Should be "Inne" or similar
    # Note: This requires Ollama running and model loaded
    try:
        cat2 = classify_product_category(mock_db, p2)
        print(f"Product: {p2.normalized_name} -> Category ID: {cat2}")
        print(f"Added objects in DB: {[x.__dict__ for x in mock_db.added]}")
    except Exception as e:
        print(f"LLM Test failed: {e}")


if __name__ == "__main__":
    test_normalization()
