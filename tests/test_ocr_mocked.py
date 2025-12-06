"""
Testy dla ocr.py z mockami zewnętrznych bibliotek
"""
import sys
import os
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../ReceiptParser"))

from src.ocr import convert_pdf_to_image, extract_text_from_image


class TestConvertPDFToImage:
    """Testy dla convert_pdf_to_image z mockami"""

    @patch('src.ocr.convert_from_path')
    @patch('tempfile.NamedTemporaryFile')
    def test_convert_single_page(self, mock_tempfile, mock_convert):
        """Test konwersji PDF z jedną stroną"""
        # Mock obrazu
        mock_image = MagicMock()
        mock_image.width = 100
        mock_image.height = 200
        mock_convert.return_value = [mock_image]
        
        # Mock pliku tymczasowego
        mock_file = MagicMock()
        mock_file.name = "/tmp/test.jpg"
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_tempfile.return_value = mock_file
        
        result = convert_pdf_to_image("test.pdf")
        
        assert result == "/tmp/test.jpg"
        mock_image.save.assert_called_once()

    @patch('src.ocr.convert_from_path')
    @patch('tempfile.NamedTemporaryFile')
    def test_convert_multiple_pages(self, mock_tempfile, mock_convert):
        """Test konwersji PDF z wieloma stronami"""
        # Mock wielu obrazów
        mock_image1 = MagicMock()
        mock_image1.width = 100
        mock_image1.height = 200
        
        mock_image2 = MagicMock()
        mock_image2.width = 100
        mock_image2.height = 150
        
        mock_convert.return_value = [mock_image1, mock_image2]
        
        # Mock pliku tymczasowego
        mock_file = MagicMock()
        mock_file.name = "/tmp/merged.jpg"
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        mock_tempfile.return_value = mock_file
        
        # Mock Image.new
        with patch('src.ocr.Image') as mock_image_class:
            mock_merged = MagicMock()
            mock_image_class.new.return_value = mock_merged
            
            result = convert_pdf_to_image("multi_page.pdf")
            
            assert result == "/tmp/merged.jpg"
            # Sprawdź czy obrazy zostały sklejone
            assert mock_merged.paste.call_count == 2

    @patch('src.ocr.convert_from_path')
    def test_convert_empty_pdf(self, mock_convert):
        """Test gdy PDF jest pusty"""
        mock_convert.return_value = []
        
        result = convert_pdf_to_image("empty.pdf")
        
        assert result is None

    @patch('src.ocr.convert_from_path')
    def test_convert_exception(self, mock_convert):
        """Test obsługi wyjątków"""
        mock_convert.side_effect = Exception("PDF conversion failed")
        
        result = convert_pdf_to_image("invalid.pdf")
        
        assert result is None


class TestExtractTextFromImage:
    """Testy dla extract_text_from_image z mockami"""

    @patch('src.ocr.pytesseract')
    @patch('src.ocr.Image')
    def test_extract_text_success(self, mock_image, mock_pytesseract):
        """Test pomyślnej ekstrakcji tekstu"""
        mock_pytesseract.image_to_string.return_value = "Lidl sp. z o.o.\nProdukt 3.59"
        
        result = extract_text_from_image("test.jpg")
        
        assert result == "Lidl sp. z o.o.\nProdukt 3.59"
        mock_pytesseract.image_to_string.assert_called_once()
        # Sprawdź czy użyto polskiego języka
        call_args = mock_pytesseract.image_to_string.call_args
        assert "pol" in str(call_args)

    @patch('src.ocr.pytesseract')
    @patch('src.ocr.Image')
    def test_extract_text_empty(self, mock_image, mock_pytesseract):
        """Test gdy OCR zwraca pusty tekst"""
        mock_pytesseract.image_to_string.return_value = ""
        
        result = extract_text_from_image("empty.jpg")
        
        assert result == ""

    @patch('src.ocr.pytesseract')
    @patch('src.ocr.Image')
    def test_extract_text_exception(self, mock_image, mock_pytesseract):
        """Test obsługi wyjątków"""
        mock_pytesseract.image_to_string.side_effect = Exception("OCR failed")
        
        result = extract_text_from_image("invalid.jpg")
        
        assert result == ""

    @patch('src.ocr.Image')
    def test_extract_text_file_not_found(self, mock_image):
        """Test gdy plik nie istnieje"""
        mock_image.open.side_effect = FileNotFoundError("File not found")
        
        with patch('src.ocr.pytesseract') as mock_pytesseract:
            result = extract_text_from_image("nonexistent.jpg")
            
            # Powinno zwrócić pusty string po obsłudze wyjątku
            assert isinstance(result, str)







