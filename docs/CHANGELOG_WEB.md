# Changelog - Transformacja do ParagonWeb

## 🎉 Nowa wersja: ParagonWeb

Projekt został przekształcony z aplikacji desktopowej (CustomTkinter) w nowoczesną aplikację webową.

## ✨ Nowe funkcjonalności

### Architektura Webowa
- **FastAPI Backend** - RESTful API z automatyczną dokumentacją (Swagger)
- **NiceGUI Frontend** - Nowoczesny interfejs webowy w Pythonie
- **Docker Support** - Pełna konteneryzacja aplikacji

### Abstrakcje dostawców
- **AIProvider** - Wsparcie dla OpenAI (Cloud) i Ollama (Local)
- **OCRProvider** - Wsparcie dla Mistral OCR (Cloud) i Tesseract (Local)
- **Konfiguracja** - Łatwe przełączanie między trybem Cloud a Lokalnym

### Nowe endpointy API
- `POST /api/upload` - Przetwarzanie paragonów
- `GET /api/receipts` - Lista paragonów
- `GET /api/stats` - Statystyki zakupów
- `GET /api/inventory` - Stan magazynu
- `POST /api/chat` - Czat z Bielikiem
- `GET/POST /api/settings` - Zarządzanie ustawieniami

## 🔄 Zmiany w kodzie

### Nowe pliki
- `server.py` - FastAPI backend
- `web_app.py` - NiceGUI frontend
- `ReceiptParser/src/ai_providers.py` - Abstrakcje dostawców AI
- `ReceiptParser/src/ocr_providers.py` - Abstrakcje dostawców OCR
- `Dockerfile` - Konfiguracja Docker
- `docker-compose.yml` - Orchestracja kontenerów
- `README_WEB.md` - Dokumentacja dla wersji webowej

### Zmodyfikowane pliki
- `ReceiptParser/src/config.py` - Dodano flagi USE_CLOUD_AI, USE_CLOUD_OCR, OPENAI_API_KEY
- `ReceiptParser/src/bielik.py` - Używa abstrakcji AIProvider
- `ReceiptParser/src/llm.py` - Używa abstrakcji AIProvider
- `ReceiptParser/src/main.py` - Używa abstrakcji OCRProvider
- `ReceiptParser/requirements.txt` - Dodano fastapi, uvicorn, nicegui, openai

### Usunięte pliki
- `gui.py` - Zastąpiony przez `web_app.py` (zachowany dla kompatybilności)

## 🚀 Migracja

### Dla użytkowników

1. **Zachowanie danych:**
   - Baza danych SQLite pozostaje bez zmian (`ReceiptParser/data/receipts.db`)
   - Wszystkie dane są kompatybilne

2. **Nowa konfiguracja:**
   - Utwórz plik `.env` w katalogu `ReceiptParser/`:
   ```env
   USE_CLOUD_AI=true
   USE_CLOUD_OCR=true
   OPENAI_API_KEY=sk-...
   MISTRAL_API_KEY=...
   ```

3. **Uruchomienie:**
   - **Docker (zalecane):** `docker-compose up`
   - **Lokalnie:** `python server.py` + `python web_app.py`

### Dla deweloperów

1. **Nowe zależności:**
   ```bash
   pip install fastapi uvicorn nicegui openai
   ```

2. **Zmiany w API:**
   - `llm.py` - `client` jest teraz wrapperem dla `AIProvider`
   - `bielik.py` - Używa `get_ai_provider()` zamiast bezpośrednio `ollama.Client`
   - `main.py` - Używa `get_ocr_provider()` zamiast bezpośrednio `MistralOCRClient` lub `extract_text_from_image`

3. **Kompatybilność wsteczna:**
   - Stary kod GUI (`gui.py`) nadal działa, ale nie jest rozwijany
   - CLI (`main.py`) działa bez zmian
   - Wszystkie testy powinny działać (wymagają aktualizacji mocków)

## 📝 Uwagi

- **Tryb Cloud jest domyślny** - dla łatwości użycia
- **Koszty API** - ~5 PLN/miesiąc dla typowego domowego użycia
- **Docker** - Wymaga Docker i docker-compose
- **NiceGUI** - Działa w przeglądarce, nie wymaga instalacji dodatkowych narzędzi

## 🔮 Przyszłe ulepszenia

- [ ] WebSocket dla real-time updates
- [ ] Pełna integracja uploadu z śledzeniem postępu
- [ ] Weryfikacja paragonów w UI (obecnie automatyczna)
- [ ] Eksport danych (CSV, JSON)
- [ ] Wykresy i wizualizacje statystyk
- [ ] Multi-user support (opcjonalnie)

## ⚠️ Breaking Changes

- `gui.py` nie jest już głównym interfejsem (zachowany dla kompatybilności)
- Konfiguracja wymaga nowych zmiennych środowiskowych
- API zmieniło się (stare endpointy nie istnieją, ale logika biznesowa pozostaje)

## 📚 Dokumentacja

- `README_WEB.md` - Instrukcje dla wersji webowej
- `http://localhost:8000/docs` - Swagger UI (po uruchomieniu)
- `http://localhost:8000/redoc` - ReDoc (po uruchomieniu)




