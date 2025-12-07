# ✅ Setup Complete - ParagonOCR Web Edition

## Status: Wszystko działa! 🎉

### Backend
- ✅ Virtual environment utworzony
- ✅ Zależności zainstalowane
- ✅ Plik `.env` skonfigurowany
- ✅ Migracje Alembic wykonane
- ✅ Serwer uruchomiony na `http://localhost:8000`
- ✅ Health endpoint działa: `{"status":"healthy"}`

### Frontend
- ✅ Zależności npm zainstalowane
- ✅ Dev server uruchomiony na `http://localhost:5173`
- ✅ Połączony z backendem przez proxy

## Dostępne Endpointy

### Backend API
- `http://localhost:8000/` - Root endpoint
- `http://localhost:8000/health` - Health check
- `http://localhost:8000/docs` - Swagger UI (interaktywna dokumentacja API)
- `http://localhost:8000/api/receipts/upload` - Upload paragonu (POST)
- `http://localhost:8000/api/receipts` - Lista paragonów (GET)
- `http://localhost:8000/api/receipts/{id}` - Szczegóły paragonu (GET)

### Frontend
- `http://localhost:5173` - Aplikacja webowa

## Następne Kroki

1. **Otwórz aplikację w przeglądarce:**
   ```
   http://localhost:5173
   ```

2. **Przetestuj upload paragonu:**
   - Przeciągnij plik PDF/PNG na obszar uploadu
   - Sprawdź czy przetwarza się poprawnie
   - Sprawdź czy pojawia się w dashboardzie

3. **Sprawdź API dokumentację:**
   ```
   http://localhost:8000/docs
   ```

## Zarządzanie Procesami

### Zatrzymanie serwerów:
```bash
# Backend
kill $(cat /tmp/backend.pid)

# Frontend
kill $(cat /tmp/frontend.pid)
```

### Restart serwerów:
```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (nowy terminal)
cd frontend
npm run dev
```

### Logi:
```bash
# Backend logi
tail -f /tmp/backend.log

# Frontend logi
tail -f /tmp/frontend.log
```

## Konfiguracja

### Backend `.env`:
- `OLLAMA_HOST=http://localhost:11434`
- `TEXT_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M`
- `DATABASE_URL=sqlite:///./data/receipts.db`
- `UPLOAD_DIR=./data/uploads`

### Wymagania:
- ✅ Python 3.13.7
- ✅ Node.js v25.2.1
- ✅ Tesseract 5.5.1
- ✅ Ollama (działa, model bielik dostępny)

## Testowanie

### Test 1: Health Check
```bash
curl http://localhost:8000/health
# Oczekiwany wynik: {"status":"healthy"}
```

### Test 2: Upload Paragonu
```bash
curl -X POST http://localhost:8000/api/receipts/upload \
  -F "file=@/path/to/receipt.pdf"
```

### Test 3: Lista Paragonów
```bash
curl http://localhost:8000/api/receipts
```

## Troubleshooting

### Backend nie odpowiada:
1. Sprawdź logi: `tail -f /tmp/backend.log`
2. Sprawdź czy port 8000 jest wolny: `lsof -i :8000`
3. Sprawdź czy Ollama działa: `curl http://localhost:11434/api/tags`

### Frontend nie odpowiada:
1. Sprawdź logi: `tail -f /tmp/frontend.log`
2. Sprawdź czy port 5173 jest wolny: `lsof -i :5173`
3. Sprawdź czy npm dependencies są zainstalowane: `cd frontend && npm install`

### Błędy bazy danych:
1. Sprawdź czy katalog `data/` istnieje
2. Uruchom migracje: `cd backend && source venv/bin/activate && alembic upgrade head`

---

**Data setup:** $(date)
**Status:** ✅ Gotowe do użycia

