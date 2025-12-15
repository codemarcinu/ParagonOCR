import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ReceiptParser")))

from src.llm import normalize_batch, normalize_products_batch
from src.config import Config

class TestBatchNormalization(unittest.TestCase):
    
    @patch('src.llm.client')
    def test_normalize_batch_basic(self, mock_client):
        # Setup mock response
        mock_response = {
            "message": {
                "content": '{"Mleko Łaciate": "Mleko", "Mąka Tortowa": "Mąka"}'
            }
        }
        mock_client.chat.return_value = mock_response
        
        raw_names = ["Mleko Łaciate", "Mąka Tortowa"]
        results = normalize_batch(raw_names)
        
        self.assertEqual(results["Mleko Łaciate"], "Mleko")
        self.assertEqual(results["Mąka Tortowa"], "Mąka")
        
        # Verify llm was called with format='json'
        args, kwargs = mock_client.chat.call_args
        self.assertEqual(kwargs['format'], 'json')

    @patch('src.llm.client')
    def test_normalize_batch_json_failure(self, mock_client):
        # Setup mock response with bad JSON
        mock_response = {
            "message": {
                "content": 'Not a JSON'
            }
        }
        mock_client.chat.return_value = mock_response
        
        raw_names = ["Item1"]
        results = normalize_batch(raw_names)
        
        # Should return None for items on failure
        self.assertIsNone(results["Item1"])

    @patch('src.llm.normalize_batch')
    def test_normalize_products_batch_threading(self, mock_normalize_batch):
        # Mock the inner function to return dummy results
        def side_effect(names, *args, **kwargs):
            return {name: f"Normalized_{name}" for name in names}
        
        mock_normalize_batch.side_effect = side_effect
        
        raw_names = [f"Item{i}" for i in range(10)]
        
        # Use small batch size to force multiple batches
        results = normalize_products_batch(
            raw_names, 
            session=MagicMock(), 
            batch_size=2, 
            max_workers=2
        )
        
        self.assertEqual(len(results), 10)
        self.assertEqual(results["Item0"], "Normalized_Item0")
        self.assertEqual(results["Item9"], "Normalized_Item9")
        
        # Check that it was called multiple times (10 items / 2 batch_size = 5 calls)
        self.assertEqual(mock_normalize_batch.call_count, 5)

if __name__ == '__main__':
    unittest.main()
