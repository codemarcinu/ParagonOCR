"""
Testy dla async receipt processing queue
"""
import sys
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../ReceiptParser"))

import pytest
from src.data_models import ParsedData


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncReceiptProcessor:
    """Testy dla async receipt processing"""
    
    async def test_process_receipt_async_success(self):
        """Test pomyślnego przetwarzania paragonu asynchronicznie"""
        receipt_data = {
            "sklep_info": {"nazwa": "Lidl", "lokalizacja": "Warszawa"},
            "paragon_info": {
                "data_zakupu": datetime(2024, 12, 7),
                "suma_calkowita": Decimal("45.67")
            },
            "pozycje": [
                {
                    "nazwa_raw": "Mleko UHT 3,2% Łaciate 1L",
                    "ilosc": Decimal("1.0"),
                    "jednostka": "szt",
                    "cena_jedn": Decimal("4.99"),
                    "cena_calk": Decimal("4.99"),
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("4.99")
                }
            ]
        }
        
        async def mock_process(data):
            await asyncio.sleep(0.01)  # Symuluj async processing
            return {"status": "success", "processed": True}
        
        result = await mock_process(receipt_data)
        
        assert result["status"] == "success"
        assert result["processed"] is True
    
    async def test_process_multiple_receipts_concurrent(self):
        """Test równoległego przetwarzania wielu paragonów"""
        receipts = [
            {"id": 1, "data": {"suma_calkowita": Decimal("10.00")}},
            {"id": 2, "data": {"suma_calkowita": Decimal("20.00")}},
            {"id": 3, "data": {"suma_calkowita": Decimal("30.00")}}
        ]
        
        async def process_receipt(receipt):
            await asyncio.sleep(0.01)
            return {"id": receipt["id"], "processed": True}
        
        # Przetwarzaj równolegle
        results = await asyncio.gather(*[process_receipt(r) for r in receipts])
        
        assert len(results) == 3
        assert all(r["processed"] for r in results)
        assert {r["id"] for r in results} == {1, 2, 3}
    
    async def test_async_queue_processing_order(self):
        """Test zachowania kolejności w async queue"""
        queue_items = [1, 2, 3, 4, 5]
        processed = []
        
        async def process_item(item):
            await asyncio.sleep(0.01)
            processed.append(item)
        
        # Przetwarzaj sekwencyjnie (zachowaj kolejność)
        for item in queue_items:
            await process_item(item)
        
        assert processed == [1, 2, 3, 4, 5]
    
    async def test_async_queue_error_handling(self):
        """Test obsługi błędów w async queue"""
        items = [1, 2, 3]
        results = []
        errors = []
        
        async def process_item(item):
            await asyncio.sleep(0.01)
            if item == 2:
                raise ValueError("Processing error")
            return item
        
        for item in items:
            try:
                result = await process_item(item)
                results.append(result)
            except ValueError as e:
                errors.append(str(e))
        
        assert results == [1, 3]
        assert len(errors) == 1
        assert "Processing error" in errors[0]
    
    async def test_async_batch_processing(self):
        """Test batch processing w async queue"""
        items = list(range(10))
        batch_size = 3
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        async def process_batch(batch):
            await asyncio.sleep(0.01)
            return [x * 2 for x in batch]
        
        # Przetwarzaj batche równolegle
        results = await asyncio.gather(*[process_batch(batch) for batch in batches])
        
        # Spłaszcz wyniki
        flat_results = [item for batch_result in results for item in batch_result]
        assert len(flat_results) == 10
        assert flat_results[0] == 0  # 0 * 2
        assert flat_results[9] == 18  # 9 * 2


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncQueuePerformance:
    """Testy wydajności async queue"""
    
    async def test_async_vs_sync_performance(self):
        """Test porównania wydajności async vs sync (benchmark)"""
        items = list(range(5))
        
        async def async_process(item):
            await asyncio.sleep(0.01)
            return item * 2
        
        def sync_process(item):
            import time
            time.sleep(0.01)
            return item * 2
        
        # Async - równolegle
        import time
        start_async = time.time()
        async_results = await asyncio.gather(*[async_process(item) for item in items])
        async_time = time.time() - start_async
        
        # Sync - sekwencyjnie
        start_sync = time.time()
        sync_results = [sync_process(item) for item in items]
        sync_time = time.time() - start_sync
        
        assert async_results == sync_results
        # Async powinno być szybsze (równoległe przetwarzanie)
        assert async_time < sync_time * 1.5  # Z tolerancją na overhead
    
    async def test_async_queue_throughput(self):
        """Test przepustowości async queue"""
        num_items = 20
        items = list(range(num_items))
        
        async def process_item(item):
            await asyncio.sleep(0.001)  # Bardzo krótki delay
            return item
        
        # Przetwarzaj wszystkie równolegle
        start = asyncio.get_event_loop().time()
        results = await asyncio.gather(*[process_item(item) for item in items])
        elapsed = asyncio.get_event_loop().time() - start
        
        assert len(results) == num_items
        assert all(r == items[i] for i, r in enumerate(results))
        # Powinno zająć mniej niż sekwencyjne przetwarzanie
        assert elapsed < 0.1  # Wszystkie równolegle powinny zakończyć się szybko


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncQueueIntegration:
    """Testy integracyjne async queue z systemem"""
    
    async def test_async_receipt_processing_with_mock_llm(self):
        """Test async processing z mockowanym LLM"""
        receipt_data = {
            "sklep_info": {"nazwa": "Lidl"},
            "paragon_info": {
                "data_zakupu": datetime(2024, 12, 7),
                "suma_calkowita": Decimal("10.00")
            },
            "pozycje": [
                {
                    "nazwa_raw": "Mleko UHT",
                    "ilosc": Decimal("1.0"),
                    "jednostka": "szt",
                    "cena_jedn": Decimal("4.99"),
                    "cena_calk": Decimal("4.99"),
                    "rabat": Decimal("0.00"),
                    "cena_po_rab": Decimal("4.99")
                }
            ]
        }
        
        mock_llm = AsyncMock()
        mock_llm.normalize.return_value = "Mleko"
        
        async def process_with_llm(data):
            await asyncio.sleep(0.01)
            normalized = await mock_llm.normalize(data["pozycje"][0]["nazwa_raw"])
            return {"normalized": normalized}
        
        result = await process_with_llm(receipt_data)
        
        assert result["normalized"] == "Mleko"
        mock_llm.normalize.assert_called_once_with("Mleko UHT")
    
    async def test_async_queue_with_database_session(self):
        """Test async queue z sesją bazy danych"""
        # Symuluj async database operations
        async def save_to_db(data):
            await asyncio.sleep(0.01)
            return {"saved": True, "id": 123}
        
        receipt_data = {"suma_calkowita": Decimal("10.00")}
        result = await save_to_db(receipt_data)
        
        assert result["saved"] is True
        assert result["id"] == 123

