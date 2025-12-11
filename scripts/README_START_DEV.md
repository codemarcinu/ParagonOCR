# Skrypt start_dev.sh

Skrypt do uruchamiania i monitorowania backendu oraz frontendu z pełnymi logami backendu na bieżąco w konsoli.

## Użycie

### Uruchomienie serwerów (z logami backendu)
```bash
./scripts/start_dev.sh
# lub
./scripts/start_dev.sh start
```

Skrypt:
- ✅ Sprawdzi czy Ollama działa
- ✅ Uruchomi backend (port 8000) z logowaniem do `backend.log`
- ✅ Uruchomi frontend (port 5173) w tle
- ✅ Wyświetli logi backendu na bieżąco w konsoli
- ✅ Zatrzyma serwery po naciśnięciu Ctrl+C

### Sprawdzenie statusu
```bash
./scripts/start_dev.sh status
```

Sprawdzi:
- Czy backend działa i odpowiada na API
- Czy frontend działa
- Czy Ollama jest dostępny

### Zatrzymanie serwerów
```bash
./scripts/start_dev.sh stop
```

### Restart serwerów
```bash
./scripts/start_dev.sh restart
```

## Funkcje

### Logi backendu na bieżąco
Główna funkcja skryptu - po uruchomieniu widzisz wszystkie logi backendu w czasie rzeczywistym:
- Logi uvicorn
- Logi aplikacji (INFO, ERROR, DEBUG)
- Wszystkie requesty HTTP
- Błędy i wyjątki

### Automatyczne zarządzanie
- Automatyczne zwalnianie zajętych portów
- Sprawdzanie zależności
- Instalacja brakujących pakietów (jeśli potrzeba)
- Zapisywanie PID procesów dla łatwego zatrzymania

### Pliki logów
- **Backend**: `backend.log` - wszystkie logi backendu
- **Frontend**: `frontend.log` - logi frontendu (vite)

## Przykładowe użycie

```bash
# Terminal 1: Uruchom serwery z logami
./scripts/start_dev.sh

# Terminal 2: Sprawdź status
./scripts/start_dev.sh status

# Terminal 3: Zobacz logi frontendu
tail -f frontend.log
```

## Wymagania

- Backend: Python 3.x, venv w `backend/venv`
- Frontend: Node.js, npm, zależności w `frontend/node_modules`
- Ollama: powinien działać na `http://localhost:11434` (opcjonalne, ale wymagane dla AI)

## Rozwiązywanie problemów

### Port zajęty
Skrypt automatycznie próbuje zwolnić porty 8000 i 5173. Jeśli to nie działa:
```bash
# Sprawdź co używa portu
lsof -i :8000
lsof -i :5173

# Zatrzymaj procesy ręcznie
./scripts/start_dev.sh stop
```

### Backend nie startuje
```bash
# Sprawdź logi
cat backend.log

# Sprawdź czy venv jest poprawny
cd backend && source venv/bin/activate && python --version
```

### Frontend nie startuje
```bash
# Sprawdź logi
cat frontend.log

# Zainstaluj zależności
cd frontend && npm install
```

