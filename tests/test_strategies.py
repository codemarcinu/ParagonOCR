"""
Testy dla strategii parsowania paragonów (strategies.py)
"""
import sys
import os
from decimal import Decimal

# Dodaj ścieżkę do modułów
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.strategies import (
    LidlStrategy,
    BiedronkaStrategy,
    AuchanStrategy,
    GenericStrategy,
    get_strategy_for_store,
)


class TestLidlStrategy:
    """Testy dla strategii Lidl"""

    def setup_method(self):
        self.strategy = LidlStrategy()

    def test_get_system_prompt(self):
        """Test czy prompt systemowy jest zwracany"""
        prompt = self.strategy.get_system_prompt()
        assert isinstance(prompt, str)
        assert "Lidl" in prompt
        assert "JSON" in prompt

    def test_post_process_scales_discounts(self):
        """Test scalania rabatów w Lidlu"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Serek Wiejski",
                    "ilosc": "1.0",
                    "cena_jedn": "3.59",
                    "cena_calk": "3.59",
                    "rabat": "0.00",
                    "cena_po_rab": "3.59",
                },
                {
                    "nazwa_raw": "Lidl Plus rabat",
                    "ilosc": "1.0",
                    "cena_jedn": "-0.50",
                    "cena_calk": "-0.50",
                    "rabat": None,
                    "cena_po_rab": "-0.50",
                },
            ]
        }

        result = self.strategy.post_process(data)

        assert len(result["pozycje"]) == 1
        assert result["pozycje"][0]["nazwa_raw"] == "Serek Wiejski"
        assert float(result["pozycje"][0]["rabat"]) == 0.50
        assert float(result["pozycje"][0]["cena_po_rab"]) == 3.09

    def test_post_process_multiple_discounts(self):
        """Test wielu rabatów pod rząd"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Produkt 1",
                    "ilosc": "1.0",
                    "cena_jedn": "10.00",
                    "cena_calk": "10.00",
                    "rabat": "0.00",
                    "cena_po_rab": "10.00",
                },
                {
                    "nazwa_raw": "Rabat",
                    "ilosc": "1.0",
                    "cena_jedn": "-2.00",
                    "cena_calk": "-2.00",
                    "rabat": None,
                    "cena_po_rab": "-2.00",
                },
                {
                    "nazwa_raw": "Produkt 2",
                    "ilosc": "1.0",
                    "cena_jedn": "5.00",
                    "cena_calk": "5.00",
                    "rabat": "0.00",
                    "cena_po_rab": "5.00",
                },
            ]
        }

        result = self.strategy.post_process(data)

        assert len(result["pozycje"]) == 2
        assert float(result["pozycje"][0]["rabat"]) == 2.00
        assert float(result["pozycje"][1]["rabat"]) == 0.00

    def test_post_process_no_discounts(self):
        """Test gdy nie ma rabatów"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": "1.0",
                    "cena_jedn": "5.00",
                    "cena_calk": "5.00",
                    "rabat": "0.00",
                    "cena_po_rab": "5.00",
                }
            ]
        }

        result = self.strategy.post_process(data)

        assert len(result["pozycje"]) == 1
        assert float(result["pozycje"][0]["rabat"]) == 0.00


class TestBiedronkaStrategy:
    """Testy dla strategii Biedronka"""

    def setup_method(self):
        self.strategy = BiedronkaStrategy()

    def test_get_system_prompt(self):
        """Test czy prompt systemowy jest zwracany"""
        prompt = self.strategy.get_system_prompt()
        assert isinstance(prompt, str)
        assert "Biedronka" in prompt or "Jeronimo" in prompt

    def test_post_process_scales_discounts(self):
        """Test scalania rabatów w Biedronce"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "KawMiel Rafiin250g",
                    "ilosc": "1.0",
                    "cena_jedn": "18.99",
                    "cena_calk": "18.99",
                    "rabat": "0.00",
                    "cena_po_rab": "18.99",
                },
                {
                    "nazwa_raw": "Rabat",
                    "ilosc": "1.0",
                    "cena_jedn": "-4.00",
                    "cena_calk": "-4.00",
                    "rabat": None,
                    "cena_po_rab": "-4.00",
                },
            ]
        }

        result = self.strategy.post_process(data)

        assert len(result["pozycje"]) == 1
        assert result["pozycje"][0]["nazwa_raw"] == "KawMiel Rafiin250g"
        assert float(result["pozycje"][0]["rabat"]) == 4.00
        assert float(result["pozycje"][0]["cena_po_rab"]) == 14.99

    def test_post_process_discount_by_name(self):
        """Test wykrywania rabatu po nazwie 'Upust'"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": "1.0",
                    "cena_jedn": "10.00",
                    "cena_calk": "10.00",
                    "rabat": "0.00",
                    "cena_po_rab": "10.00",
                },
                {
                    "nazwa_raw": "Upust",
                    "ilosc": "1.0",
                    "cena_jedn": "1.00",
                    "cena_calk": "1.00",
                    "rabat": None,
                    "cena_po_rab": "1.00",
                },
            ]
        }

        result = self.strategy.post_process(data)

        assert len(result["pozycje"]) == 1
        # Upust z dodatnią ceną nie powinien być traktowany jako rabat
        # (tylko ujemna cena lub nazwa "Rabat")


class TestAuchanStrategy:
    """Testy dla strategii Auchan"""

    def setup_method(self):
        self.strategy = AuchanStrategy()

    def test_get_system_prompt(self):
        """Test czy prompt systemowy jest zwracany"""
        prompt = self.strategy.get_system_prompt()
        assert isinstance(prompt, str)
        assert "Auchan" in prompt

    def test_post_process_removes_ocr_garbage(self):
        """Test usuwania śmieci OCR"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "ReWtymOplRec551061",
                    "ilosc": "1.0",
                    "cena_jedn": "3.25",
                    "cena_calk": "3.25",
                },
                {
                    "nazwa_raw": "NAPOJ GAZ. 86851A",
                    "ilosc": "1.0",
                    "cena_jedn": "4.48",
                    "cena_calk": "4.48",
                },
                {
                    "nazwa_raw": "ReWtymOplRec123456",
                    "ilosc": "1.0",
                    "cena_jedn": "2.00",
                    "cena_calk": "2.00",
                },
            ]
        }

        result = self.strategy.post_process(data)

        # ReWtymOplRec powinno być usunięte
        assert len(result["pozycje"]) == 1
        assert result["pozycje"][0]["nazwa_raw"] == "NAPOJ GAZ. 86851A"

    def test_post_process_removes_long_garbage(self):
        """Test usuwania długich ciągów bez spacji"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Abc123Def456Ghi789",
                    "ilosc": "1.0",
                    "cena_jedn": "5.00",
                    "cena_calk": "5.00",
                },
                {
                    "nazwa_raw": "Normalny Produkt",
                    "ilosc": "1.0",
                    "cena_jedn": "3.00",
                    "cena_calk": "3.00",
                },
            ]
        }

        result = self.strategy.post_process(data)

        assert len(result["pozycje"]) == 1
        assert result["pozycje"][0]["nazwa_raw"] == "Normalny Produkt"


class TestStrategySelection:
    """Testy dla wyboru strategii"""

    def test_get_strategy_lidl(self):
        """Test wyboru strategii Lidl"""
        text = "LIDL sp. z o.o. sp. k. Jankowice"
        strategy = get_strategy_for_store(text)
        assert isinstance(strategy, LidlStrategy)

    def test_get_strategy_biedronka(self):
        """Test wyboru strategii Biedronka"""
        text = "Biedronka Jeronimo Martins"
        strategy = get_strategy_for_store(text)
        assert isinstance(strategy, BiedronkaStrategy)

    def test_get_strategy_auchan(self):
        """Test wyboru strategii Auchan"""
        text = "Auchan Warszawa"
        strategy = get_strategy_for_store(text)
        assert isinstance(strategy, AuchanStrategy)

    def test_get_strategy_generic(self):
        """Test wyboru strategii Generic dla nieznanego sklepu"""
        text = "Nieznany Sklep XYZ"
        strategy = get_strategy_for_store(text)
        assert isinstance(strategy, GenericStrategy)

