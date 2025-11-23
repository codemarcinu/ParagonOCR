# 🚀 Instrukcja uruchomienia ParagonOCR

## Szybki start

### Opcja 1: Tryb interaktywny (dwa terminale)

```bash
./start.sh
```

Skrypt pokaże instrukcje i zapyta czy chcesz uruchomić backend.

### Opcja 2: Uruchomienie w tle (jako daemon)

```bash
./start.sh --background
```

Aplikacja zostanie uruchomiona w tle. Możesz zamknąć terminal.

## Dostępne komendy

```bash
./start.sh              # Tryb interaktywny (domyślny)
./start.sh --background  # Uruchom w tle
./start.sh --stop        # Zatrzymaj aplikację
./start.sh --status      # Sprawdź status
./start.sh --restart     # Restart aplikacji
./start.sh --logs        # Pokaż logi
./start.sh --help        # Pokaż pomoc
```

## Adresy po uruchomieniu

- **Frontend:** http://localhost:8081
- **Backend API:** http://localhost:8000
- **Dokumentacja API:** http://localhost:8000/docs

## Co robi skrypt?

1. ✅ Sprawdza wymagania (Python, venv, zależności)
2. ✅ Sprawdza dostępność portów (8000, 8081)
3. ✅ Sprawdza połączenie z Ollama
4. ✅ Inicjalizuje bazę danych (jeśli potrzeba)
5. ✅ Uruchamia backend i frontend

## Rozwiązywanie problemów

### Port jest zajęty

```bash
./start.sh --stop  # Zatrzymaj działające procesy
```

### Sprawdź status

```bash
./start.sh --status
```

### Zobacz logi

```bash
./start.sh --logs
```

### Ręczne uruchomienie

Jeśli skrypt nie działa, możesz uruchomić ręcznie:

**Terminal 1 - Backend:**
```bash
cd /home/marcin/Projekty/ParagonOCR
source venv/bin/activate
python server.py
```

**Terminal 2 - Frontend:**
```bash
cd /home/marcin/Projekty/ParagonOCR
source venv/bin/activate
python web_app.py
```

## Uwagi

- Port 8080 jest zajęty przez open-webui, więc ParagonOCR używa portu 8081
- W trybie w tle logi są zapisywane w `logs/backend.log` i `logs/frontend.log`
- PID procesów są zapisywane w `.paragon_backend.pid` i `.paragon_frontend.pid`

