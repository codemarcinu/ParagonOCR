# 🧾 ParagonOCR 2.0 - System Zarządzania Paragonami i Domowym Magazynem

**ParagonOCR 2.0** to zaawansowany system do cyfryzacji, analizy i zarządzania danymi z paragonów sklepowych z pełną integracją AI. Aplikacja wykorzystuje hybrydowe podejście do OCR (Tesseract + Mistral AI), lokalne modele językowe (LLM via Ollama), oraz zaawansowane funkcje AI do zarządzania domowym magazynem, planowania posiłków i redukcji marnowania żywności.

**Wersja:** 2.0-local-only  
**Data dokumentacji:** 2025-12-06  
**Status:** ✅ Wszystkie fazy implementacji zakończone (5/5)

> [!IMPORTANT]
> **Nowa Edycja Webowa (2025)**: Sprawdź [README_WEB.md](README_WEB.md) dla instrukcji dotyczących nowej wersji opartej na React/FastAPI/Docker z Landing Page i zaawansowaną analityką.

---

## 🚀 Główne Funkcjonalności

### 🔍 Hybrydowy OCR
- **Mistral OCR** (przez API) dla wysokiej precyzji odczytu trudnych paragonów
- **Tesseract OCR** jako fallback dla szybkiej analizy nagłówków i detekcji sklepu
- Obsługa plików PDF (automatyczna konwersja na obrazy) oraz obrazów (PNG, JPG)
- Automatyczna detekcja sklepu na podstawie wzorców regex

### 🤖 Inteligentne Parsowanie (LLM)
- Integracja z **Ollama** (model `SpeakLeash/Bielik` lub `LLaVA`) do interpretacji nieustrukturyzowanego tekstu
- Automatyczna korekta błędów OCR i normalizacja nazw produktów
- Wsparcie dla modeli multimodalnych (wizja + tekst) oraz tekstowych
- **5-stage normalization pipeline** z confidence scoring

### 💬 Lokalny Czat AI z RAG (Retrieval-Augmented Generation)
- **Inteligentny czat kulinarny** z kontekstem z bazy danych produktów
- **RAG Search Engine** - wyszukiwanie produktów z fuzzy matching, semantic search i temporal ranking
- **10 typów prompt templates** - product_info, recipe_suggestion, shopping_list, expiry_usage, nutrition_analysis, storage_advice, waste_reduction, meal_planning, budget_optimization, dietary_preferences
- **Streaming responses** - płynne wyświetlanie odpowiedzi w czasie rzeczywistym
- **Historia konwersacji** - zapisywanie i eksport rozmów
- **Request queuing** - maksymalnie 2 równoczesne zapytania

### 🏪 Strategie Sklepowe (Strategy Pattern)
- Dedykowane algorytmy dla sieci: **Lidl, Biedronka, Kaufland, Auchan**
- Inteligentne scalanie rabatów (np. "Lidl Plus", "Rabat" w osobnej linii)
- Obsługa specyficznych formatów (produkty ważone, wieloliniowe opisy)
- **Shop-specific variants** - mapowanie nazw specyficznych dla sklepów na znormalizowane nazwy

### ✅ Weryfikacja Matematyczna
- Automatyczne sprawdzanie spójności: `Ilość × Cena jedn. = Wartość`
- Wykrywanie i naprawa "ukrytych" rabatów oraz błędów odczytu
- Korekcja błędów OCR w cenach i ilościach

### 📦 Zaawansowane Zarządzanie Magazynem
- **Śledzenie dat ważności** z alertami o wygasających produktach
- **Food Waste Tracker** - analiza marnowania żywności
- **Quick Add** - szybkie dodawanie produktów
- **Meal Planner** - tygodniowy planer posiłków
- **Smart Shopping Lists** - inteligentne listy zakupów z optymalizacją budżetu
- **Nutrition Analyzer** - analiza wartości odżywczej posiłków
- **Recipe Engine** - sugestie przepisów na podstawie dostępnych produktów
- **Waste Reduction Engine** - porady dotyczące wykorzystania wygasających produktów

