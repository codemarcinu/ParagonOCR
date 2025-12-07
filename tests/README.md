# Testy ParagonOCR

## Przegląd

Projekt zawiera kompleksowe testy jednostkowe i integracyjne dla systemu parsowania paragonów.

## Statystyki testów

- **Łączna liczba testów**: 168+ (109 istniejących + 59 nowych)
- **Status**: ✅ Większość testów przechodzi (8 pre-existing failures)
- **Pokrycie kodu**: 26% overall, 73%+ dla głównych modułów (70-100%)

### Testing Phase 2 (2025-12-07)

- **Nowe testy dodane**: 59 testów
- **Nowe pliki testowe**: 5 plików
- **Kategorie testów**:
  - Batch Processing: 12 testów
  - Async Queue: 9 testów
  - Database: 13 testów
  - GUI: 16 testów
  - E2E Workflow: 9 testów
- **Infrastruktura**: pytest.ini, conftest.py z fixtures

## Struktura testów

### 1. `test_strategies.py` - Testy strategii parsowania
- **LidlStrategy**: Scalanie rabatów, obsługa wielu rabatów
- **BiedronkaStrategy**: Scalanie rabatów, wykrywanie po nazwie
- **AuchanStrategy**: Usuwanie śmieci OCR
- **Wybór strategii**: Automatyczna detekcja sklepu

### 2. `test_normalization.py` - Testy normalizacji produktów
- Normalizacja kategorii produktów (mleko, pieczywo, nabiał, etc.)
- Obsługa kaucji i opłat recyklingowych
- Pomijanie nieistotnych pozycji
- Case-insensitive matching

### 3. `test_knowledge_base.py` - Testy bazy wiedzy
- Metadane produktów (kategoria, can_freeze)
- Normalizacja nazw sklepów
- Obsługa nieznanych produktów

### 4. `test_math_verification.py` - Testy weryfikacji matematycznej
- Wykrywanie ukrytych rabatów
- Korekcja błędów OCR
- Produkty ważone
- Obsługa wielu pozycji

### 5. `test_type_conversion.py` - Testy konwersji typów
- Konwersja dat (ISO, polski format, z czasem)
- Konwersja cen na Decimal
- Obsługa przecinków jako separatorów
- Fallback dla nieprawidłowych dat

### 6. `test_integration.py` - Testy integracyjne
- Pełny pipeline Lidl (post-processing + weryfikacja)
- Pełny pipeline Biedronka
- Pipeline z korekcją matematyczną

### 7. `test_llm_mocked.py` - Testy LLM z mockami
- `get_llm_suggestion` z mockami Ollama
- `parse_receipt_with_llm` z mockami
- `parse_receipt_from_text` z mockami
- Obsługa błędów i wyjątków

### 8. `test_ocr_mocked.py` - Testy OCR z mockami
- `convert_pdf_to_image` z mockami pdf2image
- `extract_text_from_image` z mockami Tesseract
- Obsługa wielu stron PDF
- Obsługa błędów

### 9. `test_mistral_ocr_mocked.py` - Testy Mistral OCR z mockami
- Inicjalizacja klienta (z/bez klucza API)
- `process_image` z mockami Mistral API
- Obsługa wielu stron
- Obsługa błędów

### 10. `test_main_mocked.py` - Testy main.py z mockami bazy danych
- `save_to_database` z mockami SQLAlchemy
- `resolve_product` z mockami (aliasy, reguły statyczne, LLM)
- Tworzenie nowych produktów i kategorii

### 11. `test_bielik.py` - Testy asystenta AI Bielik

### 12. `tests/unit/test_batch_processing.py` - Testy batch processing LLM (2025-12-07)
- **TestBatchLLMProcessor**: 8 testów dla normalize_batch()
- **TestBatchProcessingPerformance**: 4 testy dla normalize_products_batch()
- Testy równoległego przetwarzania, obsługi błędów, log callback

### 13. `tests/unit/test_async_queue.py` - Testy async queue processing (2025-12-07)
- **TestAsyncReceiptProcessor**: 5 testów async processing
- **TestAsyncQueuePerformance**: 2 testy wydajności
- **TestAsyncQueueIntegration**: 2 testy integracyjne
- Testy równoległości, obsługi błędów, benchmarki

### 14. `tests/unit/test_database.py` - Testy bazy danych (2025-12-07)
- **TestDatabaseModels**: 7 testów CRUD operations
- **TestDatabaseIndices**: 3 testy indeksów
- **TestDatabaseBatchOperations**: 3 testy operacji batch
- Testy relacji, constraints, cascade delete

