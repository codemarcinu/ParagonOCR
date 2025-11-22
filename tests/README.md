# Testy ParagonOCR

## Przegląd

Projekt zawiera kompleksowe testy jednostkowe i integracyjne dla systemu parsowania paragonów.

## Statystyki testów

- **Łączna liczba testów**: 89
- **Status**: ✅ Wszystkie testy przechodzą
- **Pokrycie kodu**: 73% (główne moduły: 70-100%)

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

## Uruchamianie testów

### Wszystkie testy
```bash
cd /home/marcin/Projekty/ParagonOCR
source venv/bin/activate
pytest tests/ -v
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

## Kontakt

W razie problemów z testami, sprawdź:
1. Czy wszystkie zależności są zainstalowane
2. Czy venv jest aktywowany
3. Czy ścieżki do modułów są poprawne