### 🖥️ Nowoczesny Interfejs Graficzny
- **Unified Design System** - spójny system kolorów, odstępów, czcionek i ikon
- **Notification System** - toast notifications i dialogi potwierdzenia
- **Card-based layouts** - nowoczesne sekcje z borderami
- **Virtual scrolling** - optymalizacja dla dużych tabel (>1000 wierszy)
- **Lazy loading dialogs** - tworzenie okien na żądanie
- **Smooth animations** - płynne przejścia i animacje
- **Memory optimization** - profilowanie i cleanup pamięci
- **Status bar** - wyświetlanie aktualnego statusu aplikacji

### 📊 Analityka Zakupów
- **Statystyki ogólne** - łączna liczba paragonów, wydatki, średnie wartości
- **Wydatki według sklepów** - ranking sklepów według wydatków
- **Wydatki według kategorii** - analiza wydatków na kategorie produktów
- **Najczęściej kupowane produkty** - ranking produktów z liczbą zakupów
- **Statystyki miesięczne** - trendy wydatków w czasie
- **Ostatnie paragony** - szybki podgląd ostatnio dodanych paragonów

### 🦅 Asystent AI Bielik
- **Czat kulinarny** - zadawaj pytania o produkty, gotowanie, przepisy
- **Propozycje potraw** - sugestie dań na podstawie dostępnych produktów w magazynie
- **Lista zakupów** - automatyczne generowanie listy brakujących produktów
- **Konfigurowalne prompty** - możliwość edycji promptów systemowych przez GUI

### 💾 Baza Danych
- Pełna struktura relacyjna w **SQLite** (SQLAlchemy ORM)
- **Zoptymalizowane zapytania** - composite indices, LRU cache (max 200 items)
- Obsługa aliasów produktów (mapowanie różnych nazw na jeden znormalizowany produkt)
- Kategoryzacja produktów z metadanymi (możliwość mrożenia, wartości odżywcze)
- Historia zakupów z pełnymi szczegółami paragonów
- **Chat storage** - przechowywanie historii konwersacji z AI
- **Database migrations** - automatyczne aktualizacje schematu

---

## 🛠️ Wymagania Systemowe

### Oprogramowanie
- **Python 3.9+** (testowane na Python 3.13)
- **Tesseract OCR** (zainstalowany w systemie i dodany do PATH)
- **Poppler** (do konwersji PDF na obrazy)
- **Ollama** (uruchomiona lokalnie) z pobranymi modelami:
  - `SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M` (zalecany do tekstu)
  - `llava:latest` (opcjonalnie do wizji)

### Instalacja zależności systemowych

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install tesseract-ocr poppler-utils
```

**macOS:**
```bash
brew install tesseract poppler
```

**Windows:**
- Pobierz i zainstaluj Tesseract z [GitHub Releases](https://github.com/UB-Mannheim/tesseract/wiki)
- Pobierz i zainstaluj Poppler z [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases)

---

## 📦 Instalacja

### 1. Sklonuj repozytorium

```bash
git clone https://github.com/codemarcinu/paragonocr.git
cd paragonocr
```

### 2. Utwórz środowisko wirtualne i zainstaluj zależności

Możesz skorzystać z gotowego skryptu startowego, który zrobi to za Ciebie:

```bash
chmod +x uruchom.sh
./uruchom.sh
```

Lub ręcznie:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r ReceiptParser/requirements.txt
```

### 3. Konfiguracja `.env`

Utwórz plik `.env` w głównym katalogu projektu:

```ini
# Konfiguracja API (dla Mistral OCR)
MISTRAL_API_KEY=twoj_klucz_api_tutaj

# Konfiguracja Ollama
OLLAMA_HOST=http://localhost:11434
VISION_MODEL=llava:latest
TEXT_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
# Timeout dla zapytań do Ollama (w sekundach, domyślnie 300 = 5 minut)
OLLAMA_TIMEOUT=300

# Opcjonalne: Logowanie do pliku (domyślnie wyłączone)
# Logi zapisywane są w katalogu logs/ jako paragonocr_YYYYMMDD.log
ENABLE_FILE_LOGGING=false
```

**Uwaga:** Klucz API Mistral jest opcjonalny - aplikacja działa również bez niego (używa Tesseract OCR).

### 4. Inicjalizacja bazy danych

Przy pierwszym uruchomieniu, zainicjalizuj bazę danych:

```bash
# Przez GUI: kliknij przycisk "⚙️ Inicjalizuj bazę danych"
# Lub przez CLI:
python -m ReceiptParser.src.main init-db
```

---

## 🖥️ Uruchomienie

