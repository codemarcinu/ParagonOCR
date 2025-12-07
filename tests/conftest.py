"""
Konfiguracja pytest - wspólne fixtures
"""
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Any
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Dodaj ścieżkę do modułów
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

# Import models after path setup
from src.database import Base, Sklep, KategoriaProduktu, Produkt, AliasProduktu, Paragon, PozycjaParagonu
from src.data_models import ParsedData, ParsedItem, ParsedReceiptInfo, ParsedStoreInfo


@pytest.fixture
def mock_ollama():
    """Mock Ollama client for testing"""
    with patch('src.llm.client') as mock_client:
        yield mock_client


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
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
def sample_receipt() -> ParsedData:
    """Sample receipt data for testing"""
    return {
        "sklep_info": {
            "nazwa": "Lidl",
            "lokalizacja": "Warszawa"
        },
        "paragon_info": {
            "data_zakupu": datetime(2024, 12, 7, 14, 30),
            "suma_calkowita": Decimal("45.67")
        },
        "pozycje": [
            {
                "nazwa_raw": "Mleko UHT 3,2% Łaciate 1L",
                "ilosc": Decimal("1.0"),
                "jednostka": "szt",
                "cena_jedn": Decimal("4.99"),
                "cena_calk": Decimal("4.99"),
                "rabat": Decimal("0.00"),
                "cena_po_rab": Decimal("4.99"),
                "data_waznosci": date(2024, 12, 15)
            },
            {
                "nazwa_raw": "Chleb Baltonowski krojony 500g",
                "ilosc": Decimal("1.0"),
                "jednostka": "szt",
                "cena_jedn": Decimal("3.49"),
                "cena_calk": Decimal("3.49"),
                "rabat": Decimal("0.00"),
                "cena_po_rab": Decimal("3.49")
            },
            {
                "nazwa_raw": "Jaja z wolnego wybiegu L 10szt",
                "ilosc": Decimal("1.0"),
                "jednostka": "szt",
                "cena_jedn": Decimal("12.99"),
                "cena_calk": Decimal("12.99"),
                "rabat": Decimal("0.00"),
                "cena_po_rab": Decimal("12.99")
            }
        ]
    }


@pytest.fixture
def sample_receipt_with_discount() -> ParsedData:
    """Sample receipt with discount items"""
    return {
        "sklep_info": {
            "nazwa": "Biedronka",
            "lokalizacja": "Kraków"
        },
        "paragon_info": {
            "data_zakupu": datetime(2024, 12, 7, 10, 0),
            "suma_calkowita": Decimal("25.50")
        },
        "pozycje": [
            {
                "nazwa_raw": "Szynka Krakus 200g",
                "ilosc": Decimal("1.0"),
                "jednostka": "szt",
                "cena_jedn": Decimal("8.99"),
                "cena_calk": Decimal("8.99"),
                "rabat": Decimal("2.00"),
                "cena_po_rab": Decimal("6.99")
            },
            {
                "nazwa_raw": "Rabat",
                "ilosc": Decimal("1.0"),
                "jednostka": None,
                "cena_jedn": Decimal("0.00"),
                "cena_calk": Decimal("-2.00"),
                "rabat": None,
                "cena_po_rab": Decimal("-2.00")
            }
        ]
    }


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
    shop = Sklep(nazwa_sklepu="Lidl", lokalizacja="Warszawa")
    session.add(shop)
    session.flush()
    
    # Create category
    category = KategoriaProduktu(nazwa_kategorii="Nabiał")
    session.add(category)
    session.flush()
    
    # Create product
    product = Produkt(
        znormalizowana_nazwa="Mleko",
        kategoria_id=category.kategoria_id
    )
    session.add(product)
    session.flush()
    
    # Create alias
    alias = AliasProduktu(
        nazwa_z_paragonu="Mleko UHT 3,2% Łaciate 1L",
        produkt_id=product.produkt_id
    )
    session.add(alias)
    
    # Create receipt
    receipt = Paragon(
        sklep_id=shop.sklep_id,
        data_zakupu=date(2024, 12, 7),
        suma_paragonu=Decimal("45.67"),
        plik_zrodlowy="/test/receipt.pdf"
    )
    session.add(receipt)
    session.flush()
    
    # Create receipt item
    item = PozycjaParagonu(
        paragon_id=receipt.paragon_id,
        produkt_id=product.produkt_id,
        nazwa_z_paragonu_raw="Mleko UHT 3,2% Łaciate 1L",
        ilosc=Decimal("1.0"),
        cena_calkowita=Decimal("4.99")
    )
    session.add(item)
    
    session.commit()
    return session


@pytest.fixture
def mock_llm_response():
    """Mock LLM response structure"""
    def _create_response(content: str):
        return {
            "message": {"content": content}
        }
    return _create_response


@pytest.fixture
def mock_log_callback():
    """Mock log callback function"""
    messages = []
    
    def log_callback(message: str):
        messages.append(message)
    
    log_callback.messages = messages
    return log_callback


@pytest.fixture
def mock_prompt_callback():
    """Mock prompt callback function"""
    responses = {}
    
    def prompt_callback(prompt: str, default: str, raw_name: str) -> str:
        return responses.get(raw_name, default)
    
    prompt_callback.responses = responses
    return prompt_callback
