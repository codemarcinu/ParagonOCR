# 🧾 ParagonOCR (ReceiptParser)

**ParagonOCR** to zaawansowany system do cyfryzacji, analizy i zarządzania danymi z paragonów sklepowych. Aplikacja wykorzystuje hybrydowe podejście do OCR (Tesseract + Mistral AI) oraz lokalne modele językowe (LLM via Ollama), aby precyzyjnie ekstrahować dane o zakupach, kategoryzować produkty i zarządzać domowym magazynem.

## 🚀 Główne Funkcjonalności

### 🔍 Hybrydowy OCR
- **Mistral OCR** (przez API) dla wysokiej precyzji odczytu trudnych paragonów
- **Tesseract OCR** jako fallback dla szybkiej analizy nagłówków i detekcji sklepu
- Obsługa plików PDF (automatyczna konwersja na obrazy) oraz obrazów (PNG, JPG)

### 🤖 Inteligentne Parsowanie (LLM)
- Integracja z **Ollama** (model `SpeakLeash/Bielik` lub `LLaVA`) do interpretacji nieustrukturyzowanego tekstu
- Automatyczna korekta błędów OCR i normalizacja nazw produktów
- Wsparcie dla modeli multimodalnych (wizja + tekst) oraz tekstowych

### 🏪 Strategie Sklepowe (Strategy Pattern)
- Dedykowane algorytmy dla sieci: **Lidl, Biedronka, Kaufland, Auchan**
- Inteligentne scalanie rabatów (np. "Lidl Plus", "Rabat" w osobnej linii)
- Obsługa specyficznych formatów (produkty ważone, wieloliniowe opisy)
- Automatyczna detekcja sklepu na podstawie wzorców regex

### ✅ Weryfikacja Matematyczna
- Automatyczne sprawdzanie spójności: `Ilość × Cena jedn. = Wartość`
- Wykrywanie i naprawa "ukrytych" rabatów oraz błędów odczytu
- Korekcja błędów OCR w cenach i ilościach

### 📦 Zarządzanie Magazynem i GUI
- Nowoczesny interfejs graficzny oparty na **CustomTkinter**
- Moduł **"Gotowanie"** do łatwego zużywania produktów z bazy
- Śledzenie dat ważności i stanów magazynowych
- Ręczne dodawanie produktów do magazynu
- Przeglądanie stanu magazynu z oznaczeniem produktów przeterminowanych

### 💾 Baza Danych
- Pełna struktura relacyjna w **SQLite** (SQLAlchemy ORM)
- Obsługa aliasów produktów (mapowanie różnych nazw na jeden znormalizowany produkt)
- Kategoryzacja produktów z metadanymi (możliwość mrożenia)
- Historia zakupów z pełnymi szczegółami paragonów
- **Zoptymalizowane zapytania** - batch loading aliasów, indeksy na kluczowych kolumnach

## 🛠️ Wymagania Systemowe

### Oprogramowanie
- **Python 3.13+**
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

## 🗂️ Struktura Projektu