### Interfejs Graficzny (Zalecane)

Najprostszy sposób na uruchomienie aplikacji to skorzystanie ze skryptu pomocniczego, który ustawia `PYTHONPATH` i aktywuje środowisko:

```bash
./uruchom.sh
```

Alternatywnie ręcznie:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/ReceiptParser"
source venv/bin/activate
python gui.py
```

### Tryb CLI (Linia komend)

Aplikacja posiada również interfejs CLI do przetwarzania wsadowego lub debugowania:

```bash
# Inicjalizacja bazy danych
python -m ReceiptParser.src.main init-db

# Przetworzenie pojedynczego pliku
python -m ReceiptParser.src.main process --file sciezka/do/paragonu.jpg --llm mistral-ocr
# lub
python -m ReceiptParser.src.main process --file sciezka/do/paragonu.pdf --llm llava:latest
```

**Opcje modeli LLM:**
- `mistral-ocr` - używa Mistral OCR API + model tekstowy (Bielik)
- `llava:latest` - używa modelu multimodalnego (wizja + tekst)
- `SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M` - używa modelu tekstowego z Tesseract OCR

---

## 🗂️ Struktura Projektu

```
ParagonOCR/
├── gui.py                          # Główny plik interfejsu graficznego
├── history_manager.py              # Moduł zarządzania historią plików
├── uruchom.sh                      # Skrypt startowy (Linux/Mac)
├── .env                            # Konfiguracja (klucze API, modele)
├── .gitignore                      # Pliki ignorowane przez Git
├── paragony/                       # Katalog na pliki wejściowe (PDF/IMG)
├── logs/                           # Katalog na logi (tworzony automatycznie)
│   └── paragonocr_YYYYMMDD.log     # Pliki logów (jeśli ENABLE_FILE_LOGGING=true)
├── scripts/                        # Skrypty pomocnicze i narzędzia deweloperskie
│   ├── check_database.py           # Sprawdzanie zawartości bazy danych
│   ├── debug_ocr.py               # Debugowanie OCR
│   ├── verify_config.py           # Weryfikacja konfiguracji
│   ├── verify_knowledge.py        # Weryfikacja bazy wiedzy
│   ├── test_bielik.py             # Test demonstracyjny asystenta Bielik
│   ├── test_mistral.py            # Test integracji Mistral OCR
│   ├── test_receipt.py            # Test pełnego pipeline przetwarzania
│   └── generate_expanded_products.py  # Generator rozszerzonej bazy produktów
├── ANALIZA_BEZPIECZEŃSTWA.md      # Analiza bezpieczeństwa aplikacji
├── ANALIZA_KODU.md                # Analiza struktury i jakości kodu
├── ANALIZA_SUGESTII_UX.md        # Analiza sugestii UX
├── ANALIZA_GUI_ULEPSZENIA.md      # Analiza GUI i propozycje ulepszeń
├── IMPLEMENTATION_PROGRESS.md     # Postęp implementacji ParagonOCR 2.0
├── paragonocr_2.0_implementation.json  # Szczegółowy plan implementacji
├── ReceiptParser/
│   ├── data/                      # Dane i baza danych SQLite
│   │   ├── receipts.db            # Baza danych SQLite
│   │   ├── bielik_prompts.json    # Prompty dla asystenta Bielik
│   │   ├── expanded_products.json # Rozszerzona baza produktów (181+ produktów)
│   │   ├── static_rules.json      # Reguły normalizacji (908 wzorców)
│   │   ├── shop_variants.json     # Mapowania nazw specyficznych dla sklepów
│   │   └── product_metadata.json  # Metadane produktów (indeksy, kategorie, tagi)
│   ├── requirements.txt           # Zależności Python
│   └── src/
│       ├── main.py                 # Logika orkiestracji pipeline'u
│       ├── database.py             # Modele SQLAlchemy i migracje
│       ├── strategies.py            # Logika specyficzna dla sklepów
│       ├── llm.py                   # Komunikacja z Ollama (streaming, queuing)
│       ├── llm_cache.py             # Cache odpowiedzi LLM (LRU, max 100)
│       ├── ocr.py                   # Wrapper na Tesseract i PDF2Image
│       ├── mistral_ocr.py           # Klient Mistral API
│       ├── knowledge_base.py        # Metadane produktów (kategorie, mrożenie)
│       ├── normalization_rules.py    # 5-stage normalization pipeline
│       ├── data_models.py            # TypedDict definicje struktur danych
│       ├── config.py                 # Konfiguracja z .env i stałe
│       ├── config_prompts.py        # Zarządzanie promptami dla Bielik
│       ├── logger.py                # Moduł logowania (opcjonalne logowanie do pliku)
│       ├── security.py               # Moduł bezpieczeństwa (walidacja, sanityzacja)
│       ├── bielik.py                # Asystent AI Bielik (gotowanie, lista zakupów)
│       ├── purchase_analytics.py     # Analiza zakupów
│       ├── migrate_db.py             # Migracje bazy danych
│       ├── food_waste_tracker.py     # Śledzenie marnowania żywności
│       ├── quick_add.py              # Szybkie dodawanie produktów
│       ├── meal_planner.py           # Tygodniowy planer posiłków
│       ├── unified_design_system.py  # System design (kolory, odstępy, czcionki, ikony)
│       ├── notifications.py           # System powiadomień (toast, dialogi)
│       ├── ai_chat_tab.py            # Komponent czatu AI
│       ├── rag_engine.py              # RAG Search Engine (fuzzy, semantic, temporal)
│       ├── prompt_templates.py       # 10 typów prompt templates
│       ├── chat_storage.py           # Przechowywanie historii konwersacji
│       ├── recipe_engine.py          # Silnik sugestii przepisów
│       ├── waste_reduction_engine.py  # Silnik redukcji marnowania żywności
│       ├── smart_shopping.py          # Inteligentne listy zakupów
│       ├── nutrition_analyzer.py      # Analiza wartości odżywczej
│       ├── db_cache.py                # Cache bazy danych (LRU, max 200)
│       ├── gui_optimizations.py      # Optymalizacje GUI (virtual scrolling, memory profiling)
│       ├── export_import.py          # Eksport/import danych
│       └── retry_handler.py          # Obsługa retry dla API
└── tests/                            # Testy jednostkowe i integracyjne
    ├── README.md                     # Dokumentacja testów
    ├── conftest.py                   # Wspólne fixtures pytest
    ├── test_*.py                      # Pliki testowe
    └── evaluation/                    # Testy ewaluacyjne
        ├── evaluate_accuracy.py
        └── ground_truth.json
