"""
Testy dla mistral_ocr.py z mockami API
"""
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.mistral_ocr import MistralOCRClient


class TestMistralOCRClient:
    """Testy dla MistralOCRClient z mockami"""

    @patch('src.mistral_ocr.Config')
    @patch('src.mistral_ocr.Mistral')
    def test_init_with_api_key(self, mock_mistral_class, mock_config):
        """Test inicjalizacji z kluczem API"""
        mock_config.MISTRAL_API_KEY = "test_key_123"
        
        client = MistralOCRClient()
        
        assert client.client is not None
        mock_mistral_class.assert_called_once_with(api_key="test_key_123")

    @patch('src.mistral_ocr.Config')
    def test_init_without_api_key(self, mock_config):
        """Test inicjalizacji bez klucza API"""
        mock_config.MISTRAL_API_KEY = ""
        
        client = MistralOCRClient()
        
        assert client.client is None

    @patch('src.mistral_ocr.Config')
    @patch('src.mistral_ocr.Mistral')
    @patch('src.mistral_ocr.os.path.exists')
    @patch('builtins.open', create=True)
    def test_process_image_success(self, mock_open, mock_exists, mock_mistral_class, mock_config):
        """Test pomyślnego przetwarzania obrazu"""
        mock_config.MISTRAL_API_KEY = "test_key"
        mock_exists.return_value = True
        
        # Mock klienta
        mock_client = MagicMock()
        mock_mistral_class.return_value = mock_client
        
        # Mock uploadu pliku
        mock_file_response = MagicMock()
        mock_file_response.id = "file_123"
        mock_client.files.upload.return_value = mock_file_response
        
        # Mock signed URL
        mock_signed_url = MagicMock()
        mock_signed_url.url = "https://signed.url/file"
        mock_client.files.get_signed_url.return_value = mock_signed_url
        
        # Mock OCR response
        mock_ocr_response = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.markdown = "# Page 1\nText content"
        mock_page2 = MagicMock()
        mock_page2.markdown = "# Page 2\nMore text"
        mock_ocr_response.pages = [mock_page1, mock_page2]
        mock_client.ocr.process.return_value = mock_ocr_response
        
        # Mock open
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_open.return_value.__exit__.return_value = None
        
        client = MistralOCRClient()
        result = client.process_image("test.jpg")
        
        assert result is not None
        assert "Page 1" in result
        assert "Page 2" in result
        mock_client.files.upload.assert_called_once()
        mock_client.ocr.process.assert_called_once()

    @patch('src.mistral_ocr.Config')
    @patch('src.mistral_ocr.Mistral')
    def test_process_image_no_client(self, mock_mistral_class, mock_config):
        """Test gdy klient nie jest zainicjalizowany"""
        mock_config.MISTRAL_API_KEY = ""
        
        client = MistralOCRClient()
        result = client.process_image("test.jpg")
        
        assert result is None

    @patch('src.mistral_ocr.Config')
    @patch('src.mistral_ocr.Mistral')
    @patch('os.path.exists')
    def test_process_image_file_not_exists(self, mock_exists, mock_mistral_class, mock_config):
        """Test gdy plik nie istnieje"""
        mock_config.MISTRAL_API_KEY = "test_key"
        mock_exists.return_value = False
        
        mock_client = MagicMock()
        mock_mistral_class.return_value = mock_client
        
        client = MistralOCRClient()
        result = client.process_image("nonexistent.jpg")
        
        assert result is None

    @patch('src.mistral_ocr.Config')
    @patch('src.mistral_ocr.Mistral')
    @patch('builtins.open', create=True)
    def test_process_image_exception(self, mock_open, mock_mistral_class, mock_config):
        """Test obsługi wyjątków"""
        mock_config.MISTRAL_API_KEY = "test_key"
        
        mock_client = MagicMock()
        mock_mistral_class.return_value = mock_client
        mock_client.files.upload.side_effect = Exception("API Error")
        
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_open.return_value.__exit__.return_value = None
        
        client = MistralOCRClient()
        result = client.process_image("test.jpg")
        
        assert result is None

    @patch('src.mistral_ocr.Config')
    @patch('src.mistral_ocr.Mistral')
    @patch('src.mistral_ocr.os.path.exists')
    @patch('builtins.open', create=True)
    def test_process_image_single_page(self, mock_open, mock_exists, mock_mistral_class, mock_config):
        """Test przetwarzania obrazu z jedną stroną"""
        mock_config.MISTRAL_API_KEY = "test_key"
        mock_exists.return_value = True
        
        mock_client = MagicMock()
        mock_mistral_class.return_value = mock_client
        
        mock_file_response = MagicMock()
        mock_file_response.id = "file_123"
        mock_client.files.upload.return_value = mock_file_response
        
        mock_signed_url = MagicMock()
        mock_signed_url.url = "https://signed.url/file"
        mock_client.files.get_signed_url.return_value = mock_signed_url
        
        mock_ocr_response = MagicMock()
        mock_page = MagicMock()
        mock_page.markdown = "Single page content"
        mock_ocr_response.pages = [mock_page]
        mock_client.ocr.process.return_value = mock_ocr_response
        
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_open.return_value.__exit__.return_value = None
        
        client = MistralOCRClient()
        result = client.process_image("single_page.jpg")
        
        assert result is not None
        assert "Single page content" in result

