"""
Testy dla modułu bielik.py - asystent AI Bielik
"""
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
from decimal import Decimal
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.bielik import (
    BielikAssistant,
    ask_bielik,
    get_dish_suggestions,
    get_shopping_list,
)


class TestBielikAssistantRAG:
    """Testy dla wyszukiwania produktów z RAG"""

    def setup_method(self):
        """Przygotowanie mocków przed każdym testem"""
        self.mock_session = MagicMock()
        self.assistant = BielikAssistant(session=self.mock_session)

    def test_search_products_rag_found(self):
        """Test wyszukiwania produktów - znaleziono"""
        # Mock produktów
        mock_produkt1 = MagicMock()
        mock_produkt1.znormalizowana_nazwa = "Mleko"
        mock_produkt1.produkt_id = 1
        mock_kategoria1 = MagicMock()
        mock_kategoria1.nazwa_kategorii = "Nabiał"
        mock_produkt1.kategoria = mock_kategoria1

        mock_produkt2 = MagicMock()
        mock_produkt2.znormalizowana_nazwa = "Chleb"
        mock_produkt2.produkt_id = 2
        mock_kategoria2 = MagicMock()
        mock_kategoria2.nazwa_kategorii = "Pieczywo"
        mock_produkt2.kategoria = mock_kategoria2

        # Mock query
        self.mock_session.query.return_value.options.return_value.all.return_value = [
            mock_produkt1,
            mock_produkt2,
        ]

        # Mock stanu magazynowego
        mock_stan = MagicMock()
        mock_stan.ilosc = Decimal("2.0")
        mock_stan.jednostka_miary = "l"
        mock_stan.data_waznosci = date(2025, 1, 20)
        mock_stan.zamrozone = False

        self.mock_session.query.return_value.filter_by.return_value.filter.return_value.all.return_value = [
            mock_stan
        ]

        result = self.assistant._search_products_rag("mleko", limit=10)

        assert len(result) > 0
        assert result[0]["nazwa"] == "Mleko"
        assert result[0]["kategoria"] == "Nabiał"
        assert result[0]["has_stock"] is True

    def test_search_products_rag_not_found(self):
        """Test wyszukiwania produktów - nie znaleziono"""
        self.mock_session.query.return_value.options.return_value.all.return_value = []

        result = self.assistant._search_products_rag("nieistniejący produkt", limit=10)

        assert len(result) == 0

    def test_search_products_rag_min_similarity(self):
        """Test filtrowania po minimalnym podobieństwie"""
        mock_produkt = MagicMock()
        mock_produkt.znormalizowana_nazwa = "Mleko"
        mock_produkt.produkt_id = 1
        mock_produkt.kategoria = None

        self.mock_session.query.return_value.options.return_value.all.return_value = [
            mock_produkt
        ]
        self.mock_session.query.return_value.filter_by.return_value.filter.return_value.all.return_value = []

        # Wysokie minimalne podobieństwo - nic nie powinno się znaleźć
        result = self.assistant._search_products_rag(
            "zupełnie inny produkt", limit=10, min_similarity=90
        )

        assert len(result) == 0

    def teardown_method(self):
        """Czyszczenie po każdym teście"""
        if self.assistant:
            self.assistant.close()


class TestBielikAssistantAvailableProducts:
    """Testy dla pobierania dostępnych produktów"""

    def setup_method(self):
        """Przygotowanie mocków przed każdym testem"""
        self.mock_session = MagicMock()
        self.assistant = BielikAssistant(session=self.mock_session)

    def test_get_available_products(self):
        """Test pobierania dostępnych produktów"""
        # Mock stanu magazynowego
        mock_stan1 = MagicMock()
        mock_stan1.produkt_id = 1
        mock_produkt1 = MagicMock()
        mock_produkt1.znormalizowana_nazwa = "Mleko"
        mock_kategoria1 = MagicMock()
        mock_kategoria1.nazwa_kategorii = "Nabiał"
        mock_produkt1.kategoria = mock_kategoria1
        mock_stan1.produkt = mock_produkt1
        mock_stan1.ilosc = Decimal("2.0")
        mock_stan1.jednostka_miary = "l"
        mock_stan1.data_waznosci = date(2025, 1, 20)
        mock_stan1.zamrozone = False

        mock_stan2 = MagicMock()
        mock_stan2.produkt_id = 2
        mock_produkt2 = MagicMock()
        mock_produkt2.znormalizowana_nazwa = "Chleb"
        mock_kategoria2 = MagicMock()
        mock_kategoria2.nazwa_kategorii = "Pieczywo"
        mock_produkt2.kategoria = mock_kategoria2
        mock_stan2.produkt = mock_produkt2
        mock_stan2.ilosc = Decimal("1.0")
        mock_stan2.jednostka_miary = "szt"
        mock_stan2.data_waznosci = None
        mock_stan2.zamrozone = False

        self.mock_session.query.return_value.join.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_stan1,
            mock_stan2,
        ]

        result = self.assistant.get_available_products()

        assert len(result) == 2
        assert result[0]["nazwa"] == "Mleko"
        assert result[0]["total_ilosc"] == 2.0
        assert result[1]["nazwa"] == "Chleb"
        assert result[1]["total_ilosc"] == 1.0

    def test_get_available_products_empty(self):
        """Test gdy brak dostępnych produktów"""
        self.mock_session.query.return_value.join.return_value.options.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = self.assistant.get_available_products()

        assert len(result) == 0

    def teardown_method(self):
        """Czyszczenie po każdym teście"""
        if self.assistant:
            self.assistant.close()