### 15. `tests/gui/test_main_window.py` - Testy GUI (2025-12-07)
- **TestMainWindow**: 5 testów głównego okna
- **TestTabs**: 2 testy zakładek
- **TestNotifications**: 4 testy powiadomień
- **TestGUIComponents**: 3 testy komponentów
- Testy mogą być pominięte jeśli CustomTkinter nie jest dostępny

### 16. `tests/e2e/test_receipt_workflow.py` - Testy E2E workflow (2025-12-07)
- **TestReceiptFullWorkflow**: 2 testy pełnego workflow
- **TestErrorRecovery**: 3 testy obsługi błędów
- **TestPerformanceBenchmarks**: 2 testy wydajności
- **TestIntegrationScenarios**: 2 testy scenariuszy integracyjnych
- **Wyszukiwanie produktów (RAG)**: Testy fuzzy matching, filtrowanie po podobieństwie
- **Dostępne produkty**: Pobieranie produktów z magazynu, grupowanie
- **Proponowanie potraw**: Generowanie sugestii na podstawie dostępnych produktów
- **Listy zakupów**: Generowanie list, filtrowanie produktów już w magazynie
- **Odpowiedzi na pytania**: Konwersacyjny asystent z kontekstem produktów
- **Funkcje pomocnicze**: Testy wrapperów `ask_bielik`, `get_dish_suggestions`, `get_shopping_list`
- **Context manager**: Testy zarządzania sesją bazy danych
- Wszystkie testy używają mocków dla Ollama i bazy danych

## Uruchamianie testów

### Wszystkie testy
```bash
cd /home/marcin/Projekty/ParagonOCR
source venv/bin/activate
pytest tests/ -v
```

### Nowe testy (Phase 2)
```bash
# Testy jednostkowe
pytest tests/unit/ -v

# Testy GUI
pytest tests/gui/ -v

# Testy E2E
pytest tests/e2e/ -v
```

### Z pokryciem kodu
```bash
pytest tests/ --cov=ReceiptParser/src --cov-report=term-missing --cov-report=html
```

### Konkretny plik testowy
```bash
pytest tests/test_strategies.py -v
```

### Konkretny test
```bash
pytest tests/test_strategies.py::TestLidlStrategy::test_post_process_scales_discounts -v
```

## Pokrycie kodu

### Wysokie pokrycie (80-100%)
- ✅ `normalization_rules.py`: 100%
- ✅ `knowledge_base.py`: 100%
- ✅ `data_models.py`: 100%
- ✅ `ocr.py`: 100% (z mockami)
- ✅ `mistral_ocr.py`: 90% (z mockami)
- ✅ `strategies.py`: 82%
- ✅ `database.py`: 86%
- ✅ `llm.py`: 77% (z mockami)
- ✅ `bielik.py`: 85% (z mockami)

### Średnie pokrycie (50-80%)
- ⚠️ `config.py`: 71%
- ⚠️ `main.py`: 55% (część wymaga pełnej integracji z bazą)

## Uwagi

1. **Testy wymagające zewnętrznych zależności**:
   - Testy LLM wymagają działającego serwera Ollama
   - Testy Mistral OCR wymagają klucza API
   - Testy OCR wymagają zainstalowanego Tesseract

2. **Testy jednostkowe vs integracyjne**:
   - Testy jednostkowe są szybkie i nie wymagają zewnętrznych zależności
   - Testy integracyjne mogą wymagać mocków lub działających serwisów

3. **Rozszerzanie testów**:
   - Dodaj nowe testy w odpowiednich plikach
   - Używaj `conftest.py` dla wspólnych fixtures
   - Mockuj zewnętrzne zależności (Ollama, Mistral API)

## Przykłady testów

### Test strategii
```python
def test_lidl_scales_discounts():
    strategy = LidlStrategy()
    data = {
        "pozycje": [
            {"nazwa_raw": "Produkt", "cena_calk": "10.00", ...},
            {"nazwa_raw": "Rabat", "cena_calk": "-2.00", ...}
        ]
    }
    result = strategy.post_process(data)
    assert len(result["pozycje"]) == 1
    assert result["pozycje"][0]["rabat"] == "2.00"
```

### Test normalizacji
```python
def test_mleko_normalization():
    assert find_static_match("Mleko UHT 3,2%") == "Mleko"
```

### Test asystenta Bielik
```python
@patch("src.bielik.client")
def test_suggest_dishes_success(mock_client):
    assistant = BielikAssistant(session=mock_session)
    assistant.get_available_products = Mock(return_value=[...])
    mock_client.chat.return_value = {"message": {"content": json.dumps({...})}}
    
    result = assistant.suggest_dishes("obiad")
    assert len(result) > 0
```

## Kontakt

W razie problemów z testami, sprawdź:
1. Czy wszystkie zależności są zainstalowane
2. Czy venv jest aktywowany
3. Czy ścieżki do modułów są poprawne

