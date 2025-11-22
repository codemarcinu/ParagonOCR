"""
Testy dla weryfikacji matematycznej (main.py - verify_math_consistency)
"""
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.main import verify_math_consistency


class TestMathVerification:
    """Testy dla weryfikacji matematycznej"""

    def test_correct_calculation(self):
        """Test gdy obliczenia są poprawne"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": Decimal("2.0"),
                    "cena_jedn": Decimal("3.50"),
                    "cena_calk": Decimal("7.00"),
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("7.00"),
                }
            ]
        }

        log_messages = []
        result = verify_math_consistency(data, lambda msg: log_messages.append(msg))

        assert len(result["pozycje"]) == 1
        assert result["pozycje"][0]["cena_calk"] == Decimal("7.00")
        assert len(log_messages) == 0  # Nie powinno być ostrzeżeń

    def test_hidden_discount(self):
        """Test wykrywania ukrytego rabatu"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": Decimal("2.0"),
                    "cena_jedn": Decimal("5.00"),
                    "cena_calk": Decimal("8.00"),  # Powinno być 10.00, więc rabat 2.00
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("8.00"),
                }
            ]
        }

        log_messages = []
        result = verify_math_consistency(data, lambda msg: log_messages.append(msg))

        assert len(log_messages) > 0  # Powinno być ostrzeżenie
        assert "ukryty rabat" in log_messages[0].lower() or "Niezgodność" in log_messages[0]
        assert Decimal(str(result["pozycje"][0]["rabat"])) == Decimal("2.00")
        assert Decimal(str(result["pozycje"][0]["cena_po_rab"])) == Decimal("8.00")

    def test_ocr_error(self):
        """Test wykrywania błędu OCR (cena_calk > obliczona)"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": Decimal("1.0"),
                    "cena_jedn": Decimal("5.00"),
                    "cena_calk": Decimal("7.00"),  # Błąd OCR, powinno być 5.00
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("7.00"),
                }
            ]
        }

        log_messages = []
        result = verify_math_consistency(data, lambda msg: log_messages.append(msg))

        assert len(log_messages) > 0
        # Powinno skorygować cenę
        assert Decimal(str(result["pozycje"][0]["cena_calk"])) == Decimal("5.00")

    def test_weighted_product(self):
        """Test dla produktu ważonego"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Marchew",
                    "ilosc": Decimal("0.365"),
                    "cena_jedn": Decimal("3.69"),
                    "cena_calk": Decimal("1.35"),
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("1.35"),
                }
            ]
        }

        log_messages = []
        result = verify_math_consistency(data, lambda msg: log_messages.append(msg))

        # 0.365 * 3.69 = 1.34685 ≈ 1.35 (w granicach tolerancji)
        assert len(log_messages) == 0

    def test_multiple_items(self):
        """Test dla wielu pozycji"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Produkt 1",
                    "ilosc": Decimal("2.0"),
                    "cena_jedn": Decimal("3.00"),
                    "cena_calk": Decimal("6.00"),
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("6.00"),
                },
                {
                    "nazwa_raw": "Produkt 2",
                    "ilosc": Decimal("1.0"),
                    "cena_jedn": Decimal("5.00"),
                    "cena_calk": Decimal("4.00"),  # Ukryty rabat 1.00
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("4.00"),
                },
            ]
        }

        log_messages = []
        result = verify_math_consistency(data, lambda msg: log_messages.append(msg))

        assert len(result["pozycje"]) == 2
        assert Decimal(str(result["pozycje"][0]["rabat"])) == Decimal("0.00")
        assert Decimal(str(result["pozycje"][1]["rabat"])) == Decimal("1.00")

    def test_string_values(self):
        """Test gdy wartości są stringami"""
        data = {
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": "2.0",
                    "cena_jedn": "3.50",
                    "cena_calk": "7.00",
                    "rabat": "0.00",
                    "cena_po_rab": "7.00",
                }
            ]
        }

        log_messages = []
        result = verify_math_consistency(data, lambda msg: log_messages.append(msg))

        assert len(result["pozycje"]) == 1
        # Funkcja powinna obsłużyć stringi (konwersja w _convert_types)