class TestBielikAssistantSuggestDishes:
    """Testy dla proponowania potraw"""

    def setup_method(self):
        """Przygotowanie mocków przed każdym testem"""
        self.mock_session = MagicMock()
        self.assistant = BielikAssistant(session=self.mock_session)

    @patch("src.bielik.client")
    def test_suggest_dishes_success(self, mock_client):
        """Test pomyślnego proponowania potraw"""
        # Mock dostępnych produktów
        self.assistant.get_available_products = Mock(
            return_value=[
                {
                    "nazwa": "Mleko",
                    "kategoria": "Nabiał",
                    "total_ilosc": 2.0,
                    "stany": [{"jednostka": "l"}],
                },
                {
                    "nazwa": "Chleb",
                    "kategoria": "Pieczywo",
                    "total_ilosc": 1.0,
                    "stany": [{"jednostka": "szt"}],
                },
            ]
        )

        # Mock odpowiedzi LLM
        mock_response = {
            "potrawy": [
                {
                    "nazwa": "Kanapki z masłem",
                    "opis": "Proste kanapki z chlebem i masłem",
                    "skladniki": ["Chleb", "Masło"],
                    "czas_przygotowania": "5 minut",
                    "trudnosc": "łatwa",
                }
            ]
        }
        mock_client.chat.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }

        result = self.assistant.suggest_dishes("śniadanie", max_dishes=5)

        assert len(result) == 1
        assert result[0]["nazwa"] == "Kanapki z masłem"
        assert "kanapki" in result[0]["opis"].lower()
        mock_client.chat.assert_called_once()

    @patch("src.bielik.client")
    def test_suggest_dishes_no_products(self, mock_client):
        """Test gdy brak produktów w magazynie"""
        self.assistant.get_available_products = Mock(return_value=[])

        result = self.assistant.suggest_dishes()

        assert len(result) == 1
        assert "Brak produktów" in result[0]["nazwa"]
        mock_client.chat.assert_not_called()

    @patch("src.bielik.client", None)
    def test_suggest_dishes_no_client(self):
        """Test gdy klient Ollama nie jest dostępny"""
        self.assistant.get_available_products = Mock(
            return_value=[
                {
                    "nazwa": "Mleko",
                    "kategoria": "Nabiał",
                    "total_ilosc": 1.0,
                    "stany": [{"jednostka": "l"}],
                }
            ]
        )

        result = self.assistant.suggest_dishes()

        assert len(result) == 1
        assert "Błąd połączenia" in result[0]["nazwa"]

    @patch("src.bielik.client")
    def test_suggest_dishes_invalid_json(self, mock_client):
        """Test gdy LLM zwraca niepoprawny JSON"""
        self.assistant.get_available_products = Mock(
            return_value=[
                {
                    "nazwa": "Mleko",
                    "kategoria": "Nabiał",
                    "total_ilosc": 1.0,
                    "stany": [{"jednostka": "l"}],
                }
            ]
        )

        mock_client.chat.return_value = {
            "message": {"content": "To nie jest JSON"}
        }

        result = self.assistant.suggest_dishes()

        # Powinien zwrócić błąd
        assert len(result) > 0
        assert "Błąd" in result[0].get("nazwa", "")

    def teardown_method(self):
        """Czyszczenie po każdym teście"""
        if self.assistant:
            self.assistant.close()


