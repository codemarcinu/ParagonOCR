"""
Testy dla konwersji typów (llm.py - _convert_types)
"""
import sys
import os
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.llm import _convert_types


class TestTypeConversion:
    """Testy dla konwersji typów danych"""

    def test_date_conversion_iso_format(self):
        """Test konwersji daty w formacie ISO"""
        data = {
            "paragon_info": {"data_zakupu": "2024-12-27", "suma_calkowita": "26.34"},
            "pozycje": [],
        }

        result = _convert_types(data)

        assert isinstance(result["paragon_info"]["data_zakupu"], datetime)
        assert result["paragon_info"]["data_zakupu"].year == 2024
        assert result["paragon_info"]["data_zakupu"].month == 12
        assert result["paragon_info"]["data_zakupu"].day == 27

    def test_date_conversion_polish_format(self):
        """Test konwersji daty w formacie polskim"""
        data = {
            "paragon_info": {"data_zakupu": "27.12.2024", "suma_calkowita": "26.34"},
            "pozycje": [],
        }

        result = _convert_types(data)

        assert isinstance(result["paragon_info"]["data_zakupu"], datetime)
        assert result["paragon_info"]["data_zakupu"].day == 27
        assert result["paragon_info"]["data_zakupu"].month == 12

    def test_date_conversion_with_time(self):
        """Test konwersji daty z czasem"""
        data = {
            "paragon_info": {"data_zakupu": "18.11.2025 16:34", "suma_calkowita": "114.14"},
            "pozycje": [],
        }

        result = _convert_types(data)

        assert isinstance(result["paragon_info"]["data_zakupu"], datetime)
        assert result["paragon_info"]["data_zakupu"].hour == 16
        assert result["paragon_info"]["data_zakupu"].minute == 34

    def test_decimal_conversion(self):
        """Test konwersji cen na Decimal"""
        data = {
            "paragon_info": {"data_zakupu": "2024-12-27", "suma_calkowita": "26.34"},
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": "2.0",
                    "cena_jedn": "3.59",
                    "cena_calk": "7.18",
                    "rabat": "0.00",
                    "cena_po_rab": "7.18",
                }
            ],
        }

        result = _convert_types(data)

        assert isinstance(result["paragon_info"]["suma_calkowita"], Decimal)
        assert result["paragon_info"]["suma_calkowita"] == Decimal("26.34")

        assert isinstance(result["pozycje"][0]["ilosc"], Decimal)
        assert isinstance(result["pozycje"][0]["cena_jedn"], Decimal)
        assert isinstance(result["pozycje"][0]["cena_calk"], Decimal)
        assert isinstance(result["pozycje"][0]["rabat"], Decimal)

    def test_decimal_with_comma(self):
        """Test konwersji z przecinkiem jako separatorem"""
        data = {
            "paragon_info": {"data_zakupu": "2024-12-27", "suma_calkowita": "26,34"},
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": "2,0",
                    "cena_jedn": "3,59",
                    "cena_calk": "7,18",
                    "rabat": "0,00",
                    "cena_po_rab": "7,18",
                }
            ],
        }

        result = _convert_types(data)

        assert result["paragon_info"]["suma_calkowita"] == Decimal("26.34")
        assert result["pozycje"][0]["cena_jedn"] == Decimal("3.59")

    def test_null_rabat(self):
        """Test gdy rabat jest null"""
        data = {
            "paragon_info": {"data_zakupu": "2024-12-27", "suma_calkowita": "10.00"},
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": "1.0",
                    "cena_jedn": "10.00",
                    "cena_calk": "10.00",
                    "rabat": None,
                    "cena_po_rab": "10.00",
                }
            ],
        }

        result = _convert_types(data)

        assert result["pozycje"][0]["rabat"] == Decimal("0.00")

    def test_invalid_date_fallback(self):
        """Test fallback dla nieprawidłowej daty"""
        data = {
            "paragon_info": {"data_zakupu": "nieprawidłowa data", "suma_calkowita": "10.00"},
            "pozycje": [],
        }

        result = _convert_types(data)

        # Powinno ustawić dzisiejszą datę
        assert isinstance(result["paragon_info"]["data_zakupu"], datetime)

    def test_weighted_product(self):
        """Test dla produktu ważonego"""
        data = {
            "paragon_info": {"data_zakupu": "2025-01-13", "suma_calkowita": "29.76"},
            "pozycje": [
                {
                    "nazwa_raw": "Marchew Luz",
                    "ilosc": "0.365",
                    "jednostka": "kg",
                    "cena_jedn": "3.69",
                    "cena_calk": "1.35",
                    "rabat": "0.00",
                    "cena_po_rab": "1.35",
                }
            ],
        }

        result = _convert_types(data)

        assert result["pozycje"][0]["ilosc"] == Decimal("0.365")
        assert result["pozycje"][0]["jednostka"] == "kg"







