"""
Testy integracyjne - pełny pipeline przetwarzania
"""
import sys
import os
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.strategies import LidlStrategy, BiedronkaStrategy
from src.main import verify_math_consistency


class TestFullPipeline:
    """Testy pełnego pipeline przetwarzania"""

    def test_lidl_full_pipeline(self):
        """Test pełnego pipeline dla Lidla"""
        # Symulacja danych z LLM (przed post-processingiem)
        raw_data = {
            "sklep_info": {"nazwa": "Lidl", "lokalizacja": "Jankowice"},
            "paragon_info": {"data_zakupu": datetime(2024, 12, 27), "suma_calkowita": Decimal("26.34")},
            "pozycje": [
                {
                    "nazwa_raw": "Soczew.,HummusChipsy",
                    "ilosc": Decimal("2.0"),
                    "cena_jedn": Decimal("3.59"),
                    "cena_calk": Decimal("7.18"),
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("7.18"),
                },
                {
                    "nazwa_raw": "950_chipsy_mix",
                    "ilosc": Decimal("1.0"),
                    "cena_jedn": Decimal("-3.58"),
                    "cena_calk": Decimal("-3.58"),
                    "rabat": None,
                    "cena_po_rab": Decimal("-3.58"),
                },
            ],
        }

        # Post-processing (strategia)
        strategy = LidlStrategy()
        processed_data = strategy.post_process(raw_data)

        # Weryfikacja matematyczna
        log_messages = []
        final_data = verify_math_consistency(
            processed_data, lambda msg: log_messages.append(msg)
        )

        # Sprawdzenie wyników
        assert len(final_data["pozycje"]) == 1
        assert final_data["pozycje"][0]["nazwa_raw"] == "Soczew.,HummusChipsy"
        assert float(final_data["pozycje"][0]["rabat"]) == 3.58
        assert float(final_data["pozycje"][0]["cena_po_rab"]) == 3.60

    def test_biedronka_full_pipeline(self):
        """Test pełnego pipeline dla Biedronki"""
        raw_data = {
            "sklep_info": {"nazwa": "Biedronka", "lokalizacja": "Kostrzyn"},
            "paragon_info": {"data_zakupu": datetime(2025, 11, 18), "suma_calkowita": Decimal("114.14")},
            "pozycje": [
                {
                    "nazwa_raw": "KawMiel Rafiin250g",
                    "ilosc": Decimal("1.0"),
                    "cena_jedn": Decimal("18.99"),
                    "cena_calk": Decimal("18.99"),
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("18.99"),
                },
                {
                    "nazwa_raw": "Rabat",
                    "ilosc": Decimal("1.0"),
                    "cena_jedn": Decimal("-4.00"),
                    "cena_calk": Decimal("-4.00"),
                    "rabat": None,
                    "cena_po_rab": Decimal("-4.00"),
                },
            ],
        }

        # Post-processing
        strategy = BiedronkaStrategy()
        processed_data = strategy.post_process(raw_data)

        # Weryfikacja matematyczna
        log_messages = []
        final_data = verify_math_consistency(
            processed_data, lambda msg: log_messages.append(msg)
        )

        # Sprawdzenie wyników
        assert len(final_data["pozycje"]) == 1
        assert final_data["pozycje"][0]["nazwa_raw"] == "KawMiel Rafiin250g"
        assert float(final_data["pozycje"][0]["rabat"]) == 4.00
        assert float(final_data["pozycje"][0]["cena_po_rab"]) == 14.99

    def test_pipeline_with_math_correction(self):
        """Test pipeline z korekcją matematyczną"""
        raw_data = {
            "sklep_info": {"nazwa": "Lidl", "lokalizacja": "Test"},
            "paragon_info": {"data_zakupu": datetime(2024, 1, 1), "suma_calkowita": Decimal("10.00")},
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": Decimal("2.0"),
                    "cena_jedn": Decimal("5.00"),
                    "cena_calk": Decimal("8.00"),  # Błąd - powinno być 10.00 lub rabat 2.00
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("8.00"),
                }
            ],
        }

        # Post-processing
        strategy = LidlStrategy()
        processed_data = strategy.post_process(raw_data)

        # Weryfikacja matematyczna (wykryje ukryty rabat)
        log_messages = []
        final_data = verify_math_consistency(
            processed_data, lambda msg: log_messages.append(msg)
        )

        # Powinno wykryć ukryty rabat
        assert len(log_messages) > 0
        assert float(final_data["pozycje"][0]["rabat"]) == 2.00