class TestBielikAssistantShoppingList:
    """Testy dla generowania list zakupów"""

    def setup_method(self):
        """Przygotowanie mocków przed każdym testem"""
        self.mock_session = MagicMock()
        self.assistant = BielikAssistant(session=self.mock_session)

    @patch("src.bielik.client")
    def test_generate_shopping_list_success(self, mock_client):
        """Test pomyślnego generowania listy zakupów"""
        # Mock dostępnych produktów
        self.assistant.get_available_products = Mock(
            return_value=[
                {
                    "nazwa": "Mleko",
                    "kategoria": "Nabiał",
                    "total_ilosc": 1.0,
                    "stany": [{"jednostka": "l"}],
                }
            ]
        )

        # Mock odpowiedzi LLM
        mock_response = {
            "potrawa": "Spaghetti",
            "produkty": [
                {
                    "nazwa": "Makaron",
                    "ilosc": "500g",
                    "kategoria": "Sypkie",
                    "priorytet": "wysoki",
                },
                {
                    "nazwa": "Pomidory",
                    "ilosc": "1kg",
                    "kategoria": "Warzywa",
                    "priorytet": "średni",
                },
            ],
            "uwagi": "Kup świeże pomidory",
        }
        mock_client.chat.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }

        result = self.assistant.generate_shopping_list(dish_name="Spaghetti")

        assert result["potrawa"] == "Spaghetti"
        assert len(result["produkty"]) == 2
        assert result["produkty"][0]["nazwa"] == "Makaron"
        # Mleko nie powinno być na liście (już jest w magazynie)
        assert not any(p["nazwa"] == "Mleko" for p in result["produkty"])

    @patch("src.bielik.client")
    def test_generate_shopping_list_filters_existing(self, mock_client):
        """Test filtrowania produktów, które już są w magazynie"""
        self.assistant.get_available_products = Mock(
            return_value=[
                {
                    "nazwa": "Mleko",
                    "kategoria": "Nabiał",
                    "total_ilosc": 1.0,
                    "stany": [{"jednostka": "l"}],
                },
                {
                    "nazwa": "Chleb",
                    "kategoria": "Pieczywo",
                    "total_ilosc": 1.0,
                    "stany": [{"jednostka": "szt"}],
                },
            ]
        )

        # LLM zwraca listę z produktami, które już są w magazynie
        mock_response = {
            "potrawa": "Kanapki",
            "produkty": [
                {"nazwa": "Mleko", "ilosc": "1l", "kategoria": "Nabiał"},
                {"nazwa": "Chleb", "ilosc": "1szt", "kategoria": "Pieczywo"},
                {"nazwa": "Masło", "ilosc": "200g", "kategoria": "Nabiał"},
            ],
            "uwagi": "",
        }
        mock_client.chat.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }

        result = self.assistant.generate_shopping_list(dish_name="Kanapki")

        # Tylko Masło powinno być na liście (Mleko i Chleb już są)
        assert len(result["produkty"]) == 1
        assert result["produkty"][0]["nazwa"] == "Masło"

    @patch("src.bielik.client", None)
    def test_generate_shopping_list_no_client(self):
        """Test gdy klient Ollama nie jest dostępny"""
        self.assistant.get_available_products = Mock(return_value=[])

        result = self.assistant.generate_shopping_list(query="co potrzebuję?")

        assert result["produkty"] == []
        assert "Nie można połączyć" in result["uwagi"]

    def teardown_method(self):
        """Czyszczenie po każdym teście"""
        if self.assistant:
            self.assistant.close()


