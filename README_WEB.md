# ParagonWeb - Aplikacja Webowa

ParagonWeb to nowoczesna aplikacja webowa do zarządzania paragonami, zbudowana na FastAPI i NiceGUI.

## 🚀 Szybki Start

### Opcja 1: Docker (Zalecane)

Najprostszy sposób na uruchomienie aplikacji:

```bash
# Zbuduj i uruchom kontener
docker-compose up --build

# Aplikacja będzie dostępna pod:
# - Frontend: http://localhost:8080
# - Backend API: http://localhost:8000
```

### Opcja 2: Lokalne uruchomienie

1. **Zainstaluj zależności:**

```bash
cd ReceiptParser
pip install -r requirements.txt
```

2. **Skonfiguruj zmienne środowiskowe:**

Utwórz plik `.env` w katalogu `ReceiptParser/`:

```env
# Tryb Cloud (domyślny - zalecany dla łatwości użycia)
USE_CLOUD_AI=true
USE_CLOUD_OCR=true

# Klucze API (wymagane dla trybu Cloud)
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...

# Alternatywnie: Tryb lokalny
# USE_CLOUD_AI=false
# USE_CLOUD_OCR=false
# OLLAMA_HOST=http://localhost:11434
```

3. **Inicjalizuj bazę danych:**

```bash
python -m ReceiptParser.src.main init-db
```

4. **Uruchom backend:**

```bash
python server.py
```

5. **W osobnym terminalu uruchom frontend:**

```bash
python web_app.py
```

Aplikacja będzie dostępna pod:
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000

## 📋 Funkcjonalności

### Dashboard
- Dodawanie paragonów przez upload plików (PNG, JPG, PDF)
- Podgląd statystyk zakupów
- Lista ostatnich paragonów

### Magazyn
- Przegląd stanu magazynowego produktów
- Informacje o datach ważności
- Kategorie produktów

### Bielik - Asystent Kulinarny
- Czat z asystentem AI
- Propozycje potraw na podstawie dostępnych produktów
- Generowanie list zakupów

### Ustawienia
- Przełączanie między trybem Cloud a Lokalnym
- Konfiguracja kluczy API
- Zarządzanie ustawieniami aplikacji

## 🔧 Konfiguracja

### Tryb Cloud (Domyślny)

Domyślnie aplikacja używa Cloud API:
- **OCR:** Mistral OCR API
- **AI:** OpenAI API (GPT-4o-mini)

**Zalety:**
- Brak potrzeby instalacji Tesseract/Poppler
- Działa na każdym systemie operacyjnym
- Wysoka jakość OCR i AI

**Wymagania:**
- Klucz API Mistral (darmowy tier dostępny)
- Klucz API OpenAI (płatny, ale bardzo tani - ~5 PLN/miesiąc dla domowego użycia)

### Tryb Lokalny

Alternatywnie można użyć lokalnych narzędzi:
- **OCR:** Tesseract (wymaga instalacji)
- **AI:** Ollama (wymaga uruchomienia lokalnego serwera)

**Zalety:**
- Brak kosztów API
- Pełna kontrola nad danymi

**Wymagania:**
- Zainstalowany Tesseract OCR
- Uruchomiony serwer Ollama z modelami

## 📊 API Endpoints

Backend udostępnia REST API:

- `POST /api/upload` - Przetwarzanie paragonu
- `GET /api/task/{task_id}` - Status zadania
- `GET /api/receipts` - Lista paragonów
- `GET /api/stats` - Statystyki zakupów
- `GET /api/inventory` - Stan magazynu
- `POST /api/chat` - Czat z Bielikiem
- `GET /api/settings` - Pobierz ustawienia
- `POST /api/settings` - Zaktualizuj ustawienia

## 🐳 Docker

### Budowanie obrazu

```bash
docker build -t paragon-web .
```

### Uruchomienie

```bash
docker-compose up
```

### Volume'y

Aplikacja używa następujących volume'ów:
- `./ReceiptParser/data` - Baza danych SQLite
- `./logs` - Logi aplikacji
- `./paragony` - Pliki paragonów
- `./uploads` - Tymczasowe pliki uploadów

## 🔒 Bezpieczeństwo

- Wszystkie klucze API są przechowywane w zmiennych środowiskowych
- Upload plików jest walidowany (tylko PNG, JPG, PDF)
- CORS jest skonfigurowany (w produkcji ustaw konkretne domeny)

## 📝 Uwagi

- Aplikacja używa SQLite jako bazy danych (wystarczająca dla domowego użycia)
- W trybie Cloud, koszty API są minimalne (~5 PLN/miesiąc dla typowego użycia)
- Frontend NiceGUI działa w przeglądarce, nie wymaga instalacji dodatkowych narzędzi

## 🆘 Rozwiązywanie problemów

### Błąd: "Dostawca AI nie jest dostępny"

**Rozwiązanie:**
- Sprawdź czy klucz API OpenAI jest ustawiony (tryb Cloud)
- Lub sprawdź czy Ollama działa (tryb lokalny): `curl http://localhost:11434/api/tags`

### Błąd: "Dostawca OCR nie jest dostępny"

**Rozwiązanie:**
- Sprawdź czy klucz API Mistral jest ustawiony (tryb Cloud)
- Lub sprawdź czy Tesseract jest zainstalowany (tryb lokalny): `tesseract --version`

### Błąd połączenia z API

**Rozwiązanie:**
- Sprawdź czy backend działa: `curl http://localhost:8000/`
- Sprawdź logi w `./logs/`

## 📚 Dokumentacja API

Pełna dokumentacja API jest dostępna pod adresem:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

