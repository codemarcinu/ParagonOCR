
import sys
import os
import logging
from sqlalchemy import text

# Add parent directory to path to allow importing app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.database import engine, Base
# Import all models to ensure metadata is populated
from app.models import receipt, product, category, shop, webauthn_key, user, shopping_list, chat_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    try:
        logger.info("Starting database reset...")
        
        # Drop all tables
        logger.info("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        
        # Create all tables
        logger.info("Recreating all tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database reset completed successfully.")
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")

if __name__ == "__main__":
    reset_database()