class TestBielikAssistantAnswerQuestion:
    """Testy dla odpowiadania na pytania"""

    def setup_method(self):
        """Przygotowanie mocków przed każdym testem"""
        self.mock_session = MagicMock()
        self.assistant = BielikAssistant(session=self.mock_session)

    @patch("src.bielik.client")
    def test_answer_question_success(self, mock_client):
        """Test pomyślnej odpowiedzi na pytanie"""
        # Mock wyszukiwania produktów
        self.assistant._search_products_rag = Mock(
            return_value=[
                {
                    "nazwa": "Mleko",
                    "kategoria": "Nabiał",
                    "has_stock": True,
                    "ilosc": 2.0,
                }
            ]
        )

        # Mock dostępnych produktów
        self.assistant.get_available_products = Mock(
            return_value=[
                {
                    "nazwa": "Mleko",
                    "kategoria": "Nabiał",
                    "total_ilosc": 2.0,
                    "stany": [{"jednostka": "l"}],
                }
            ]
        )

        # Mock odpowiedzi LLM
        mock_client.chat.return_value = {
            "message": {"content": "Masz mleko w magazynie, możesz zrobić z niego wiele potraw!"}
        }

        result = self.assistant.answer_question("co mam do jedzenia?")

        assert "mleko" in result.lower() or "Masz" in result
        mock_client.chat.assert_called_once()

    @patch("src.bielik.client", None)
    def test_answer_question_no_client(self):
        """Test gdy klient Ollama nie jest dostępny"""
        self.assistant._search_products_rag = Mock(return_value=[])
        self.assistant.get_available_products = Mock(return_value=[])

        result = self.assistant.answer_question("co mam do jedzenia?")

        assert "nie mogę połączyć" in result.lower() or "Ollama" in result

    @patch("src.bielik.client")
    def test_answer_question_with_products_context(self, mock_client):
        """Test odpowiedzi z kontekstem produktów"""
        self.assistant._search_products_rag = Mock(
            return_value=[
                {
                    "nazwa": "Chleb",
                    "kategoria": "Pieczywo",
                    "has_stock": True,
                    "ilosc": 1.0,
                }
            ]
        )
        self.assistant.get_available_products = Mock(return_value=[])

        mock_client.chat.return_value = {
            "message": {"content": "Masz chleb w bazie danych."}
        }

        result = self.assistant.answer_question("co to jest chleb?")

        assert "chleb" in result.lower()
        # Sprawdź czy kontekst produktów został przekazany
        call_args = mock_client.chat.call_args
        assert "Chleb" in str(call_args) or "chleb" in str(call_args).lower()

    def teardown_method(self):
        """Czyszczenie po każdym teście"""
        if self.assistant:
            self.assistant.close()


class TestBielikHelperFunctions:
    """Testy dla funkcji pomocniczych"""

    @patch("src.bielik.BielikAssistant")
    def test_ask_bielik(self, mock_assistant_class):
        """Test funkcji ask_bielik"""
        mock_assistant = MagicMock()
        mock_assistant.answer_question.return_value = "Odpowiedź"
        mock_assistant_class.return_value.__enter__.return_value = mock_assistant

        result = ask_bielik("pytanie")

        assert result == "Odpowiedź"
        mock_assistant.answer_question.assert_called_once_with("pytanie")

    @patch("src.bielik.BielikAssistant")
    def test_get_dish_suggestions(self, mock_assistant_class):
        """Test funkcji get_dish_suggestions"""
        mock_assistant = MagicMock()
        mock_assistant.suggest_dishes.return_value = [{"nazwa": "Potrawa"}]
        mock_assistant_class.return_value.__enter__.return_value = mock_assistant

        result = get_dish_suggestions("obiad", max_dishes=3)

        assert len(result) == 1
        assert result[0]["nazwa"] == "Potrawa"
        mock_assistant.suggest_dishes.assert_called_once_with("obiad", 3)

    @patch("src.bielik.BielikAssistant")
    def test_get_shopping_list(self, mock_assistant_class):
        """Test funkcji get_shopping_list"""
        mock_assistant = MagicMock()
        mock_assistant.generate_shopping_list.return_value = {
            "produkty": [{"nazwa": "Produkt"}]
        }
        mock_assistant_class.return_value.__enter__.return_value = mock_assistant

        result = get_shopping_list(dish_name="Potrawa")

        assert len(result["produkty"]) == 1
        mock_assistant.generate_shopping_list.assert_called_once_with("Potrawa", None)


class TestBielikContextManager:
    """Testy dla context managera"""

    def test_context_manager(self):
        """Test użycia BielikAssistant jako context manager"""
        mock_session = MagicMock()

        with BielikAssistant(session=mock_session) as assistant:
            assert assistant is not None
            assert assistant.session == mock_session

        # Po wyjściu z context managera, sesja powinna być zamknięta
        mock_session.close.assert_called_once()

    def test_context_manager_exception(self):
        """Test context managera przy wyjątku"""
        mock_session = MagicMock()

        try:
            with BielikAssistant(session=mock_session) as assistant:
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Sesja powinna być zamknięta nawet przy wyjątku
        mock_session.close.assert_called_once()

