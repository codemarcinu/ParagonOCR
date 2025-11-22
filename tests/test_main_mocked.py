"""
Testy dla main.py z mockami bazy danych
"""
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.main import save_to_database, resolve_product
from src.data_models import ParsedData


class TestSaveToDatabase:
    """Testy dla save_to_database z mockami"""

    @patch('src.main.Session')
    @patch('src.main.sessionmaker')
    def test_save_new_shop(self, mock_sessionmaker, mock_session_class):
        """Test zapisu z nowym sklepem"""
        # Mock sesji
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_sessionmaker.return_value.return_value = mock_session
        
        parsed_data: ParsedData = {
            "sklep_info": {"nazwa": "Lidl", "lokalizacja": "Test"},
            "paragon_info": {
                "data_zakupu": datetime(2024, 12, 27),
                "suma_calkowita": Decimal("26.34")
            },
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": Decimal("1.0"),
                    "jednostka": None,
                    "cena_jedn": Decimal("3.59"),
                    "cena_calk": Decimal("3.59"),
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("3.59")
                }
            ]
        }
        
        log_messages = []
        prompt_responses = {}
        
        def mock_log(msg):
            log_messages.append(msg)
        
        def mock_prompt(prompt_text, default, raw_name):
            return prompt_responses.get(raw_name, default)
        
        # Mock resolve_product
        with patch('src.main.resolve_product') as mock_resolve:
            mock_resolve.return_value = 1  # produkt_id
            
            save_to_database(
                mock_session,
                parsed_data,
                "test.jpg",
                mock_log,
                mock_prompt
            )
            
            # Sprawdź czy sklep został dodany
            assert mock_session.add.called
            # Sprawdź czy paragon został dodany
            assert "Przygotowano do zapisu" in log_messages[-1]

    @patch('src.main.Session')
    @patch('src.main.sessionmaker')
    def test_save_existing_shop(self, mock_sessionmaker, mock_session_class):
        """Test zapisu z istniejącym sklepem"""
        mock_session = MagicMock()
        mock_shop = MagicMock()
        mock_shop.sklep_id = 1
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_shop
        mock_sessionmaker.return_value.return_value = mock_session
        
        parsed_data: ParsedData = {
            "sklep_info": {"nazwa": "Lidl", "lokalizacja": "Test"},
            "paragon_info": {
                "data_zakupu": datetime(2024, 12, 27),
                "suma_calkowita": Decimal("10.00")
            },
            "pozycje": []
        }
        
        log_messages = []
        
        def mock_log(msg):
            log_messages.append(msg)
        
        def mock_prompt(prompt_text, default, raw_name):
            return default
        
        with patch('src.main.resolve_product'):
            save_to_database(
                mock_session,
                parsed_data,
                "test.jpg",
                mock_log,
                mock_prompt
            )
            
            # Sprawdź czy sklep NIE został dodany ponownie
            add_calls = [call for call in mock_session.add.call_args_list 
                        if 'Sklep' in str(call)]
            assert len(add_calls) == 0


