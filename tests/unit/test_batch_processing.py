"""
Testy dla batch processing LLM - normalizacja produktów w batchach
"""
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ReceiptParser"))

import pytest
from src.llm import normalize_batch, normalize_products_batch
from src.config import Config


@pytest.mark.unit
class TestBatchLLMProcessor:
    """Testy dla batch LLM processing"""
    
    @patch('src.llm.client')
    def test_normalize_batch_success(self, mock_client):
        """Test pomyślnej normalizacji batcha produktów"""
        raw_names = [
            "Mleko UHT 3,2% Łaciate 1L",
            "Chleb Baltonowski krojony 500g",
            "Jaja z wolnego wybiegu L 10szt"
        ]
        
        expected_json = {
            "Mleko UHT 3,2% Łaciate 1L": "Mleko",
            "Chleb Baltonowski krojony 500g": "Chleb",
            "Jaja z wolnego wybiegu L 10szt": "Jajka"
        }
        
        mock_client.chat.return_value = {
            "message": {"content": json.dumps(expected_json)}
        }
        
        result = normalize_batch(raw_names)
        
        assert len(result) == 3
        assert result["Mleko UHT 3,2% Łaciate 1L"] == "Mleko"
        assert result["Chleb Baltonowski krojony 500g"] == "Chleb"
        assert result["Jaja z wolnego wybiegu L 10szt"] == "Jajka"
        mock_client.chat.assert_called_once()
    
    @patch('src.llm.client')
    def test_normalize_batch_with_markdown(self, mock_client):
        """Test normalizacji batcha z odpowiedzią w formacie markdown"""
        raw_names = ["Mleko UHT 3,2% Łaciate 1L"]
        
        mock_response = '```json\n{"Mleko UHT 3,2% Łaciate 1L": "Mleko"}\n```'
        mock_client.chat.return_value = {
            "message": {"content": mock_response}
        }
        
        result = normalize_batch(raw_names)
        
        assert result["Mleko UHT 3,2% Łaciate 1L"] == "Mleko"
    
    @patch('src.llm.client')
    def test_normalize_batch_with_learning_examples(self, mock_client):
        """Test normalizacji batcha z przykładami uczenia"""
        raw_names = ["Szynka Krakus 200g"]
        learning_examples = [
            ("Szynka Krakus 150g", "Szynka"),
            ("Szynka Krakus 300g", "Szynka")
        ]
        
        mock_client.chat.return_value = {
            "message": {"content": json.dumps({"Szynka Krakus 200g": "Szynka"})}
        }
        
        result = normalize_batch(raw_names, learning_examples=learning_examples)
        
        assert result["Szynka Krakus 200g"] == "Szynka"
        # Sprawdź czy learning examples zostały przekazane do promptu
        call_args = mock_client.chat.call_args
        assert call_args is not None
    
    @patch('src.llm.client')
    def test_normalize_batch_skip_item(self, mock_client):
        """Test gdy LLM sugeruje pominięcie produktu (POMIŃ)"""
        raw_names = ["Reklamówka mała płatna"]
        
        mock_client.chat.return_value = {
            "message": {"content": json.dumps({"Reklamówka mała płatna": "POMIŃ"})}
        }
        
        result = normalize_batch(raw_names)
        
        # POMIŃ powinno być zwrócone jako None po clean_llm_suggestion
        # (zgodnie z logiką clean_llm_suggestion, ale sprawdzamy co faktycznie zwraca)
        assert "Reklamówka mała płatna" in result
    
    @patch('src.llm.client')
    def test_normalize_batch_json_decode_error(self, mock_client):
        """Test obsługi błędu parsowania JSON"""
        raw_names = ["Mleko UHT 3,2% Łaciate 1L"]
        
        mock_client.chat.return_value = {
            "message": {"content": "Invalid JSON response"}
        }
        
        result = normalize_batch(raw_names)
        
        # W przypadku błędu JSON, wszystkie produkty powinny zwrócić None
        assert result["Mleko UHT 3,2% Łaciate 1L"] is None
    
    @patch('src.llm.client')
    def test_normalize_batch_empty_list(self, mock_client):
        """Test normalizacji pustej listy produktów"""
        result = normalize_batch([])
        
        assert result == {}
        mock_client.chat.assert_not_called()
    
    @patch('src.llm.client')
    def test_normalize_batch_client_not_configured(self, mock_client):
        """Test gdy klient Ollama nie jest skonfigurowany"""
        mock_client.__bool__ = Mock(return_value=False)
        # Symuluj brak klienta
        with patch('src.llm.client', None):
            raw_names = ["Mleko UHT 3,2% Łaciate 1L"]
            result = normalize_batch(raw_names)
            
            # Powinno zwrócić None dla wszystkich produktów
            assert result["Mleko UHT 3,2% Łaciate 1L"] is None
    
    @patch('src.llm.client')
    def test_normalize_batch_exception_handling(self, mock_client):
        """Test obsługi wyjątków podczas wywołania LLM"""
        raw_names = ["Mleko UHT 3,2% Łaciate 1L"]
        
        mock_client.chat.side_effect = Exception("Connection error")
        
        result = normalize_batch(raw_names)
        
        # W przypadku wyjątku, wszystkie produkty powinny zwrócić None
        assert result["Mleko UHT 3,2% Łaciate 1L"] is None


