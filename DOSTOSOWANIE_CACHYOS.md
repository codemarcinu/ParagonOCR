# ✅ Dostosowanie skryptów do CachyOS

## Wykonane zmiany

### 1. Zastąpienie `lsof` przez `ss`
- **Problem:** `lsof` nie jest domyślnie zainstalowany w CachyOS
- **Rozwiązanie:** Wszystkie użycia `lsof` zostały zastąpione przez `ss` (iproute2)
- **Pliki zmienione:**
  - `start.sh` - sprawdzanie portów
  - `manager.py` - sprawdzanie portów

### 2. Wrapper dla Fish Shell
- **Utworzony:** `start.fish` - funkcja `paragon` dla Fish
- **Użycie:** `paragon start`, `paragon stop`, `paragon manager`, etc.

### 3. Dokumentacja
- **Utworzony:** `INSTALACJA_CACHYOS.md` - instrukcje dla CachyOS
- **Utworzony:** `DOSTOSOWANIE_CACHYOS.md` - ten plik

## Jak używać

### Metoda 1: Przez Fish (zalecane)

Najpierw dodaj do `~/.config/fish/config.fish`:
```fish
source /home/marcin/Projekty/ParagonOCR/start.fish
```

Następnie:
```fish
paragon start      # Uruchom w tle
paragon status     # Sprawdź status
paragon manager    # GUI managera
paragon stop       # Zatrzymaj
```

### Metoda 2: Bezpośrednio przez bash

```bash
./start.sh --background
./start.sh --status
python manager.py
```

## Sprawdzone narzędzia

✅ **Dostępne:**
- `python3` - Python 3.13.7
- `ss` - iproute2 (sprawdzanie portów)
- `curl` - sprawdzanie Ollama
- `ollama` - lokalny serwer AI
- `fish` - Fish Shell 4.2.1
- `bash` - Bash (dla skryptów)

❌ **Niedostępne (zastąpione):**
- `lsof` → zastąpione przez `ss`

## Testy

Wszystkie skrypty zostały przetestowane:
- ✅ `start.sh --status` - działa
- ✅ `start.fish` - funkcja działa
- ✅ `manager.py` - sprawdzanie portów działa (z venv)

## Porty

- Manager: **8082**
- Frontend: **8081**
- Backend: **8000**
- Open-WebUI: **8080** (już zajęty)

## Następne kroki

1. Dodaj funkcję fish do konfiguracji:
   ```fish
   source /home/marcin/Projekty/ParagonOCR/start.fish
   ```

2. Uruchom aplikację:
   ```fish
   paragon start
   ```

3. Otwórz managera:
   ```fish
   paragon manager
   ```
   Lub bezpośrednio: http://localhost:8082

## Uwagi

- Wszystkie skrypty działają z bash (dostępny w systemie)
- Fish wrapper wywołuje bash skrypty
- `ss` jest częścią iproute2 (domyślnie w CachyOS)
- Manager wymaga aktywnego venv (automatycznie w `paragon manager`)