```

---

## 🧪 Testowanie

Projekt posiada rozbudowany zestaw testów (pytest) z pokryciem kodu ~73%.

### Uruchamianie testów

```bash
# Wszystkie testy
pytest tests/ -v

# Z pokryciem kodu
pytest tests/ --cov=ReceiptParser/src --cov-report=term-missing --cov-report=html

# Konkretny plik testowy
pytest tests/test_strategies.py -v

# Konkretny test
pytest tests/test_strategies.py::TestLidlStrategy::test_post_process_scales_discounts -v
```

### Statystyki testów

- **Łączna liczba testów**: 89+
- **Status**: ✅ Wszystkie testy przechodzą
- **Pokrycie kodu**: 73% (główne moduły: 70-100%)

Testy pokrywają:
- Strategie parsowania (Lidl, Biedronka, Auchan, Kaufland)
- Normalizację produktów (5-stage pipeline)
- Weryfikację matematyczną
- Integrację z bazą danych (na mockach)
- Komunikację z LLM (na mockach)
- OCR (na mockach)
- RAG Engine
- Chat Storage

Więcej informacji o testach znajdziesz w `tests/README.md`.

---

## 📊 Schemat Bazy Danych

### Tabele

- **`sklepy`**: Przechowuje nazwy i lokalizacje sklepów
- **`paragony`**: Nagłówki paragonów (data, suma, relacja do sklepu, plik źródłowy)
- **`produkty`**: Znormalizowane nazwy produktów i ich kategorie
- **`kategorie_produktow`**: Kategorie produktów (np. "Nabiał", "Pieczywo")
- **`aliasy_produktow`**: Mapuje "dziwne" nazwy z paragonów na produkty znormalizowane
- **`pozycje_paragonu`**: Konkretne linie z paragonu (cena, ilość, rabaty, relacja do produktu)
- **`stan_magazynowy`**: Aktualny stan posiadania, daty ważności, jednostki miary
- **`conversations`**: Historia konwersacji z AI (tytuł, data utworzenia, model)
- **`chat_messages`**: Wiadomości w konwersacjach (role, content, timestamp, tokens, RAG context)

### Relacje

```
Sklep 1:N Paragon
Paragon 1:N PozycjaParagonu
Produkt 1:N PozycjaParagonu
Produkt 1:N AliasProduktu
Produkt 1:N StanMagazynowy
KategoriaProduktu 1:N Produkt
Conversation 1:N ChatMessage
```

### Indeksy i Optymalizacje

- **Composite indices** na częstych zapytaniach:
  - `pozycje_paragonu`: (paragon_id, produkt_id)
  - `stan_magazynowy`: (produkt_id, data_waznosci, ilosc, priorytet)
  - `paragony`: (sklep_id, data_zakupu)
  - `chat_messages`: (conversation_id, timestamp)
- **LRU Cache** dla zapytań do bazy (max 200 items)
- **LRU Cache** dla odpowiedzi LLM (max 100 responses)

---

## 🔧 Funkcjonalności Szczegółowe

### Strategie Parsowania

Każdy sklep ma dedykowaną strategię parsowania, która:
- Definiuje specyficzny prompt systemowy dla LLM
- Wykonuje post-processing danych (np. scalanie rabatów)
- Obsługuje specyficzne formaty paragonów

**Obsługiwane sklepy:**
- Lidl (scalanie rabatów Lidl Plus)
- Biedronka (obsługa rabatów i produktów ważonych)
- Kaufland
- Auchan (usuwanie śmieci OCR)
- Carrefour, Żabka, Dino, Netto, Stokrotka, Rossmann, Hebe, Orlen, Shell, McDonald's (podstawowa obsługa)

### 5-Stage Normalization Pipeline

System automatycznie normalizuje nazwy produktów poprzez:

1. **Cleanup OCR (100%)** - usuwanie kodów podatkowych, ilości, promocji, normalizacja whitespace
2. **Static Rules (80%)** - regex patterns z `static_rules.json` (908 wzorców)
3. **Alias Lookup (15%)** - fuzzy matching z `rapidfuzz` na aliasach produktów
4. **LLM-based (4%)** - zapytanie do Ollama z promptem normalizacji
5. **User Confirmation (1%)** - interaktywny prompt dla niskiej pewności

Zwraca `(normalized_name, confidence_score)` z poziomami:
- `0.95+`: certain
- `0.80-0.95`: high
- `0.60-0.80`: medium
- `0.40-0.60`: low
- `<0.40`: needs_confirmation

### Rozszerzona Baza Produktów

- **181+ produktów** w `expanded_products.json` (gotowe do rozszerzenia do 500+)
- **10 kategorii**: Piekarnicze, Nabiał, Owoce, Warzywa, Mięso, Snacki, Napoje, Mrożone, Słoiki/Puszki, Przyprawy
- **Pełne metadane**: wartości odżywcze, właściwości (mrożenie, alergeny), ceny, częstotliwość zakupów
- **Shop-specific variants**: 720 mapowań dla LIDL, BIEDRONKA, KAUFLAND, AUCHAN
- **Product metadata**: szybkie wyszukiwanie po kategoriach i tagach

### RAG Search Engine

Inteligentne wyszukiwanie produktów z kontekstem:

- **Fuzzy matching** (weight: 0.4) - `rapidfuzz.fuzz.partial_ratio()`
- **Semantic search** (weight: 0.3) - wyszukiwanie w kategoriach, tagach, aliasach
- **Temporal ranking** (weight: 0.3) - priorytetyzacja wygasających produktów i często używanych
- **Format context** - formatowanie kontekstu dla różnych typów zapytań (product_info, recipe_suggestion, shopping_list, expiry_usage)

### Prompt Templates

10 gotowych szablonów promptów dla różnych scenariuszy:

1. **product_info** - informacje o produktach
2. **recipe_suggestion** - sugestie przepisów
3. **shopping_list** - generowanie list zakupów
4. **expiry_usage** - wykorzystanie wygasających produktów
5. **nutrition_analysis** - analiza wartości odżywczej
6. **storage_advice** - porady dotyczące przechowywania
7. **waste_reduction** - redukcja marnowania żywności
8. **meal_planning** - planowanie posiłków
9. **budget_optimization** - optymalizacja budżetu
10. **dietary_preferences** - preferencje dietetyczne i alergie

### Advanced Features

#### Recipe Engine
- Sugestie przepisów na podstawie dostępnych produktów
- Priorityzacja wygasających produktów
- Wsparcie dla preferencji dietetycznych i alergii
- Obliczanie kosztu przepisu z metadanych produktów

#### Waste Reduction Engine
- Alerty o wygasających produktach z sugestiami przepisów
- Porady dotyczące mrożenia (AI-powered)
- Statystyki marnowania żywności z analizą AI

#### Smart Shopping
- Generowanie list zakupów na podstawie planowanych posiłków
- Grupowanie według sekcji sklepu
- Sugestie alternatywnych produktów
- Optymalizacja budżetu

#### Nutrition Analyzer
- Analiza wartości odżywczej posiłków
- Śledzenie dziennego spożycia
- Identyfikacja niedoborów
- Sugestie zbilansowanych posiłków

---

## ⚡ Optymalizacje i Ulepszenia

### ParagonOCR 2.0 - Wprowadzone Optymalizacje (2025-12-06)

**Wydajność:**
- ✅ **Database optimization** - composite indices, LRU cache (max 200 items)
- ✅ **LLM response optimization** - cache odpowiedzi (max 100), request queuing (max 2 concurrent)
- ✅ **GUI performance** - virtual scrolling dla dużych tabel (>1000 wierszy), lazy loading dialogs
- ✅ **Memory optimization** - profilowanie pamięci (tracemalloc), cleanup widgetów, garbage collection

**Funkcjonalności:**
- ✅ **Unified Design System** - spójny system kolorów, odstępów, czcionek i ikon
- ✅ **Notification System** - toast notifications i dialogi potwierdzenia
- ✅ **AI Chat with RAG** - inteligentny czat z kontekstem z bazy danych
- ✅ **5-stage Normalization Pipeline** - zaawansowana normalizacja z confidence scoring
- ✅ **Expanded Product Dictionary** - 181+ produktów z pełnymi metadanymi
- ✅ **Advanced Features** - Recipe Engine, Waste Reduction, Smart Shopping, Nutrition Analyzer

**Stabilność:**
- ✅ **Timeout dla Ollama** - konfigurowalny timeout zapobiega zawieszeniu aplikacji
- ✅ **Truncation tekstu** - automatyczne obcinanie zbyt długich tekstów dla LLM
- ✅ **Walidacja danych** - sprawdzanie poprawności przed zapisem do bazy
- ✅ **Ochrona przed memory leak** - limit iteracji w przetwarzaniu kolejki logów

**Jakość kodu:**
- ✅ **Walidacja nazw produktów** - sprawdzanie długości i czyszczenie
- ✅ **Obsługa ujemnych rabatów** - poprawne wykrywanie i korekta błędnych wartości
- ✅ **Type safety** - użycie `TypedDict` zamiast `Dict` w sygnaturach metod
- ✅ **Comprehensive docstrings** - Google style docstrings we wszystkich modułach

**Bezpieczeństwo:**
- ✅ **Walidacja ścieżek plików** - ochrona przed path traversal attacks
- ✅ **Bezpieczne pliki tymczasowe** - odpowiednie uprawnienia (chmod 600) i cleanup
- ✅ **Walidacja rozmiaru plików** - ochrona przed DoS (max 100MB dla plików, 50MB dla obrazów)
- ✅ **Walidacja wymiarów obrazów** - maksymalne wymiary 10000x10000px
- ✅ **Sanityzacja logów** - usuwanie wrażliwych danych (pełne ścieżki, długie teksty OCR)
- ✅ **Walidacja modeli LLM** - tylko dozwolone modele mogą być używane

---

## 🐛 Rozwiązywanie Problemów

### Problem: "Nie udało się skonwertować pliku PDF"
**Rozwiązanie:** Upewnij się, że Poppler jest zainstalowany i dostępny w PATH.

### Problem: "BŁĄD: Klient Ollama nie jest skonfigurowany"
**Rozwiązanie:** 
1. Upewnij się, że Ollama jest uruchomiona: `systemctl --user status ollama` (Linux) lub `ollama serve` (ręcznie)
2. Sprawdź, czy model jest pobrany: `ollama list`
3. Pobierz model: `ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M`

### Problem: "Timeout podczas komunikacji z Ollama"
**Rozwiązanie:** 
- Zwiększ wartość `OLLAMA_TIMEOUT` w pliku `.env` (domyślnie 300 sekund)
- Sprawdź, czy Ollama działa poprawnie: `curl http://localhost:11434/api/tags`

