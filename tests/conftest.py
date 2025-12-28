"""
Konfiguracja pytest - wspólne fixtures
"""
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any, Generator
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

# Import models
from app.database import Base
from app.models.shop import Shop
from app.models.product import Product
from app.models.category import Category
from app.models.receipt import Receipt, ReceiptItem
from app.models.user import User
from app.models.webauthn_key import WebAuthnKey
from app.models.shopping_list import ShoppingList
from app.models.chat_history import Message, Conversation
from app.schemas import ReceiptCreate, ReceiptItemCreate

@pytest.fixture
def mock_ollama():
    """Mock Ollama client for testing"""
    with patch('app.services.llm_service.ollama_client') as mock_client:
        yield mock_client


@pytest.fixture
def test_db() -> Generator[Session, None, None]:
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(test_db):
    """Alias for test_db for clarity"""
    return test_db


@pytest.fixture
def sample_receipt_create() -> ReceiptCreate:
    """Sample ReceiptCreate data for testing"""
    return ReceiptCreate(
        shop_id=1,
        purchase_date=date(2024, 12, 7),
        purchase_time="14:30",
        total_amount=45.67,
        subtotal=45.67,
        tax=0.0,
        items=[
            ReceiptItemCreate(
                raw_name="Mleko UHT 3,2% Łaciate 1L",
                quantity=1.0,
                unit="szt",
                unit_price=4.99,
                total_price=4.99,
                discount=0.0
            ),
            ReceiptItemCreate(
                raw_name="Chleb Baltonowski krojony 500g",
                quantity=1.0,
                unit="szt",
                unit_price=3.49,
                total_price=3.49,
                discount=0.0
            ),
             ReceiptItemCreate(
                raw_name="Jaja z wolnego wybiegu L 10szt",
                quantity=1.0,
                unit="szt",
                unit_price=12.99,
                total_price=12.99,
                discount=0.0
            )
        ]
    )

@pytest.fixture
def sample_products():
    """Sample product names for batch processing tests"""
    return [
        "Mleko UHT 3,2% Łaciate 1L",
        "Chleb Baltonowski krojony 500g",
        "Jaja z wolnego wybiegu L 10szt",
        "Szynka Krakus 200g",
        "Pomidor gałązka luz",
        "Coca Cola 0.5L",
        "Reklamówka mała płatna"
    ]


@pytest.fixture
def populated_db(test_db):
    """Database with sample data"""
    session = test_db
    
    # Create shop
    shop = Shop(name="Lidl", location="Warszawa")
    session.add(shop)
    session.flush()
    
    # Create category
    category = Category(name="Nabiał")
    session.add(category)
    session.flush()
    
    # Create product
    product = Product(
        normalized_name="Mleko",
        category_id=category.id,
        unit="l"
    )
    session.add(product)
    session.flush()
    
    # Create receipt
    receipt = Receipt(
        shop_id=shop.id,
        purchase_date=date(2024, 12, 7),
        total_amount=45.67,
        source_file="/test/receipt.pdf",
        status="completed"
    )
    session.add(receipt)
    session.flush()
    
    # Create receipt item
    item = ReceiptItem(
        receipt_id=receipt.id,
        product_id=product.id,
        raw_name="Mleko UHT 3,2% Łaciate 1L",
        quantity=1.0,
        total_price=4.99
    )
    session.add(item)
    
    session.commit()
    return session