class TestResolveProduct:
    """Testy dla resolve_product z mockami"""

    @patch('src.main.get_product_metadata')
    @patch('src.main.find_static_match')
    def test_resolve_existing_alias(self, mock_find_static, mock_get_metadata):
        """Test gdy alias już istnieje w bazie"""
        mock_session = MagicMock()
        
        # Mock aliasu
        mock_alias = MagicMock()
        mock_alias.produkt_id = 5
        mock_produkt = MagicMock()
        mock_produkt.znormalizowana_nazwa = "Mleko"
        mock_alias.produkt = mock_produkt
        
        mock_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = mock_alias
        
        log_messages = []
        
        def mock_log(msg):
            log_messages.append(msg)
        
        def mock_prompt(prompt_text, default, raw_name):
            return default
        
        result = resolve_product(mock_session, "Mleko UHT", mock_log, mock_prompt)
        
        assert result == 5
        assert "Znaleziono alias" in log_messages[0]

    @patch('src.main.get_product_metadata')
    @patch('src.main.find_static_match')
    def test_resolve_static_match(self, mock_find_static, mock_get_metadata):
        """Test gdy produkt pasuje do reguły statycznej"""
        mock_session = MagicMock()
        
        # Brak aliasu
        mock_query_alias = MagicMock()
        mock_query_alias.options.return_value.filter_by.return_value.first.return_value = None
        
        # Reguła statyczna zwraca "Mleko"
        mock_find_static.return_value = "Mleko"
        
        # Brak produktu w bazie
        mock_query_produkt = MagicMock()
        mock_query_produkt.filter_by.return_value.first.return_value = None
        
        # Mock kategorii
        mock_query_kategoria = MagicMock()
        mock_kategoria = MagicMock()
        mock_kategoria.kategoria_id = 1
        mock_query_kategoria.filter_by.return_value.first.return_value = mock_kategoria
        
        # Konfiguracja query chain - musimy użyć callable który zwraca odpowiednie query
        def query_side_effect(model_class):
            if 'AliasProduktu' in str(model_class):
                return mock_query_alias
            elif 'Produkt' in str(model_class):
                return mock_query_produkt
            elif 'KategoriaProduktu' in str(model_class):
                return mock_query_kategoria
            return MagicMock()
        
        mock_session.query = query_side_effect
        
        # Mock produktu który zostanie utworzony
        mock_product = MagicMock()
        mock_product.produkt_id = 10
        
        # Mock add - symuluje dodanie obiektów
        added_objects = []
        def add_side_effect(obj):
            added_objects.append(obj)
            # Jeśli to produkt, ustaw produkt_id
            if hasattr(obj, 'znormalizowana_nazwa') and hasattr(obj, 'kategoria_id'):
                obj.produkt_id = 10
        mock_session.add = add_side_effect
        
        # Mock flush - po flush produkt ma ID
        def flush_side_effect():
            for obj in added_objects:
                if hasattr(obj, 'znormalizowana_nazwa') and not hasattr(obj, 'produkt_id'):
                    obj.produkt_id = 10
                elif hasattr(obj, 'nazwa_kategorii') and not hasattr(obj, 'kategoria_id'):
                    obj.kategoria_id = 1
        mock_session.flush = flush_side_effect
        
        mock_get_metadata.return_value = {"kategoria": "Nabiał", "can_freeze": True}
        
        log_messages = []
        
        def mock_log(msg):
            log_messages.append(msg)
        
        def mock_prompt(prompt_text, default, raw_name):
            return "Mleko"  # Użytkownik akceptuje sugestię
        
        result = resolve_product(mock_session, "Mleko UHT 3,2%", mock_log, mock_prompt)
        
        # Powinno utworzyć nowy produkt i alias
        assert len(added_objects) >= 2  # Kategoria + Produkt + Alias
        assert result == 10  # produkt_id

    @patch('src.main.get_llm_suggestion')
    @patch('src.main.get_product_metadata')
    @patch('src.main.find_static_match')
    def test_resolve_llm_suggestion(self, mock_find_static, mock_get_metadata, mock_llm):
        """Test gdy używa się sugestii LLM"""
        mock_session = MagicMock()
        
        # Brak aliasu
        mock_query_alias = MagicMock()
        mock_query_alias.options.return_value.filter_by.return_value.first.return_value = None
        
        # Brak reguły statycznej
        mock_find_static.return_value = None
        
        # LLM sugeruje "Chleb"
        mock_llm.return_value = "Chleb"
        
        # Brak produktu w bazie
        mock_query_produkt = MagicMock()
        mock_query_produkt.filter_by.return_value.first.return_value = None
        
        # Mock kategorii
        mock_query_kategoria = MagicMock()
        mock_kategoria = MagicMock()
        mock_kategoria.kategoria_id = 2
        mock_query_kategoria.filter_by.return_value.first.return_value = mock_kategoria
        
        def query_side_effect(model_class):
            if 'AliasProduktu' in str(model_class):
                return mock_query_alias
            elif 'Produkt' in str(model_class):
                return mock_query_produkt
            elif 'KategoriaProduktu' in str(model_class):
                return mock_query_kategoria
            return MagicMock()
        
        mock_session.query = query_side_effect
        
        # Mock add - symuluje dodanie obiektów
        added_objects = []
        def add_side_effect(obj):
            added_objects.append(obj)
            # Jeśli to produkt, ustaw produkt_id
            if hasattr(obj, 'znormalizowana_nazwa') and hasattr(obj, 'kategoria_id'):
                obj.produkt_id = 20
        mock_session.add = add_side_effect
        
        # Mock flush - po flush produkt ma ID
        def flush_side_effect():
            for obj in added_objects:
                if hasattr(obj, 'znormalizowana_nazwa') and not hasattr(obj, 'produkt_id'):
                    obj.produkt_id = 20
                elif hasattr(obj, 'nazwa_kategorii') and not hasattr(obj, 'kategoria_id'):
                    obj.kategoria_id = 2
        mock_session.flush = flush_side_effect
        
        mock_get_metadata.return_value = {"kategoria": "Pieczywo", "can_freeze": True}
        
        log_messages = []
        
        def mock_log(msg):
            log_messages.append(msg)
        
        def mock_prompt(prompt_text, default, raw_name):
            return "Chleb"
        
        result = resolve_product(mock_session, "Chleb Baltonowski", mock_log, mock_prompt)
        
        assert "Sugestia (LLM)" in str(log_messages)
        assert result == 20  # produkt_id

    @patch('src.main.find_static_match')
    def test_resolve_skip_product(self, mock_find_static):
        """Test gdy produkt powinien być pominięty"""
        mock_session = MagicMock()
        mock_session.query.return_value.options.return_value.filter_by.return_value.first.return_value = None
        mock_find_static.return_value = "POMIŃ"
        
        log_messages = []
        
        def mock_log(msg):
            log_messages.append(msg)
        
        def mock_prompt(prompt_text, default, raw_name):
            return ""  # Użytkownik pomija
        
        result = resolve_product(mock_session, "Reklamówka", mock_log, mock_prompt)
        
        assert result is None