```
ParagonOCR/
├── gui.py                  # Główny plik interfejsu graficznego
├── history_manager.py      # Moduł zarządzania historią plików
├── uruchom.sh              # Skrypt startowy (Linux/Mac)
├── .env                    # Konfiguracja (klucze API, modele)
├── paragony/               # Katalog na pliki wejściowe (PDF/IMG)
├── logs/                   # Katalog na logi (tworzony automatycznie przy włączeniu logowania)
│   └── paragonocr_YYYYMMDD.log  # Pliki logów (jeśli ENABLE_FILE_LOGGING=true)
├── scripts/                # Skrypty pomocnicze i narzędzia deweloperskie
│   ├── check_database.py   # Sprawdzanie zawartości bazy danych
│   ├── debug_ocr.py         # Debugowanie OCR
│   ├── verify_config.py     # Weryfikacja konfiguracji
│   ├── verify_knowledge.py  # Weryfikacja bazy wiedzy
│   ├── test_bielik.py       # Test demonstracyjny asystenta Bielik
│   ├── test_mistral.py      # Test integracji Mistral OCR
│   └── test_receipt.py      # Test pełnego pipeline przetwarzania
├── ReceiptParser/
│   ├── data/               # Baza danych SQLite (receipts.db)
│   │   ├── receipts/       # Opcjonalny katalog na pliki paragonów
│   │   └── bielik_prompts.json  # Prompty dla asystenta Bielik
│   ├── requirements.txt    # Zależności Python
│   └── src/
│       ├── main.py         # Logika orkiestracji pipeline'u
│       ├── database.py     # Modele SQLAlchemy
│       ├── strategies.py   # Logika specyficzna dla sklepów (Lidl, Biedronka...)
│       ├── llm.py          # Komunikacja z Ollama
│       ├── ocr.py          # Wrapper na Tesseract i PDF2Image
│       ├── mistral_ocr.py  # Klient Mistral API
│       ├── knowledge_base.py # Metadane produktów (kategorie, mrożenie)
│       ├── normalization_rules.py # Regexy do normalizacji nazw
│       ├── data_models.py  # TypedDict definicje struktur danych
│       ├── config.py       # Konfiguracja z .env i stałe
│       ├── config_prompts.py # Zarządzanie promptami dla Bielik
│       ├── logger.py       # Moduł logowania (opcjonalne logowanie do pliku)
│       ├── security.py     # Moduł bezpieczeństwa (walidacja, sanityzacja)
│       ├── bielik.py       # Asystent AI Bielik (gotowanie, lista zakupów)
│       ├── purchase_analytics.py # Analiza zakupów
│       └── migrate_db.py    # Migracje bazy danych
└── tests/                  # Testy jednostkowe i integracyjne
    ├── README.md           # Dokumentacja testów
    ├── conftest.py         # Wspólne fixtures pytest
    ├── test_*.py           # Pliki testowe
    └── evaluation/         # Testy ewaluacyjne
        ├── evaluate_accuracy.py
        └── ground_truth.json
```

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

- **Łączna liczba testów**: 89
- **Status**: ✅ Wszystkie testy przechodzą
- **Pokrycie kodu**: 73% (główne moduły: 70-100%)

Testy pokrywają:
- Strategie parsowania (Lidl, Biedronka, Auchan, Kaufland)
- Normalizację produktów
- Weryfikację matematyczną
- Integrację z bazą danych (na mockach)
- Komunikację z LLM (na mockach)
- OCR (na mockach)

Więcej informacji o testach znajdziesz w `tests/README.md`.

## 📊 Schemat Bazy Danych

### Tabele

- **`sklepy`**: Przechowuje nazwy i lokalizacje sklepów
- **`paragony`**: Nagłówki paragonów (data, suma, relacja do sklepu, plik źródłowy)
- **`produkty`**: Znormalizowane nazwy produktów i ich kategorie
- **`kategorie_produktow`**: Kategorie produktów (np. "Nabiał", "Pieczywo")
- **`aliasy_produktow`**: Mapuje "dziwne" nazwy z paragonów (np. "Mleko 3.2% Łaciat") na produkty znormalizowane (np. "Mleko")
- **`pozycje_paragonu`**: Konkretne linie z paragonu (cena, ilość, rabaty, relacja do produktu)
- **`stan_magazynowy`**: Aktualny stan posiadania, daty ważności, jednostki miary

### Relacje

```
Sklep 1:N Paragon
Paragon 1:N PozycjaParagonu
Produkt 1:N PozycjaParagonu
Produkt 1:N AliasProduktu
Produkt 1:N StanMagazynowy
KategoriaProduktu 1:N Produkt
```

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

### Normalizacja Produktów

System automatycznie normalizuje nazwy produktów poprzez:
1. **Sprawdzenie aliasów w bazie danych** (najszybsze)
2. **Reguły statyczne** (regex patterns) - oszczędność zapytań do LLM
3. **Zapytanie do LLM** (ostatnia deska ratunku)
4. **Weryfikacja użytkownika** (interaktywny prompt)

### Baza Wiedzy