### Problem: "Mistral OCR nie zwrócił wyniku"
**Rozwiązanie:** 
- Sprawdź, czy klucz API jest poprawny w pliku `.env`
- Jeśli nie masz klucza API, użyj trybu bez Mistral OCR (aplikacja automatycznie użyje Tesseract)

### Problem: Błędy importów w GUI
**Rozwiązanie:** Upewnij się, że używasz skryptu `uruchom.sh` lub ręcznie ustawiasz `PYTHONPATH`:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/ReceiptParser"
```

### Problem: Jak włączyć logowanie do pliku?
**Rozwiązanie:** Dodaj do pliku `.env`:
```ini
ENABLE_FILE_LOGGING=true
```
Logi będą zapisywane w katalogu `logs/` jako `paragonocr_YYYYMMDD.log`. Katalog zostanie utworzony automatycznie przy pierwszym uruchomieniu z włączonym logowaniem.

### Problem: "BŁĄD WALIDACJI: Model 'xyz' nie jest dozwolony"
**Rozwiązanie:** Aplikacja waliduje modele LLM dla bezpieczeństwa. Dozwolone modele to:
- `llava:latest`
- `SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M`
- `mistral-ocr`

Jeśli chcesz użyć innego modelu, dodaj go do listy `ALLOWED_LLM_MODELS` w `ReceiptParser/src/security.py`.

### Problem: "Plik jest za duży" lub "Obraz za duży"
**Rozwiązanie:** Aplikacja ma limity bezpieczeństwa:
- Maksymalny rozmiar pliku: 100 MB
- Maksymalny rozmiar obrazu: 50 MB
- Maksymalne wymiary obrazu: 10000x10000px

Te limity chronią przed atakami DoS. Jeśli potrzebujesz przetwarzać większe pliki, możesz zmienić stałe w `ReceiptParser/src/security.py`.

### Problem: Wolne działanie przy dużych tabelach (>1000 wierszy)
**Rozwiązanie:** Aplikacja automatycznie używa virtual scrolling dla tabel z >1000 wierszami. Jeśli nadal jest wolno, sprawdź:
- Czy masz wystarczająco pamięci RAM
- Czy baza danych ma odpowiednie indeksy (sprawdź `IMPLEMENTATION_PROGRESS.md`)

---

## 🔒 Bezpieczeństwo

Aplikacja implementuje szereg mechanizmów bezpieczeństwa:

### Ochrona przed Path Traversal
- Wszystkie ścieżki plików są walidowane i normalizowane przed użyciem
- Sprawdzanie rozszerzeń plików i rozmiarów
- Ochrona przed dostępem do plików poza katalogiem projektu

### Bezpieczne Pliki Tymczasowe
- Pliki tymczasowe tworzone z odpowiednimi uprawnieniami (tylko właściciel)
- Automatyczny cleanup nawet przy błędach
- Ochrona przed race conditions

### Sanityzacja Danych
- Logi nie zawierają pełnych ścieżek (tylko nazwy plików)
- Długie teksty OCR są obcinane w logach
- Błędy są sanityzowane przed wyświetleniem

### Walidacja Wejściowa
- Walidacja modeli LLM (tylko dozwolone)
- Walidacja rozmiaru i wymiarów plików
- Ochrona przed DoS przez zbyt duże pliki

Więcej informacji o bezpieczeństwie znajdziesz w `ANALIZA_BEZPIECZEŃSTWA.md`.

---

## 📚 Dokumentacja Dodatkowa

Projekt zawiera szczegółowe dokumenty analityczne:

- **ANALIZA_BEZPIECZEŃSTWA.md** - analiza mechanizmów bezpieczeństwa, potencjalne zagrożenia i rekomendacje
- **ANALIZA_KODU.md** - analiza struktury kodu, flow przetwarzania, code smells i obszary do poprawy
- **ANALIZA_SUGESTII_UX.md** - analiza sugestii UX, możliwości implementacji i priorytetyzacja
- **ANALIZA_GUI_ULEPSZENIA.md** - szczegółowa analiza GUI z propozycjami wizualnych i UX ulepszeń
- **IMPLEMENTATION_PROGRESS.md** - szczegółowy postęp implementacji ParagonOCR 2.0
- **paragonocr_2.0_implementation.json** - kompletny plan implementacji z wszystkimi fazami

---

## 🛠️ Narzędzia Deweloperskie

W katalogu `scripts/` znajdują się pomocne narzędzia:

- **check_database.py** - sprawdza zawartość bazy danych (sklepy, paragony, produkty)
- **debug_ocr.py** - testuje ekstrakcję tekstu z obrazów/PDF
- **verify_config.py** - weryfikuje poprawność konfiguracji i importów
- **verify_knowledge.py** - testuje bazę wiedzy (normalizacja sklepów, metadane produktów)
- **test_bielik.py** - demonstracja funkcjonalności asystenta Bielik
- **test_mistral.py** - test integracji z Mistral OCR API
- **test_receipt.py** - test pełnego pipeline przetwarzania paragonu
- **generate_expanded_products.py** - generator rozszerzonej bazy produktów

Uruchomienie przykład:
```bash
python scripts/check_database.py
python scripts/test_bielik.py
```

---

## 📝 Licencja

Projekt stworzony w celach edukacyjnych i do użytku domowego.

---

## 🤝 Autor

**Marcin** (CodeMarcinu)

---

## 🎨 Design System

Aplikacja wykorzystuje spójny design system z ujednoliconymi:

- **Kolory** (`AppColors`) - spójna paleta kolorów dla wszystkich elementów UI
- **Odstępy** (`AppSpacing`) - ujednolicone wartości padding i margin
- **Czcionki** (`AppFont`) - spójna typografia z różnymi rozmiarami i wagami
- **Ikony** (`Icons`) - spójny zestaw ikon emoji dla wszystkich akcji
- **Hover effects** - dynamiczne przyciemnianie przycisków przy najechaniu
- **Tooltips** - pomoc kontekstowa dla wszystkich interaktywnych elementów
- **Alternatywne kolory wierszy** - lepsza czytelność tabel
- **Card-based layouts** - nowoczesne sekcje z borderami
- **Notification System** - toast notifications i dialogi potwierdzenia

Więcej informacji o ulepszeniach GUI znajdziesz w `ANALIZA_GUI_ULEPSZENIA.md`.

---

## 🚀 ParagonOCR 2.0 - Status Implementacji

**Data rozpoczęcia:** 2025-12-06  
**Status:** ✅ Wszystkie fazy zakończone (5/5)

### Zakończone Fazy:

1. ✅ **Phase 1: UI/UX Overhaul** (100%)
   - Unified Design System
   - GUI Refactoring
   - Notification System
   - Enhanced Tab Layouts

2. ✅ **Phase 2: Local AI Chat with RAG** (100%)
   - Chat UI Tab
   - RAG Search Engine
   - Enhanced LLM Integration (streaming, queuing)
   - Smart Prompt Templates
   - Chat Storage and History

3. ✅ **Phase 3: Product Dictionary Enhancement** (100%)
   - Expand Product Catalog (181+ produktów)
   - Multi-Stage Normalization Pipeline
   - Static Rules Library (908 wzorców)
   - Shop-Specific Variants (720 mapowań)
   - Product Metadata

4. ✅ **Phase 4: Advanced Features** (100%)
   - Smart Recipe Engine
   - Food Waste Reduction AI
   - Smart Shopping Lists
   - Nutritional Analysis

5. ✅ **Phase 5: Performance & Polish** (100%)
   - Database Optimization (indices, caching)
   - LLM Response Optimization (caching, queuing)
   - GUI Performance Optimization (virtual scrolling, lazy loading, memory profiling)

**Statystyki:**
- Zakończone pliki: 21/21 (100%)
- Zakończone fazy: 5/5 (100%)
- Linie kodu dodane: ~23000+

Więcej szczegółów w `IMPLEMENTATION_PROGRESS.md`.

---

## 🙏 Podziękowania

- **Ollama** - za lokalne modele LLM
- **Mistral AI** - za API OCR
- **Tesseract OCR** - za darmowy OCR
- **CustomTkinter** - za nowoczesny interfejs GUI
- **SpeakLeash** - za model Bielik

---

*Jeśli masz pytania lub sugestie, utwórz issue w repozytorium.*

**Ostatnia aktualizacja:** 2025-12-06
