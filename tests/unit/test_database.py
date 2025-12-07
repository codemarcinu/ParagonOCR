"""
Testy dla bazy danych - modele ORM, indeksy, operacje batch
"""
import sys
import os
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ReceiptParser"))

import pytest
from sqlalchemy.exc import IntegrityError
from src.database import (
    Base, Sklep, KategoriaProduktu, Produkt, AliasProduktu,
    Paragon, PozycjaParagonu, StanMagazynowy
)


@pytest.mark.unit
class TestDatabaseModels:
    """Testy dla modeli bazy danych"""
    
    def test_create_shop(self, test_db):
        """Test tworzenia sklepu"""
        shop = Sklep(nazwa_sklepu="Lidl", lokalizacja="Warszawa")
        test_db.add(shop)
        test_db.commit()
        
        assert shop.sklep_id is not None
        assert shop.nazwa_sklepu == "Lidl"
        assert shop.lokalizacja == "Warszawa"
    
    def test_create_product_with_category(self, test_db):
        """Test tworzenia produktu z kategorią"""
        category = KategoriaProduktu(nazwa_kategorii="Nabiał")
        test_db.add(category)
        test_db.flush()
        
        product = Produkt(
            znormalizowana_nazwa="Mleko",
            kategoria_id=category.kategoria_id
        )
        test_db.add(product)
        test_db.commit()
        
        assert product.produkt_id is not None
        assert product.znormalizowana_nazwa == "Mleko"
        assert product.kategoria.nazwa_kategorii == "Nabiał"
    
    def test_create_receipt_with_items(self, test_db):
        """Test tworzenia paragonu z pozycjami"""
        # Setup
        shop = Sklep(nazwa_sklepu="Lidl", lokalizacja="Warszawa")
        test_db.add(shop)
        test_db.flush()
        
        category = KategoriaProduktu(nazwa_kategorii="Nabiał")
        test_db.add(category)
        test_db.flush()
        
        product = Produkt(
            znormalizowana_nazwa="Mleko",
            kategoria_id=category.kategoria_id
        )
        test_db.add(product)
        test_db.flush()
        
        # Create receipt
        receipt = Paragon(
            sklep_id=shop.sklep_id,
            data_zakupu=date(2024, 12, 7),
            suma_paragonu=Decimal("45.67"),
            plik_zrodlowy="/test/receipt.pdf"
        )
        test_db.add(receipt)
        test_db.flush()
        
        # Create receipt item
        item = PozycjaParagonu(
            paragon_id=receipt.paragon_id,
            produkt_id=product.produkt_id,
            nazwa_z_paragonu_raw="Mleko UHT 3,2% Łaciate 1L",
            ilosc=Decimal("1.0"),
            cena_calkowita=Decimal("4.99")
        )
        test_db.add(item)
        test_db.commit()
        
        # Verify relationships
        assert receipt.sklep.nazwa_sklepu == "Lidl"
        assert len(receipt.pozycje) == 1
        assert receipt.pozycje[0].produkt.znormalizowana_nazwa == "Mleko"
    
    def test_create_alias_for_product(self, test_db):
        """Test tworzenia aliasu dla produktu"""
        category = KategoriaProduktu(nazwa_kategorii="Nabiał")
        test_db.add(category)
        test_db.flush()
        
        product = Produkt(
            znormalizowana_nazwa="Mleko",
            kategoria_id=category.kategoria_id
        )
        test_db.add(product)
        test_db.flush()
        
        alias = AliasProduktu(
            nazwa_z_paragonu="Mleko UHT 3,2% Łaciate 1L",
            produkt_id=product.produkt_id
        )
        test_db.add(alias)
        test_db.commit()
        
        assert alias.alias_id is not None
        assert alias.produkt.znormalizowana_nazwa == "Mleko"
        assert len(product.aliasy) == 1
    
    def test_unique_constraint_shop_name(self, test_db):
        """Test unikalności nazwy sklepu"""
        shop1 = Sklep(nazwa_sklepu="Lidl", lokalizacja="Warszawa")
        test_db.add(shop1)
        test_db.commit()
        
        shop2 = Sklep(nazwa_sklepu="Lidl", lokalizacja="Kraków")
        test_db.add(shop2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_unique_constraint_product_name(self, test_db):
        """Test unikalności nazwy produktu"""
        category = KategoriaProduktu(nazwa_kategorii="Nabiał")
        test_db.add(category)
        test_db.flush()
        
        product1 = Produkt(
            znormalizowana_nazwa="Mleko",
            kategoria_id=category.kategoria_id
        )
        test_db.add(product1)
        test_db.commit()
        
        product2 = Produkt(
            znormalizowana_nazwa="Mleko",
            kategoria_id=category.kategoria_id
        )
        test_db.add(product2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_cascade_delete_receipt_items(self, test_db):
        """Test kaskadowego usuwania pozycji przy usunięciu paragonu"""
        shop = Sklep(nazwa_sklepu="Lidl")
        test_db.add(shop)
        test_db.flush()
        
        receipt = Paragon(
            sklep_id=shop.sklep_id,
            data_zakupu=date(2024, 12, 7),
            suma_paragonu=Decimal("10.00"),
            plik_zrodlowy="/test/receipt.pdf"
        )
        test_db.add(receipt)
        test_db.flush()
        
        item = PozycjaParagonu(
            paragon_id=receipt.paragon_id,
            nazwa_z_paragonu_raw="Produkt",
            cena_calkowita=Decimal("10.00")
        )
        test_db.add(item)
        test_db.commit()
        
        item_id = item.pozycja_id
        
        # Delete receipt
        test_db.delete(receipt)
        test_db.commit()
        
        # Item should be deleted (cascade)
        deleted_item = test_db.query(PozycjaParagonu).filter_by(pozycja_id=item_id).first()
        assert deleted_item is None


@pytest.mark.unit
class TestDatabaseIndices:
    """Testy dla indeksów bazy danych"""
    
    def test_product_name_index(self, test_db):
        """Test indeksu na nazwie produktu"""
        category = KategoriaProduktu(nazwa_kategorii="Nabiał")
        test_db.add(category)
        test_db.flush()
        
        product = Produkt(
            znormalizowana_nazwa="Mleko",
            kategoria_id=category.kategoria_id
        )
        test_db.add(product)
        test_db.commit()
        
        # Query using indexed column (should be fast)
        result = test_db.query(Produkt).filter_by(znormalizowana_nazwa="Mleko").first()
        assert result is not None
        assert result.znormalizowana_nazwa == "Mleko"
    
    def test_receipt_shop_date_index(self, test_db):
        """Test złożonego indeksu na sklep_id i data_zakupu"""
        shop = Sklep(nazwa_sklepu="Lidl")
        test_db.add(shop)
        test_db.flush()
        
        receipt = Paragon(
            sklep_id=shop.sklep_id,
            data_zakupu=date(2024, 12, 7),
            suma_paragonu=Decimal("10.00"),
            plik_zrodlowy="/test/receipt.pdf"
        )
        test_db.add(receipt)
        test_db.commit()
        
        # Query using composite index
        result = test_db.query(Paragon).filter_by(
            sklep_id=shop.sklep_id,
            data_zakupu=date(2024, 12, 7)
        ).first()
        
        assert result is not None
        assert result.sklep_id == shop.sklep_id
    
    def test_alias_name_index(self, test_db):
        """Test indeksu na nazwie aliasu"""
        category = KategoriaProduktu(nazwa_kategorii="Nabiał")
        test_db.add(category)
        test_db.flush()
        
        product = Produkt(
            znormalizowana_nazwa="Mleko",
            kategoria_id=category.kategoria_id
        )
        test_db.add(product)
        test_db.flush()
        
        alias = AliasProduktu(
            nazwa_z_paragonu="Mleko UHT 3,2% Łaciate 1L",
            produkt_id=product.produkt_id
        )
        test_db.add(alias)
        test_db.commit()
        
        # Query using indexed column
        result = test_db.query(AliasProduktu).filter_by(
            nazwa_z_paragonu="Mleko UHT 3,2% Łaciate 1L"
        ).first()
        
        assert result is not None
        assert result.nazwa_z_paragonu == "Mleko UHT 3,2% Łaciate 1L"


@pytest.mark.unit
class TestDatabaseBatchOperations:
    """Testy dla operacji batch na bazie danych"""
    
    def test_batch_insert_products(self, test_db):
        """Test wsadowego wstawiania produktów"""
        category = KategoriaProduktu(nazwa_kategorii="Nabiał")
        test_db.add(category)
        test_db.flush()
        
        products = [
            Produkt(znormalizowana_nazwa="Mleko", kategoria_id=category.kategoria_id),
            Produkt(znormalizowana_nazwa="Ser", kategoria_id=category.kategoria_id),
            Produkt(znormalizowana_nazwa="Jogurt", kategoria_id=category.kategoria_id)
        ]
        
        test_db.add_all(products)
        test_db.commit()
        
        # Verify all inserted
        count = test_db.query(Produkt).count()
        assert count == 3
        
        # Verify names
        names = {p.znormalizowana_nazwa for p in test_db.query(Produkt).all()}
        assert names == {"Mleko", "Ser", "Jogurt"}
    
    def test_batch_query_aliases(self, test_db):
        """Test wsadowego zapytania o aliasy"""
        category = KategoriaProduktu(nazwa_kategorii="Nabiał")
        test_db.add(category)
        test_db.flush()
        
        product = Produkt(
            znormalizowana_nazwa="Mleko",
            kategoria_id=category.kategoria_id
        )
        test_db.add(product)
        test_db.flush()
        
        aliases = [
            AliasProduktu(nazwa_z_paragonu="Mleko UHT 3,2% Łaciate 1L", produkt_id=product.produkt_id),
            AliasProduktu(nazwa_z_paragonu="Mleko UHT 2%", produkt_id=product.produkt_id),
            AliasProduktu(nazwa_z_paragonu="Mleko pełne", produkt_id=product.produkt_id)
        ]
        test_db.add_all(aliases)
        test_db.commit()
        
        # Batch query using IN clause
        raw_names = ["Mleko UHT 3,2% Łaciate 1L", "Mleko UHT 2%"]
        results = test_db.query(AliasProduktu).filter(
            AliasProduktu.nazwa_z_paragonu.in_(raw_names)
        ).all()
        
        assert len(results) == 2
        assert {r.nazwa_z_paragonu for r in results} == set(raw_names)
    
    def test_batch_update_receipts(self, test_db):
        """Test wsadowej aktualizacji paragonów"""
        shop = Sklep(nazwa_sklepu="Lidl")
        test_db.add(shop)
        test_db.flush()
        
        receipts = [
            Paragon(sklep_id=shop.sklep_id, data_zakupu=date(2024, 12, 7), 
                   suma_paragonu=Decimal("10.00"), plik_zrodlowy="/test1.pdf"),
            Paragon(sklep_id=shop.sklep_id, data_zakupu=date(2024, 12, 8), 
                   suma_paragonu=Decimal("20.00"), plik_zrodlowy="/test2.pdf")
        ]
        test_db.add_all(receipts)
        test_db.commit()
        
        # Batch update
        test_db.query(Paragon).filter(
            Paragon.data_zakupu == date(2024, 12, 7)
        ).update({"suma_paragonu": Decimal("15.00")})
        test_db.commit()
        
        # Verify update
        updated = test_db.query(Paragon).filter_by(paragon_id=receipts[0].paragon_id).first()
        assert updated.suma_paragonu == Decimal("15.00")
        
        # Other receipt unchanged
        unchanged = test_db.query(Paragon).filter_by(paragon_id=receipts[1].paragon_id).first()
        assert unchanged.suma_paragonu == Decimal("20.00")

