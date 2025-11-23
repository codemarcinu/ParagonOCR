# 📄 ParagonOCR / ParagonWeb

> Automatyczne przetwarzanie paragonów zakupowych z wykorzystaniem AI i OCR

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

## 🚀 Szybki Start

### Docker (Zalecane - 2 minuty)

```bash
# 1. Sklonuj repozytorium
git clone <repo-url>
cd ParagonOCR
git checkout feature/web-app-transformation

# 2. Skonfiguruj klucze API (opcjonalnie - można później przez UI)
cd ReceiptParser
cat > .env << EOF
USE_CLOUD_AI=true
USE_CLOUD_OCR=true
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
EOF

# 3. Uruchom
cd ..
docker-compose up --build

# 4. Otwórz przeglądarkę
# Frontend: http://localhost:8081 (lub 8080 jeśli wolny)
# Backend API: http://localhost:8000
```

### Lokalnie

```bash
# 1. Zainstaluj zależności
cd ReceiptParser
pip install -r requirements.txt

# 2. Konfiguracja (jak wyżej)

# 3. Inicjalizuj bazę
python -m ReceiptParser.src.main init-db

# 4. Uruchom (2 terminale)
# Terminal 1:
python server.py
# Terminal 2:
python web_app.py
```

## 📚 Dokumentacja

- **[📖 Pełna Dokumentacja](DOCUMENTATION.md)** - Kompleksowy przewodnik użytkownika i dewelopera
- **[🔌 Dokumentacja API](API_DOCUMENTATION.md)** - Szczegółowa dokumentacja REST API
- **[🚀 Przewodnik Deployment](DEPLOYMENT.md)** - Instrukcje wdrożenia na różnych platformach
- **[🐳 Ollama w Dockerze](DOCKER_OLLAMA.md)** - Konfiguracja i użycie Ollama w Dockerze
- **[📝 Changelog](CHANGELOG_WEB.md)** - Lista zmian w transformacji do wersji webowej
- **[🌐 README Web](README_WEB.md)** - Szybki przewodnik dla wersji webowej

## ✨ Funkcjonalności

### 🎯 Główne

- **📄 Automatyczne przetwarzanie paragonów** - OCR + AI parsowanie (PDF, PNG, JPG)
- **📦 Zarządzanie magazynem** - Śledzenie produktów, dat ważności, kategorii
- **📊 Analityka zakupów** - Statystyki, trendy, wykresy wydatków
- **🦅 Asystent Bielik** - AI asystent kulinarny z RAG (Retrieval-Augmented Generation)
- **🌐 Interfejs webowy** - Nowoczesny UI w przeglądarce, responsywny
- **🐳 Docker ready** - Łatwa instalacja i deployment

### 🔧 Techniczne

- **Hybrydowy tryb działania:**
  - **Cloud:** Mistral OCR + OpenAI (domyślny, łatwy w użyciu)
  - **Lokalny:** Tesseract + Ollama (bez kosztów, pełna kontrola)
- **Docker ready:**
  - Ollama w osobnym kontenerze (automatyczna konfiguracja)
  - Komunikacja między kontenerami przez sieć Docker
  - Volume dla modeli Ollama (zachowuje modele między restartami)
- **REST API** - Pełne API dla integracji z innymi aplikacjami
- **SQLite Database** - Lekka baza danych, łatwa kopia zapasowa
- **Modularna architektura** - Łatwe rozszerzanie i utrzymanie

## 🏗️ Architektura

```
┌─────────────────────────────────────────┐
│         ParagonWeb Application          │
├─────────────────────────────────────────┤
│                                         │
│  ┌────────────┐      ┌────────────┐    │
│  │  NiceGUI   │◄─────┤  FastAPI   │    │
│  │  Frontend  │ HTTP │  Backend   │    │
│  │  :8080     │      │  :8000     │    │
│  └────────────┘      └────────────┘    │
│                           │             │
│                           ▼             │
│  ┌──────────────────────────────┐      │
│  │   ReceiptParser (Core)      │      │
│  │  - OCR Providers             │      │
│  │  - AI Providers              │      │
│  │  - Database (SQLite)         │      │
│  │  - Business Logic            │      │
│  └──────────────────────────────┘      │
│                                         │
└─────────────────────────────────────────┘
```

## 💰 Koszty

### Tryb Cloud (Domyślny)

- **Mistral OCR:** Darmowy tier lub ~$0.01/strona
- **OpenAI (GPT-4o-mini):** ~$0.15 za 1M tokenów
- **Typowe użycie domowe:** ~5 PLN/miesiąc

### Tryb Lokalny

