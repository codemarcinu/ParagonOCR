"""
Testy dla bazy wiedzy (knowledge_base.py)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.knowledge_base import get_product_metadata, normalize_shop_name


class TestProductMetadata:
    """Testy dla metadanych produktów"""

    def test_mleko_metadata(self):
        """Test metadanych mleka"""
        meta = get_product_metadata("Mleko")
        assert meta["kategoria"] == "Nabiał"
        assert meta["can_freeze"] is True

    def test_smietana_metadata(self):
        """Test metadanych śmietany (nie można mrozić)"""
        meta = get_product_metadata("Śmietana")
        assert meta["kategoria"] == "Nabiał"
        assert meta["can_freeze"] is False

    def test_kurczak_metadata(self):
        """Test metadanych kurczaka"""
        meta = get_product_metadata("Kurczak")
        assert meta["kategoria"] == "Mięso"
        assert meta["can_freeze"] is True

    def test_kaucja_metadata(self):
        """Test metadanych kaucji"""
        meta = get_product_metadata("Kaucja")
        assert meta["kategoria"] == "Inne"
        assert meta["can_freeze"] is False

    def test_opłata_recyklingowa_metadata(self):
        """Test metadanych opłaty recyklingowej"""
        meta = get_product_metadata("Opłata recyklingowa")
        assert meta["kategoria"] == "Inne"
        assert meta["can_freeze"] is False

    def test_nieznany_produkt(self):
        """Test dla nieznanego produktu (domyślne wartości)"""
        meta = get_product_metadata("Nieznany Produkt")
        assert meta["kategoria"] == "Inne"
        assert meta["can_freeze"] is None


class TestShopNormalization:
    """Testy dla normalizacji nazw sklepów"""

    def test_lidl_normalization(self):
        """Test normalizacji Lidla"""
        assert normalize_shop_name("LIDL sp. z o.o.") == "Lidl"
        assert normalize_shop_name("lidl jankowice") == "Lidl"

    def test_biedronka_normalization(self):
        """Test normalizacji Biedronki"""
        assert normalize_shop_name("Biedronka Jeronimo Martins") == "Biedronka"
        assert normalize_shop_name("SKLEP 3218 TARGOWA") == "Biedronka"

    def test_auchan_normalization(self):
        """Test normalizacji Auchan"""
        assert normalize_shop_name("Auchan Warszawa") == "Auchan"

    def test_kaufland_normalization(self):
        """Test normalizacji Kaufland"""
        assert normalize_shop_name("Kaufland") == "Kaufland"

    def test_zabka_normalization(self):
        """Test normalizacji Żabki"""
        assert normalize_shop_name("Żabka Polska") == "Żabka"
        assert normalize_shop_name("zabka") == "Żabka"

    def test_nieznany_sklep(self):
        """Test dla nieznanego sklepu"""
        assert normalize_shop_name("Nieznany Sklep XYZ") == "Nieznany Sklep"








