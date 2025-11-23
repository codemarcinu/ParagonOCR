# 📚 ParagonWeb - Pełna Dokumentacja

## Spis treści

1. [Wprowadzenie](#wprowadzenie)
2. [Architektura](#architektura)
3. [Instalacja](#instalacja)
4. [Konfiguracja](#konfiguracja)
5. [Użytkowanie](#użytkowanie)
6. [API Reference](#api-reference)
7. [Deweloperzy](#deweloperzy)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Wprowadzenie

**ParagonWeb** to nowoczesna aplikacja webowa do zarządzania paragonami zakupowymi. Aplikacja automatycznie ekstrahuje dane z paragonów (PDF, PNG, JPG), kategoryzuje produkty, śledzi stan magazynowy i oferuje inteligentnego asystenta kulinarnego.

### Główne funkcjonalności

- 📄 **Automatyczne przetwarzanie paragonów** - OCR + AI parsowanie
- 📦 **Zarządzanie magazynem** - Śledzenie produktów, dat ważności
- 📊 **Analityka zakupów** - Statystyki, wykresy, trendy
- 🦅 **Asystent Bielik** - AI asystent kulinarny z RAG
- 🌐 **Interfejs webowy** - Działa w przeglądarce, responsywny
- 🐳 **Docker ready** - Łatwa instalacja i deployment

### Wymagania systemowe

**Minimalne:**
- Python 3.13+ (lub Docker)
- 2GB RAM
- 1GB wolnego miejsca na dysku

**Zalecane:**
- Python 3.13+
- 4GB RAM
- 5GB wolnego miejsca
- Dostęp do internetu (dla trybu Cloud)

---

## Architektura

### Komponenty

```
┌─────────────────────────────────────────────────────────┐
│                    ParagonWeb                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐         ┌──────────────┐            │
│  │  NiceGUI     │◄────────┤   FastAPI    │            │
│  │  Frontend    │  HTTP   │   Backend    │            │
│  │  (Port 8080) │         │  (Port 8000) │            │
│  └──────────────┘         └──────────────┘            │
│                                                         │
│         │                        │                      │
│         ▼                        ▼                      │
│  ┌──────────────────────────────────────┐             │
│  │      ReceiptParser (Core Logic)      │             │
│  │  - OCR Providers (Mistral/Tesseract) │             │
│  │  - AI Providers (OpenAI/Ollama)     │             │
│  │  - Database (SQLite)                 │             │
│  │  - Business Logic                    │             │
│  └──────────────────────────────────────┘             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Przepływ danych

1. **Upload paragonu** → Frontend (NiceGUI)
2. **Przetwarzanie** → Backend (FastAPI)
3. **OCR** → Mistral OCR API lub Tesseract (lokalnie)
4. **Parsowanie** → OpenAI API lub Ollama (lokalnie)
5. **Zapis** → SQLite Database
6. **Wyświetlenie** → Frontend

### Tryby działania

#### Tryb Cloud (Domyślny)
- **OCR:** Mistral OCR API
- **AI:** OpenAI API (GPT-4o-mini)
- **Zalety:** Brak instalacji, wysoka jakość, działa wszędzie
- **Wymagania:** Klucze API (Mistral + OpenAI)

#### Tryb Lokalny
- **OCR:** Tesseract (lokalnie)
- **AI:** Ollama (lokalnie)
- **Zalety:** Brak kosztów, pełna kontrola
- **Wymagania:** Tesseract + Ollama z modelami

---

## Instalacja

### Metoda 1: Docker (Zalecana)

**Krok 1:** Sklonuj repozytorium
```bash
git clone <repo-url>
cd ParagonOCR
git checkout feature/web-app-transformation
```

**Krok 2:** Utwórz plik `.env` (opcjonalnie)
```bash
cd ReceiptParser
cat > .env << EOF
USE_CLOUD_AI=true
USE_CLOUD_OCR=true
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
EOF
```

**Krok 3:** Uruchom Docker
```bash
cd ..
docker-compose up --build
```

**Krok 4:** Otwórz przeglądarkę
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- Dokumentacja API: http://localhost:8000/docs

### Metoda 2: Instalacja lokalna

**Krok 1:** Przygotuj środowisko
```bash
python3.13 -m venv venv
source venv/bin/activate  # Linux/Mac
# lub
venv\Scripts\activate  # Windows
```

**Krok 2:** Zainstaluj zależności
```bash
cd ReceiptParser
pip install -r requirements.txt
```

**Krok 3:** Konfiguracja
```bash
# Utwórz plik .env
cat > .env << EOF
USE_CLOUD_AI=true
USE_CLOUD_OCR=true
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
EOF
```

**Krok 4:** Inicjalizuj bazę danych
```bash
python -m ReceiptParser.src.main init-db
```

**Krok 5:** Uruchom aplikację
```bash
# Terminal 1: Backend
cd ..
python server.py

# Terminal 2: Frontend
python web_app.py
```

### Metoda 3: Tryb lokalny (bez Cloud API)

#### Opcja A: Docker (Zalecane)

**Krok 1:** Uruchom z konfiguracją lokalną
```bash
docker-compose -f docker-compose.local.yml up -d --build
```

**Krok 2:** Pobierz modele Ollama (pierwszy raz)
```bash
# Ollama automatycznie pobierze modele przy pierwszym użyciu
# Lub ręcznie:
docker exec -it paragon_ollama ollama pull llava:latest
docker exec -it paragon_ollama ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
```

**Uwaga:** W Dockerze Ollama jest w osobnym kontenerze i komunikuje się przez sieć Docker.

#### Opcja B: Lokalna instalacja

**Wymagania:**
- Tesseract OCR: `sudo apt-get install tesseract-ocr tesseract-ocr-pol`
- Ollama: https://ollama.ai/download

**Konfiguracja:**
```bash
# .env
USE_CLOUD_AI=false
USE_CLOUD_OCR=false
OLLAMA_HOST=http://localhost:11434
VISION_MODEL=llava:latest
TEXT_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
```

**Uruchom Ollama:**
```bash
ollama serve
# W osobnym terminalu:
ollama pull llava:latest
ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
```

---

## Konfiguracja

### Zmienne środowiskowe

Plik `.env` w katalogu `ReceiptParser/`:

```env
# === Tryb działania ===
USE_CLOUD_AI=true          # true = OpenAI, false = Ollama
USE_CLOUD_OCR=true        # true = Mistral OCR, false = Tesseract

# === Ollama (tylko dla USE_CLOUD_AI=false) ===
# W Dockerze automatycznie ustawiane na http://ollama:11434
# Lokalnie: http://localhost:11434
OLLAMA_HOST=http://localhost:11434

# === Cloud API Keys ===
OPENAI_API_KEY=sk-...     # Wymagane jeśli USE_CLOUD_AI=true
MISTRAL_API_KEY=...       # Wymagane jeśli USE_CLOUD_OCR=true

# === Lokalne ustawienia (dla USE_CLOUD_AI=false) ===
OLLAMA_HOST=http://localhost:11434
VISION_MODEL=llava:latest
TEXT_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
OLLAMA_TIMEOUT=300

# === Opcjonalne ===
ENABLE_FILE_LOGGING=true  # Logi do pliku
```

### Uzyskanie kluczy API

#### OpenAI API Key
1. Przejdź na https://platform.openai.com/api-keys
2. Zaloguj się lub utwórz konto
3. Kliknij "Create new secret key"
4. Skopiuj klucz (zaczyna się od `sk-`)
5. **Uwaga:** Klucz jest widoczny tylko raz!

**Koszty:** ~$0.15 za 1M tokenów (GPT-4o-mini), typowe użycie: ~5 PLN/miesiąc

#### Mistral API Key
1. Przejdź na https://console.mistral.ai/
2. Zaloguj się lub utwórz konto
3. Przejdź do "API Keys"
4. Utwórz nowy klucz
5. Skopiuj klucz

**Koszty:** Darmowy tier dostępny, płatne: ~$0.01 za stronę OCR

### Konfiguracja przez UI

Możesz również skonfigurować aplikację przez interfejs webowy:
1. Otwórz http://localhost:8080/ustawienia
2. Przełącz tryby Cloud/Lokalny
3. Wprowadź klucze API
4. Kliknij "Zapisz ustawienia"

---

## Użytkowanie

### Dashboard

**Dodawanie paragonu:**
1. Kliknij "Wybierz plik paragonu"
2. Wybierz plik (PNG, JPG, PDF)
3. Plik zostanie automatycznie przesłany i przetworzony
4. Postęp przetwarzania jest widoczny na pasku postępu

**Statystyki:**
- Łączna liczba paragonów
- Suma wydatków
- Liczba pozycji
- Ostatnie paragony

### Magazyn

**Przegląd produktów:**
- Lista wszystkich produktów w magazynie
- Ilość, jednostka, data ważności
- Kategoria produktu
- Status (OK, Wkrótce przeterminowany, Przeterminowany)

**Filtrowanie:**
- Sortowanie po dacie ważności
- Wyszukiwanie po nazwie

### Bielik - Asystent Kulinarny

**Funkcje:**
- Odpowiadanie na pytania o jedzenie
- Propozycje potraw na podstawie dostępnych produktów
- Generowanie list zakupów
- Wyszukiwanie produktów w bazie

**Przykłady pytań:**
- "Co mam do jedzenia?"
- "Co mogę zrobić na obiad?"
- "Czy mam mleko w magazynie?"
- "Jakie potrawy mogę przygotować?"

### Ustawienia

**Tryb działania:**
- Przełącznik Cloud AI (OpenAI) / Lokalny (Ollama)
- Przełącznik Cloud OCR (Mistral) / Lokalny (Tesseract)

**Klucze API:**
- Pole na OpenAI API Key
- Pole na Mistral API Key
- Klucze są ukryte (password field)

---

## API Reference

### Base URL
```
http://localhost:8000
```

### Endpointy

#### POST /api/upload
Przetwarza przesłany paragon.

**Request:**
```http
POST /api/upload
Content-Type: multipart/form-data

file: <plik>
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "processing"
}
```

**Status zadania:**
```http
GET /api/task/{task_id}
```

**Response:**
```json
{
  "status": "completed|processing|error",
  "progress": 0-100,
  "message": "Status message"
}
```

#### GET /api/receipts
Zwraca listę paragonów.

**Query Parameters:**
- `skip` (int, default: 0) - Liczba paragonów do pominięcia
- `limit` (int, default: 50) - Maksymalna liczba paragonów

**Response:**
```json
{
  "receipts": [
    {
      "paragon_id": 1,
      "sklep": "Lidl",
      "data_zakupu": "2025-01-15",
      "suma_paragonu": 123.45,
      "liczba_pozycji": 10,
      "plik_zrodlowy": "/path/to/file.pdf"
    }
  ],
  "total": 1
}
```

#### GET /api/stats
Zwraca statystyki zakupów.

**Response:**
```json
{
  "total_statistics": {
    "total_receipts": 50,
    "total_spent": 5000.00,
    "total_items": 500,
    "avg_receipt": 100.00
  },
  "by_store": [
    {"name": "Lidl", "amount": 2000.00}
  ],
  "by_category": [
    {"name": "Nabiał", "amount": 500.00}
  ],
  "top_products": [
    {"name": "Mleko", "count": 20, "total": 200.00}
  ],
  "monthly": [
    {
      "month": "Styczeń 2025",
      "receipts": 10,
      "spent": 1000.00
    }
  ]
}
```

#### GET /api/inventory
Zwraca stan magazynu.

**Response:**
```json
{
  "inventory": [
    {
      "produkt_id": 1,
      "nazwa": "Mleko",
      "ilosc": 2.0,
      "jednostka": "l",
      "data_waznosci": "2025-01-20",
      "zamrozone": false,
      "kategoria": "Nabiał"
    }
  ]
}
```

#### POST /api/chat
Wysyła wiadomość do asystenta Bielik.

**Request:**
```json
{
  "question": "Co mam do jedzenia?"
}
```

**Response:**
```json
{
  "answer": "Masz w magazynie: mleko, chleb, jajka..."
}
```

#### GET /api/settings
Zwraca aktualne ustawienia.

**Response:**
```json
{
  "use_cloud_ai": true,
  "use_cloud_ocr": true,
  "openai_api_key_set": true,
  "mistral_api_key_set": true
}
```

#### POST /api/settings
Aktualizuje ustawienia.

**Request:**
```json
{
  "use_cloud_ai": true,
  "use_cloud_ocr": true,
  "openai_api_key": "sk-...",
  "mistral_api_key": "..."
}
```

**Response:**
```json
{
  "message": "Ustawienia zaktualizowane"
}
```

### Dokumentacja interaktywna

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Deweloperzy

### Struktura projektu

```
ParagonOCR/
├── server.py                 # FastAPI backend
├── web_app.py                # NiceGUI frontend
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker orchestration
├── ReceiptParser/
│   ├── src/
│   │   ├── ai_providers.py   # AI provider abstractions
│   │   ├── ocr_providers.py  # OCR provider abstractions
│   │   ├── config.py         # Configuration
│   │   ├── main.py           # Main processing pipeline
│   │   ├── bielik.py         # Bielik assistant
│   │   ├── llm.py            # LLM integration
│   │   ├── database.py       # Database models
│   │   └── ...
│   └── requirements.txt      # Dependencies
└── tests/                    # Testy
```

### Dodawanie nowego dostawcy AI

```python
# ReceiptParser/src/ai_providers.py

class CustomAIProvider(AIProvider):
    def chat(self, model, messages, format=None, options=None, images=None):
        # Implementacja
        pass
    
    def is_available(self):
        # Sprawdź dostępność
        return True
```

### Dodawanie nowego dostawcy OCR

```python
# ReceiptParser/src/ocr_providers.py

class CustomOCRProvider(OCRProvider):
    def extract_text(self, image_path: str) -> str:
        # Implementacja
        pass
    
    def is_available(self):
        # Sprawdź dostępność
        return True
```

### Testowanie

```bash
# Uruchom testy
pytest tests/

# Z coverage
pytest --cov=ReceiptParser tests/
```

### Rozwój lokalny

```bash
# Backend w trybie dev (auto-reload)
uvicorn server:app --reload --host 0.0.0.0 --port 8000

# Frontend w trybie dev
python web_app.py --reload
```

---

## Troubleshooting

### Problem: "Dostawca AI nie jest dostępny"

**Rozwiązanie:**
1. **Tryb Cloud:**
   - Sprawdź czy `OPENAI_API_KEY` jest ustawiony
   - Sprawdź czy klucz jest poprawny: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`

2. **Tryb Lokalny:**
   - **W Dockerze:**
     - Sprawdź czy kontener Ollama działa: `docker ps | grep ollama`
     - Sprawdź logi: `docker logs paragon_ollama`
     - Sprawdź dostępność: `docker exec paragon_ollama curl http://localhost:11434/api/tags`
   - **Lokalnie:**
     - Sprawdź czy Ollama działa: `curl http://localhost:11434/api/tags`
     - Sprawdź czy model jest pobrany: `ollama list`

### Problem: "Dostawca OCR nie jest dostępny"

**Rozwiązanie:**
1. **Tryb Cloud:**
   - Sprawdź czy `MISTRAL_API_KEY` jest ustawiony
   - Sprawdź czy klucz jest poprawny: `curl https://api.mistral.ai/v1/models -H "Authorization: Bearer $MISTRAL_API_KEY"`

2. **Tryb Lokalny:**
   - Sprawdź czy Tesseract jest zainstalowany: `tesseract --version`
   - Sprawdź czy język polski jest zainstalowany: `tesseract --list-langs`

### Problem: "Błąd połączenia z API"

**Rozwiązanie:**
1. Sprawdź czy backend działa: `curl http://localhost:8000/`
2. Sprawdź logi: `docker-compose logs` lub `./logs/`
3. Sprawdź porty: `netstat -tuln | grep 8000`

### Problem: "Baza danych nie istnieje"

**Rozwiązanie:**
```bash
python -m ReceiptParser.src.main init-db
```

### Problem: "Docker build fails"

**Rozwiązanie:**
1. Sprawdź czy Docker działa: `docker ps`
2. Sprawdź logi builda: `docker-compose build --no-cache`
3. Sprawdź czy porty są wolne: `lsof -i :8000 -i :8080`

### Problem: "Upload pliku nie działa"

**Rozwiązanie:**
1. Sprawdź czy katalog `uploads/` istnieje i ma uprawnienia zapisu
2. Sprawdź rozmiar pliku (max 50MB)
3. Sprawdź format pliku (tylko PNG, JPG, PDF)

---

## FAQ

### P: Ile kosztuje użycie aplikacji?

**O:** W trybie Cloud:
- Mistral OCR: Darmowy tier lub ~$0.01/strona
- OpenAI: ~$0.15 za 1M tokenów (GPT-4o-mini)
- **Typowe użycie domowe: ~5 PLN/miesiąc**

W trybie lokalnym: **0 PLN** (wymaga własnego sprzętu)

### P: Czy mogę używać aplikacji bez internetu?

**O:** Tak, w trybie lokalnym (Ollama + Tesseract). Wymaga:
- Zainstalowanego Tesseract
- Uruchomionego Ollama z modelami

### P: Jakie formaty plików są obsługiwane?

**O:** 
- Obrazy: PNG, JPG, JPEG
- Dokumenty: PDF

### P: Czy dane są bezpieczne?

**O:** 
- Wszystkie dane są przechowywane lokalnie (SQLite)
- Klucze API są przechowywane w zmiennych środowiskowych
- W trybie Cloud, obrazy są wysyłane do API (Mistral/OpenAI)
- **Rekomendacja:** Używaj trybu lokalnego dla wrażliwych danych

### P: Jak zrobić backup danych?

**O:**
```bash
# Backup bazy danych
cp ReceiptParser/data/receipts.db ReceiptParser/data/receipts.db.backup

# Backup całego katalogu danych
tar -czf backup.tar.gz ReceiptParser/data/
```

### P: Czy mogę uruchomić aplikację na serwerze?

**O:** Tak! Docker pozwala na łatwy deployment:
```bash
# Na serwerze
git clone <repo>
cd ParagonOCR
docker-compose up -d
```

### P: Jak zaktualizować aplikację?

**O:**
```bash
# Docker
docker-compose pull
docker-compose up -d --build

# Lokalnie
git pull
pip install -r ReceiptParser/requirements.txt --upgrade
```

### P: Czy mogę używać własnych modeli AI?

**O:** Tak! W trybie lokalnym możesz używać dowolnych modeli Ollama:
```env
VISION_MODEL=twoj-model:latest
TEXT_MODEL=twoj-model:latest
```

---

## Wsparcie

- **Issues:** GitHub Issues
- **Dokumentacja:** Ten plik
- **API Docs:** http://localhost:8000/docs

---

**Wersja dokumentacji:** 1.0.0  
**Ostatnia aktualizacja:** 2025-11-23

