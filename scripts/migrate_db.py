
import sys
import os
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))

from app.database import Base
from app.models.user import User
from app.models.shop import Shop
from app.models.receipt import Receipt, ReceiptItem
from app.models.product import Product
from app.models.category import Category
from app.models.pantry import PantryItem

# Configuration
POSSIBLE_PATHS = [
    "data/receipts.db",             # If running from backend/
    "backend/data/receipts.db",     # If running from root
    "../backend/data/receipts.db",  # If running from scripts/
]

SQLITE_DB_PATH = None
for path in POSSIBLE_PATHS:
    if os.path.exists(path):
        SQLITE_DB_PATH = path
        break

if not SQLITE_DB_PATH:
    # Fallback to absolute path search or user home default from config
    home_db = os.path.expanduser("~/.paragonocr/receipts.db")
    if os.path.exists(home_db):
        SQLITE_DB_PATH = home_db

# We read the NEW Postgres URL from the env file we just updated
from app.config import settings

POSTGRES_URL = settings.DATABASE_URL
if "sqlite" in POSTGRES_URL:
    print("Error: DATABASE_URL in config thinks it is still sqlite.") 
    print(f"Value: {POSTGRES_URL}")
    sys.exit(1)

def migrate():
    print(f"Source SQLite: {SQLITE_DB_PATH}")
    print(f"Target Postgres: {POSTGRES_URL}")
    
    if not os.path.exists(SQLITE_DB_PATH):
        print("Source database not found!")
        return

    # 1. Connect to SQLite (Source)
    sqlite_engine = create_engine(f"sqlite:///{SQLITE_DB_PATH}")
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SqliteSession()

    # 2. Connect to Postgres (Target) & Init Schema
    pg_engine = create_engine(POSTGRES_URL)
    print("Initializing schema on Postgres...")
    Base.metadata.create_all(pg_engine) # Create tables
    
    PgSession = sessionmaker(bind=pg_engine)
    pg_session = PgSession()

    try:
        from sqlalchemy import text
        
        # 3. Migrate Data Table by Table
        
        # Users
        print("Migrating Users...")
        with sqlite_engine.connect() as conn:
            users_data = conn.execute(text("SELECT * FROM users")).mappings().all()
            for row in users_data:
                u = User(**dict(row))
                pg_session.merge(u)
        pg_session.commit()

        # Shops
        print("Migrating Shops...")
        with sqlite_engine.connect() as conn:
            shops_data = conn.execute(text("SELECT * FROM shops")).mappings().all()
            for row in shops_data:
                s = Shop(**dict(row))
                pg_session.merge(s)
        pg_session.commit()

        # Categories
        print("Migrating Categories...")
        with sqlite_engine.connect() as conn:
            cats_data = conn.execute(text("SELECT * FROM categories")).mappings().all()
            for row in cats_data:
                c = Category(**dict(row))
                pg_session.merge(c)
        pg_session.commit()

        # Products
        print("Migrating Products...")
        with sqlite_engine.connect() as conn:
            prods_data = conn.execute(text("SELECT * FROM products")).mappings().all()
            for row in prods_data:
                p = Product(**dict(row))
                pg_session.merge(p)
        pg_session.commit()

        # Receipts (Handle missing user_id)
        print("Migrating Receipts...")
        with sqlite_engine.connect() as conn:
            receipts_data = conn.execute(text("SELECT * FROM receipts")).mappings().all()
            for row in receipts_data:
                data = dict(row)
                if 'user_id' not in data or data['user_id'] is None:
                    data['user_id'] = 1 # Default Admin
                
                # Filter out unknown columns if any
                valid_columns = {c.name for c in Receipt.__table__.columns}
                filtered_data = {k: v for k, v in data.items() if k in valid_columns}
                
                r = Receipt(**filtered_data)
                pg_session.merge(r)
        pg_session.commit()

        # Receipt Items
        print("Migrating Receipt Items...")
        with sqlite_engine.connect() as conn:
            items_data = conn.execute(text("SELECT * FROM receipt_items")).mappings().all()
            for row in items_data:
                i = ReceiptItem(**dict(row))
                pg_session.merge(i)
        pg_session.commit()
        
        # Pantry
        print("Migrating Pantry...")
        with sqlite_engine.connect() as conn:
            # Check if table exists first
            has_pantry = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='pantry_items'")).fetchone()
            if has_pantry:
                pantry_data = conn.execute(text("SELECT * FROM pantry_items")).mappings().all()
                for row in pantry_data:
                    # Handle potential schema diffs for pantry too
                    data = dict(row)
                    if 'user_id' not in data or data['user_id'] is None:
                        data['user_id'] = 1
                    
                    valid_columns = {c.name for c in PantryItem.__table__.columns}
                    filtered_data = {k: v for k, v in data.items() if k in valid_columns}

                    i = PantryItem(**filtered_data)
                    pg_session.merge(i)
            else:
                print("Skipping Pantry (table not found in source)")

        pg_session.commit()

        print("Migration complete!")

    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        pg_session.rollback()
    finally:
        sqlite_session.close()
        pg_session.close()

if __name__ == "__main__":
    migrate()
