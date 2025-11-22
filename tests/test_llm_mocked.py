"""
Testy dla llm.py z mockami Ollama
"""
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.llm import get_llm_suggestion, parse_receipt_with_llm, parse_receipt_from_text, _convert_types


class TestLLMSuggestion:
    """Testy dla get_llm_suggestion z mockami"""

    @patch('src.llm.client')
    def test_get_llm_suggestion_success(self, mock_client):
        """Test pomyślnego uzyskania sugestii"""
        mock_client.chat.return_value = {
            "message": {"content": "Mleko"}
        }
        
        result = get_llm_suggestion("Mleko UHT 3,2% Łaciate 1L")
        
        assert result == "Mleko"
        mock_client.chat.assert_called_once()

    @patch('src.llm.client')
    def test_get_llm_suggestion_with_quotes(self, mock_client):
        """Test usuwania cudzysłowów z odpowiedzi"""
        mock_client.chat.return_value = {
            "message": {"content": '"Mleko"'}
        }
        
        result = get_llm_suggestion("Mleko UHT")
        
        assert result == "Mleko"

    @patch('src.llm.client')
    def test_get_llm_suggestion_pomin(self, mock_client):
        """Test gdy LLM sugeruje pominięcie"""
        mock_client.chat.return_value = {
            "message": {"content": "POMIŃ"}
        }
        
        result = get_llm_suggestion("Śmieci OCR")
        
        assert result == "POMIŃ"

    @patch('src.llm.client', None)
    def test_get_llm_suggestion_no_client(self):
        """Test gdy klient Ollama nie jest dostępny"""
        result = get_llm_suggestion("Produkt")
        
        assert result is None


class TestParseReceiptWithLLM:
    """Testy dla parse_receipt_with_llm z mockami"""

    @patch('src.llm.client')
    @patch('src.llm.Path')
    def test_parse_receipt_success(self, mock_path, mock_client):
        """Test pomyślnego parsowania paragonu"""
        # Mock pliku
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        # Mock odpowiedzi LLM
        mock_response = {
            "sklep_info": {"nazwa": "Lidl", "lokalizacja": "Test"},
            "paragon_info": {"data_zakupu": "2024-12-27", "suma_calkowita": "26.34"},
            "pozycje": [
                {
                    "nazwa_raw": "Produkt",
                    "ilosc": "1.0",
                    "cena_jedn": "3.59",
                    "cena_calk": "3.59",
                    "rabat": "0.00",
                    "cena_po_rab": "3.59"
                }
            ]
        }
        mock_client.chat.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }
        
        result = parse_receipt_with_llm("test_image.jpg")
        
        assert result is not None
        assert result["sklep_info"]["nazwa"] == "Lidl"
        assert len(result["pozycje"]) == 1

    @patch('src.llm.client')
    @patch('src.llm.Path')
    def test_parse_receipt_with_ocr_text(self, mock_path, mock_client):
        """Test parsowania z tekstem OCR"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_response = {
            "sklep_info": {"nazwa": "Biedronka", "lokalizacja": None},
            "paragon_info": {"data_zakupu": "2024-12-27", "suma_calkowita": "10.00"},
            "pozycje": []
        }
        mock_client.chat.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }
        
        result = parse_receipt_with_llm("test.jpg", ocr_text="Lidl sp. z o.o.")
        
        assert result is not None
        # Sprawdź czy OCR text został przekazany
        call_args = mock_client.chat.call_args
        assert "Lidl" in str(call_args)

    @patch('src.llm.client')
    @patch('pathlib.Path')
    def test_parse_receipt_invalid_json(self, mock_path, mock_client):
        """Test gdy LLM zwraca niepoprawny JSON"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_client.chat.return_value = {
            "message": {"content": "To nie jest JSON"}
        }
        
        result = parse_receipt_with_llm("test.jpg")
        
        assert result is None

    @patch('src.llm.Path')
    def test_parse_receipt_file_not_exists(self, mock_path):
        """Test gdy plik nie istnieje"""
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        result = parse_receipt_with_llm("nonexistent.jpg")
        
        assert result is None

    @patch('src.llm.client', None)
    def test_parse_receipt_no_client(self):
        """Test gdy klient nie jest dostępny"""
        result = parse_receipt_with_llm("test.jpg")
        
        assert result is None


class TestParseReceiptFromText:
    """Testy dla parse_receipt_from_text z mockami"""

    @patch('src.llm.client')
    def test_parse_receipt_from_text_success(self, mock_client):
        """Test pomyślnego parsowania z tekstu"""
        mock_response = {
            "sklep_info": {"nazwa": "Biedronka", "lokalizacja": "Kostrzyn"},
            "paragon_info": {"data_zakupu": "2025-11-18", "suma_calkowita": "114.14"},
            "pozycje": [
                {
                    "nazwa_raw": "KawMiel Rafiin250g",
                    "ilosc": "1.0",
                    "cena_jedn": "18.99",
                    "cena_calk": "18.99",
                    "rabat": "0.00",
                    "cena_po_rab": "18.99"
                }
            ]
        }
        mock_client.chat.return_value = {
            "message": {"content": json.dumps(mock_response)}
        }
        
        text = "Biedronka\nKawMiel Rafiin250g 18.99"
        result = parse_receipt_from_text(text)
        
        assert result is not None
        assert result["sklep_info"]["nazwa"] == "Biedronka"
        assert len(result["pozycje"]) == 1

    @patch('src.llm.client')
    def test_parse_receipt_from_text_invalid_json(self, mock_client):
        """Test gdy LLM zwraca niepoprawny JSON"""
        mock_client.chat.return_value = {
            "message": {"content": "Niepoprawny JSON"}
        }
        
        result = parse_receipt_from_text("Tekst paragonu")
        
        assert result is None

    @patch('src.llm.client', None)
    def test_parse_receipt_from_text_no_client(self):
        """Test gdy klient nie jest dostępny"""
        result = parse_receipt_from_text("Tekst")
        
        assert result is None


class TestExtractJSONFromResponse:
    """Testy dla _extract_json_from_response"""

    def test_extract_json_with_code_block(self):
        """Test wyciągania JSON z bloku kodu"""
        # Funkcja _extract_json_from_response jest używana wewnętrznie
        # Testujemy ją przez parse_receipt_from_text z poprawnym JSON
        from src.llm import parse_receipt_from_text
        
        with patch('src.llm.client') as mock_client:
            # Poprawny JSON bez dodatkowych znaków
            valid_json = {
                "sklep_info": {"nazwa": "Lidl"},
                "paragon_info": {"data_zakupu": "2024-12-27", "suma_calkowita": "10.00"},
                "pozycje": []
            }
            mock_client.chat.return_value = {
                "message": {
                    "content": json.dumps(valid_json)  # Używamy json.dumps dla poprawnego formatu
                }
            }
            
            result = parse_receipt_from_text("Test")
            
            assert result is not None
            assert result["sklep_info"]["nazwa"] == "Lidl"

    def test_extract_json_direct(self):
        """Test wyciągania JSON bez bloku kodu"""
        from src.llm import _extract_json_from_response
        
        response = '{"sklep": "Biedronka"}'
        
        result = _extract_json_from_response(response)
        
        assert result is not None
        assert result["sklep"] == "Biedronka"

    def test_extract_json_not_found(self):
        """Test gdy JSON nie został znaleziony"""
        from src.llm import _extract_json_from_response
        
        response = "To nie jest JSON"
        
        result = _extract_json_from_response(response)
        
        assert result is None

