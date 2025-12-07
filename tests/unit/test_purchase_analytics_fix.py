"""
Testy dla purchase_analytics.py - weryfikacja naprawy błędów SQLAlchemy ambiguous JOIN
"""
import sys
import os
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ReceiptParser"))

import pytest
from src.purchase_analytics import PurchaseAnalytics
from src.database import (
    Sklep, KategoriaProduktu, Produkt, Paragon, PozycjaParagonu, sessionmaker, engine
)


@pytest.mark.unit
class TestPurchaseAnalyticsFix:
    """Testy weryfikujące naprawę błędów ambiguous JOIN w purchase_analytics"""
    
    def test_get_total_statistics_no_errors(self, test_db):
        """Test że get_total_statistics() działa bez błędów SQLAlchemy"""
        analytics = PurchaseAnalytics(session=test_db)
        
        # Powinno działać bez wyjątków
        stats = analytics.get_total_statistics()
        
        # Sprawdź typy zwracanych wartości
        assert isinstance(stats, dict)
        assert isinstance(stats['total_receipts'], int)
        assert isinstance(stats['total_spent'], float)
        assert isinstance(stats['total_items'], int)
        assert isinstance(stats['avg_receipt'], float)
        
        # Wartości powinny być numeryczne (nie stringi z błędami)
        assert stats['total_receipts'] >= 0
        assert stats['total_spent'] >= 0
        assert stats['total_items'] >= 0
        assert stats['avg_receipt'] >= 0
        
        analytics.close()
    
    def test_get_spending_by_store_no_ambiguous_join(self, test_db):
        """Test że get_spending_by_store() działa z explicit join conditions"""
        # Utwórz testowe dane
        shop = Sklep(nazwa_sklepu="Test Shop")
        test_db.add(shop)
        test_db.flush()
        
        receipt = Paragon(
            sklep_id=shop.sklep_id,
            data_zakupu=date.today(),
            suma_paragonu=Decimal("100.00"),
            plik_zrodlowy="test.pdf"
        )
        test_db.add(receipt)
        test_db.commit()
        
        analytics = PurchaseAnalytics(session=test_db)
        
        # Powinno działać bez błędów ambiguous JOIN
        results = analytics.get_spending_by_store(limit=10)
        
        assert isinstance(results, list)
        # Sprawdź że nie ma błędów w wynikach
        for store_name, total in results:
            assert isinstance(store_name, str)
            assert isinstance(total, float)
            assert total >= 0
        
        analytics.close()
    
    def test_get_spending_by_category_no_ambiguous_join(self, test_db):
        """Test że get_spending_by_category() działa z explicit join conditions"""
        # Utwórz testowe dane
        category = KategoriaProduktu(nazwa_kategorii="Test Category")
        test_db.add(category)
        test_db.flush()
        
        product = Produkt(
            znormalizowana_nazwa="Test Product",
            kategoria_id=category.kategoria_id
        )
        test_db.add(product)
        test_db.flush()
        
        shop = Sklep(nazwa_sklepu="Test Shop")
        test_db.add(shop)
        test_db.flush()
        
        receipt = Paragon(
            sklep_id=shop.sklep_id,
            data_zakupu=date.today(),
            suma_paragonu=Decimal("100.00"),
            plik_zrodlowy="test.pdf"
        )
        test_db.add(receipt)
        test_db.flush()
        
        pozycja = PozycjaParagonu(
            paragon_id=receipt.paragon_id,
            produkt_id=product.produkt_id,
            nazwa_z_paragonu_raw="Test Product",
            cena_calkowita=Decimal("50.00"),
            cena_po_rabacie=Decimal("50.00")
        )
        test_db.add(pozycja)
        test_db.commit()
        
        analytics = PurchaseAnalytics(session=test_db)
        
        # Powinno działać bez błędów ambiguous JOIN
        results = analytics.get_spending_by_category(limit=10)
        
        assert isinstance(results, list)
        # Sprawdź że nie ma błędów w wynikach
        for category_name, total in results:
            assert isinstance(category_name, str)
            assert isinstance(total, float)
            assert total >= 0
        
        analytics.close()
    
    def test_get_top_products_no_ambiguous_join(self, test_db):
        """Test że get_top_products() działa z explicit join conditions"""
        # Utwórz testowe dane
        product = Produkt(znormalizowana_nazwa="Test Product")
        test_db.add(product)
        test_db.flush()
        
        shop = Sklep(nazwa_sklepu="Test Shop")
        test_db.add(shop)
        test_db.flush()
        
        receipt = Paragon(
            sklep_id=shop.sklep_id,
            data_zakupu=date.today(),
            suma_paragonu=Decimal("100.00"),
            plik_zrodlowy="test.pdf"
        )
        test_db.add(receipt)
        test_db.flush()
        
        pozycja = PozycjaParagonu(
            paragon_id=receipt.paragon_id,
            produkt_id=product.produkt_id,
            nazwa_z_paragonu_raw="Test Product",
            cena_calkowita=Decimal("50.00"),
            cena_po_rabacie=Decimal("50.00")
        )
        test_db.add(pozycja)
        test_db.commit()
        
        analytics = PurchaseAnalytics(session=test_db)
        
        # Powinno działać bez błędów ambiguous JOIN
        results = analytics.get_top_products(limit=10)
        
        assert isinstance(results, list)
        # Sprawdź że nie ma błędów w wynikach
        for product_name, count, total in results:
            assert isinstance(product_name, str)
            assert isinstance(count, int)
            assert isinstance(total, float)
            assert count >= 0
            assert total >= 0
        
        analytics.close()

