"""
Testy dla normalizacji produktów (normalization_rules.py)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.normalization_rules import find_static_match


class TestNormalizationRules:
    """Testy dla reguł normalizacji produktów"""

    def test_mleko(self):
        """Test normalizacji mleka"""
        assert find_static_match("Mleko UHT 3,2% Łaciate 1L") == "Mleko"
        assert find_static_match("Mleko 1,5%") == "Mleko"
        assert find_static_match("mleczko") == "Mleko"

    def test_pieczywo(self):
        """Test normalizacji pieczywa"""
        assert find_static_match("Kajzerka pszenna") == "Bułka"
        assert find_static_match("Bułka grahamka") == "Bułka"
        assert find_static_match("Chleb Baltonowski") == "Chleb"
        assert find_static_match("Chleb razowy") == "Chleb"

    def test_nabial(self):
        """Test normalizacji nabiału"""
        assert find_static_match("Serek wiejski Piątnica") == "Ser Biały/Twaróg"
        assert find_static_match("Twaróg półtłusty") == "Ser Biały/Twaróg"
        assert find_static_match("Ser Gouda") == "Ser Żółty"
        assert find_static_match("Masło Osełka") == "Masło"

    def test_warzywa_owoce(self):
        """Test normalizacji warzyw i owoców"""
        assert find_static_match("Pomidor gałązka") == "Pomidory"
        assert find_static_match("Ziemniaki wczesne") == "Ziemniaki"
        assert find_static_match("Jabłka Ligol") == "Jabłka"
        assert find_static_match("Banany") == "Banany"

    def test_mieso(self):
        """Test normalizacji mięsa"""
        assert find_static_match("Kurczak filet piersi") == "Kurczak"
        assert find_static_match("Szynka konserwowa") == "Szynka"
        assert find_static_match("Kiełbasa śląska") == "Kiełbasa"

    def test_napoje(self):
        """Test normalizacji napojów"""
        assert find_static_match("Coca Cola 0.5L") == "Napój Gazowany"
        assert find_static_match("Pepsi") == "Napój Gazowany"
        assert find_static_match("Woda Żywiec Zdrój") == "Woda Mineralna"
        assert find_static_match("Sok Tymbark") == "Sok"
        assert find_static_match("Piwo Tyskie") == "Piwo"

    def test_kaucja(self):
        """Test normalizacji kaucji i opłat"""
        assert find_static_match("Kaucja") == "Kaucja"
        assert find_static_match("Butelka zwrotna") == "Kaucja"
        assert find_static_match("Opłata recyklingowa") == "Opłata recyklingowa"
        assert find_static_match("Recykling") == "Opłata recyklingowa"

    def test_pomijanie(self):
        """Test pomijania nieistotnych pozycji"""
        assert find_static_match("Reklamówka") == "POMIŃ"
        assert find_static_match("Torba") == "POMIŃ"
        assert find_static_match("Siatka") == "POMIŃ"

    def test_nieznany_produkt(self):
        """Test dla nieznanych produktów"""
        assert find_static_match("Nieznany Produkt 123") is None
        assert find_static_match("XYZ ABC") is None

    def test_case_insensitive(self):
        """Test czy normalizacja jest case-insensitive"""
        assert find_static_match("MLEKO") == "Mleko"
        assert find_static_match("mleko") == "Mleko"
        assert find_static_match("MleKo") == "Mleko"








