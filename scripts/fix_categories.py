
import sys
import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

# Add parent directory to path to allow importing app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import get_db, SessionLocal
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.models.webauthn_key import WebAuthnKey # Explicitly import this too just in case

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fix_log.txt", mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def fix_categories():
    db = SessionLocal()
    try:
        logger.info("Starting category cleanup...")
        
        # 1. Ensure 'Inne' category exists as fallback
        fallback_cat = db.query(Category).filter(Category.name == "Inne").first()
        if not fallback_cat:
            logger.info("Creating default 'Inne' category")
            fallback_cat = Category(name="Inne", color="#808080")
            db.add(fallback_cat)
            db.commit()
            db.refresh(fallback_cat)
        
        # 2. Find invalid categories
        all_categories = db.query(Category).all()
        invalid_categories = []
        
        allowed_names = ["Nabiał", "Pieczywo", "Owoce i Warzywa", "Mięso i Wędliny", "Napoje", 
                         "Słodycze", "Chemia i Kosmetyki", "Alkohol", "Inne"]
        
        for cat in all_categories:
            is_valid = False
            # Check against whitelist (case-insensitive)
            for allowed in allowed_names:
                if cat.name.lower() == allowed.lower():
                    is_valid = True
                    break
            
            if not is_valid:
                # Also allow simple clear names if we decide to be lenient, but 
                # given the bug was code blocks, let's be strict or check for garbage.
                # The user bug showed python code blocks.
                if len(cat.name) > 50 or "```" in cat.name or "{" in cat.name or ":" in cat.name:
                    invalid_categories.append(cat)
                    continue

        logger.info(f"Found {len(invalid_categories)} invalid categories.")
        
        for invalid_cat in invalid_categories:
            logger.info(f"Processing invalid category: '{invalid_cat.name[:50]}...' (ID: {invalid_cat.id})")
            
            # Reassign products to fallback
            products = db.query(Product).filter(Product.category_id == invalid_cat.id).all()
            for prod in products:
                logger.info(f"  Reassigning product '{prod.normalized_name}' to 'Inne'")
                prod.category_id = fallback_cat.id
            
            # Delete category
            logger.info(f"  Deleting category {invalid_cat.id}")
            db.delete(invalid_cat)
            
        db.commit()
        logger.info("Category cleanup completed successfully.")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_categories()