System zawiera wbudowaną bazę wiedzy o produktach:
- **Kategorie**: Pieczywo, Nabiał, Mięso, Warzywa, Owoce, itd.
- **Metadane**: Informacja czy produkt można mrozić
- **Normalizacja sklepów**: Automatyczne rozpoznawanie sklepów po wzorcach

## ⚡ Optymalizacje i Ulepszenia

### Wprowadzone Optymalizacje (2025-11-22)

**Wydajność:**
- ✅ **Batch loading aliasów** - eliminacja problemu N+1 w zapytaniach do bazy danych
- ✅ **Indeksy bazy danych** - przyspieszenie zapytań na `nazwa_z_paragonu` i `znormalizowana_nazwa`
- ✅ **Timeout dla Ollama** - konfigurowalny timeout zapobiega zawieszeniu aplikacji
- ✅ **Truncation tekstu** - automatyczne obcinanie zbyt długich tekstów dla LLM

**Stabilność:**
- ✅ **Naprawione race conditions** - timeouty w komunikacji między wątkami GUI
- ✅ **Cleanup plików tymczasowych** - gwarancja usuwania plików nawet przy błędach
- ✅ **Walidacja danych** - sprawdzanie poprawności przed zapisem do bazy
- ✅ **Ochrona przed memory leak** - limit iteracji w przetwarzaniu kolejki logów

**Jakość kodu:**
- ✅ **Walidacja nazw produktów** - sprawdzanie długości i czyszczenie
- ✅ **Obsługa ujemnych rabatów** - poprawne wykrywanie i korekta błędnych wartości

**Bezpieczeństwo (2025-11-22):**
- ✅ **Walidacja ścieżek plików** - ochrona przed path traversal attacks
- ✅ **Bezpieczne pliki tymczasowe** - odpowiednie uprawnienia (chmod 600) i cleanup
- ✅ **Walidacja rozmiaru plików** - ochrona przed DoS (max 100MB dla plików, 50MB dla obrazów)
- ✅ **Walidacja wymiarów obrazów** - maksymalne wymiary 10000x10000px
- ✅ **Sanityzacja logów** - usuwanie wrażliwych danych (pełne ścieżki, długie teksty OCR)
- ✅ **Walidacja modeli LLM** - tylko dozwolone modele mogą być używane
- ✅ **Nowy moduł bezpieczeństwa** - `ReceiptParser/src/security.py` z funkcjami walidacji i sanityzacji

### Wprowadzone Ulepszenia Jakości Kodu (2025-11-22)

**Refaktoryzacja i Czytelność:**
- ✅ **Eliminacja magic numbers** - wszystkie hardcoded wartości przeniesione do stałych konfiguracyjnych (`Config`)
- ✅ **Type safety** - użycie `TypedDict` (`ParsedData`) zamiast `Dict` w sygnaturach metod
- ✅ **Eliminacja duplikacji** - wspólna metoda `_merge_discounts()` dla strategii Lidl i Biedronka
- ✅ **Podział długich metod** - `KauflandStrategy.post_process()` podzielona na 5 mniejszych funkcji
- ✅ **Opcjonalne logowanie do pliku** - moduł `logger.py` z możliwością zapisu logów do pliku

**Konfiguracja:**
- ✅ **Stałe matematyczne** - `MATH_TOLERANCE`, `SIGNIFICANT_DIFFERENCE`, `MIN_PRODUCT_PRICE`
- ✅ **Stałe dla Kaufland** - `KAUFLAND_TYPICAL_DISCOUNTS`, `KAUFLAND_DISCOUNT_TOLERANCE`
- ✅ **Logowanie do pliku** - włączane przez `ENABLE_FILE_LOGGING=true` w `.env`

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

## 📝 Licencja

Projekt stworzony w celach edukacyjnych i do użytku domowego.

## 🤝 Autor

**Marcin** (CodeMarcinu)

## 🙏 Podziękowania

- **Ollama** - za lokalne modele LLM
- **Mistral AI** - za API OCR
- **Tesseract OCR** - za darmowy OCR
- **CustomTkinter** - za nowoczesny interfejs GUI

---

*Jeśli masz pytania lub sugestie, utwórz issue w repozytorium.*