- **0 PLN** - Wymaga własnego sprzętu (Tesseract + Ollama)

## 📋 Wymagania

### Minimalne
- Python 3.13+ (lub Docker)
- 2GB RAM
- 1GB wolnego miejsca

### Zalecane
- Python 3.13+
- 4GB RAM
- 5GB wolnego miejsca
- Dostęp do internetu (dla trybu Cloud)

## 🔑 Konfiguracja

### Klucze API (Tryb Cloud)

1. **OpenAI API Key:**
   - Przejdź na https://platform.openai.com/api-keys
   - Utwórz nowy klucz
   - Skopiuj (zaczyna się od `sk-`)

2. **Mistral API Key:**
   - Przejdź na https://console.mistral.ai/
   - Utwórz nowy klucz
   - Skopiuj

### Plik .env

Utwórz plik `ReceiptParser/.env`:

```env
USE_CLOUD_AI=true
USE_CLOUD_OCR=true
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
```

Lub skonfiguruj przez UI: http://localhost:8080/ustawienia

## 🎮 Użycie

### Dashboard
- Dodawanie paragonów przez drag & drop
- Podgląd statystyk zakupów
- Lista ostatnich paragonów

### Magazyn
- Przegląd produktów w magazynie
- Filtrowanie po kategorii, dacie ważności
- Status produktów (OK, Wkrótce przeterminowany, Przeterminowany)

### Bielik
- Czat z asystentem kulinarnym
- Propozycje potraw
- Generowanie list zakupów

### API
- Pełne REST API dostępne pod http://localhost:8000
- Dokumentacja interaktywna: http://localhost:8000/docs

## 🛠️ Rozwój

### Struktura projektu

```
ParagonOCR/
├── server.py              # FastAPI backend
├── web_app.py             # NiceGUI frontend
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker orchestration
├── ReceiptParser/
│   ├── src/
│   │   ├── ai_providers.py    # AI abstractions
│   │   ├── ocr_providers.py   # OCR abstractions
│   │   ├── main.py            # Processing pipeline
│   │   ├── bielik.py          # Bielik assistant
│   │   └── ...
│   └── requirements.txt
└── docs/                  # Dokumentacja
```

### Testowanie

```bash
pytest tests/
pytest --cov=ReceiptParser tests/
```

### Contributing

1. Fork repozytorium
2. Utwórz feature branch (`git checkout -b feature/amazing-feature`)
3. Commit zmian (`git commit -m 'Add amazing feature'`)
4. Push do brancha (`git push origin feature/amazing-feature`)
5. Otwórz Pull Request

## 📖 Przykłady

### Upload paragonu przez API

```python
import requests

with open('receipt.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/upload',
        files={'file': f}
    )
    task_id = response.json()['task_id']
```

### Zapytanie do Bielika

```python
response = requests.post(
    'http://localhost:8000/api/chat',
    json={'question': 'Co mam do jedzenia?'}
)
answer = response.json()['answer']
print(answer)
```

### Pobranie statystyk

```python
response = requests.get('http://localhost:8000/api/stats')
stats = response.json()
print(f"Wydatki: {stats['total_statistics']['total_spent']} PLN")
```

## 🐛 Troubleshooting

### Problem: "Dostawca AI nie jest dostępny"

**Rozwiązanie:**
- Sprawdź klucz API OpenAI (tryb Cloud)
- Lub sprawdź czy Ollama działa (tryb lokalny): `curl http://localhost:11434/api/tags`

### Problem: "Błąd połączenia z API"

**Rozwiązanie:**
- Sprawdź czy backend działa: `curl http://localhost:8000/`
- Sprawdź logi: `docker-compose logs` lub `./logs/`

Więcej w [Dokumentacji](DOCUMENTATION.md#troubleshooting).

## 📝 Licencja

[Tu wstaw licencję]

## 🙏 Podziękowania

- [FastAPI](https://fastapi.tiangolo.com/) - Nowoczesny framework webowy
- [NiceGUI](https://nicegui.io/) - Pythonowy framework UI
- [OpenAI](https://openai.com/) - API AI
- [Mistral AI](https://mistral.ai/) - OCR API
- [Ollama](https://ollama.ai/) - Lokalne modele AI

## 📞 Kontakt

- **Issues:** GitHub Issues
- **Dokumentacja:** [DOCUMENTATION.md](DOCUMENTATION.md)
- **API Docs:** http://localhost:8000/docs (po uruchomieniu)

---

**Wersja:** 2.0.0 (Web)  
**Status:** 🚧 W rozwoju (feature/web-app-transformation)