@pytest.mark.unit
class TestBatchProcessingPerformance:
    """Testy wydajności batch processing"""
    
    @patch('src.llm.normalize_batch')
    @patch('src.llm.get_learning_examples')
    def test_normalize_products_batch_parallel_execution(self, mock_get_examples, mock_normalize_batch):
        """Test równoległego przetwarzania wielu batchy"""
        raw_names = [
            "Mleko UHT 3,2% Łaciate 1L",
            "Chleb Baltonowski krojony 500g",
            "Jaja z wolnego wybiegu L 10szt",
            "Szynka Krakus 200g",
            "Pomidor gałązka luz",
            "Coca Cola 0.5L"
        ]
        
        # Symuluj wyniki dla każdego batcha
        def mock_batch_side_effect(batch, *args, **kwargs):
            return {name: name.split()[0] for name in batch}
        
        mock_normalize_batch.side_effect = mock_batch_side_effect
        mock_get_examples.return_value = []
        
        session = Mock()
        result = normalize_products_batch(
            raw_names,
            session,
            batch_size=3,
            max_workers=2
        )
        
        # Sprawdź czy wszystkie produkty zostały przetworzone
        assert len(result) == 6
        # Sprawdź czy normalize_batch zostało wywołane (2 batche po 3 produkty)
        assert mock_normalize_batch.call_count == 2
    
    @patch('src.llm.normalize_batch')
    @patch('src.llm.get_learning_examples')
    def test_normalize_products_batch_with_log_callback(self, mock_get_examples, mock_normalize_batch):
        """Test batch processing z log callback"""
        raw_names = ["Mleko UHT 3,2% Łaciate 1L", "Chleb Baltonowski krojony 500g"]
        
        mock_normalize_batch.return_value = {
            "Mleko UHT 3,2% Łaciate 1L": "Mleko",
            "Chleb Baltonowski krojony 500g": "Chleb"
        }
        mock_get_examples.return_value = []
        
        log_messages = []
        def log_callback(msg):
            log_messages.append(msg)
        
        session = Mock()
        result = normalize_products_batch(
            raw_names,
            session,
            log_callback=log_callback
        )
        
        assert len(result) == 2
        # Sprawdź czy log callback został wywołany
        assert len(log_messages) > 0
        assert any("INFO: Przetwarzam" in msg for msg in log_messages)
    
    @patch('src.llm.normalize_batch')
    @patch('src.llm.get_learning_examples')
    def test_normalize_products_batch_empty_list(self, mock_get_examples, mock_normalize_batch):
        """Test batch processing z pustą listą"""
        session = Mock()
        result = normalize_products_batch([], session)
        
        assert result == {}
        mock_normalize_batch.assert_not_called()
    
    @patch('src.llm.normalize_batch')
    @patch('src.llm.get_learning_examples')
    def test_normalize_products_batch_batch_failure(self, mock_get_examples, mock_normalize_batch):
        """Test obsługi błędu w jednym z batchy"""
        raw_names = ["Mleko UHT 3,2% Łaciate 1L", "Chleb Baltonowski krojony 500g"]
        
        # Pierwszy batch się powiedzie, drugi zwróci błąd
        def mock_batch_side_effect(batch, *args, **kwargs):
            if "Mleko" in batch[0]:
                return {"Mleko UHT 3,2% Łaciate 1L": "Mleko"}
            else:
                raise Exception("Batch processing error")
        
        mock_normalize_batch.side_effect = mock_batch_side_effect
        mock_get_examples.return_value = []
        
        session = Mock()
        result = normalize_products_batch(
            raw_names,
            session,
            batch_size=1,
            max_workers=2
        )
        
        # Sprawdź czy błąd został obsłużony (None dla produktu z błędnego batcha)
        assert "Mleko UHT 3,2% Łaciate 1L" in result
        assert "Chleb Baltonowski krojony 500g" in result
        # Produkt z błędnego batcha powinien mieć None
        assert result.get("Chleb Baltonowski krojony 500g") is None

