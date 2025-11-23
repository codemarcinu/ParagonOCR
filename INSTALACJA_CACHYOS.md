# 🐧 Instalacja ParagonOCR na CachyOS

## Wymagania systemowe

- CachyOS (lub Arch Linux)
- Python 3.13+
- Fish Shell 4.2.1+ (domyślny shell)
- Dostęp do internetu

## Instalacja zależności systemowych

```bash
# Zainstaluj brakujące narzędzia (jeśli potrzeba)
sudo pacman -S iproute2 curl python python-pip

# Sprawdź czy ss jest dostępny (część iproute2)
which ss
```

## Konfiguracja dla Fish Shell

### Opcja 1: Dodaj funkcję do Fish

Dodaj do `~/.config/fish/config.fish`:

```fish
# ParagonOCR
source /home/marcin/Projekty/ParagonOCR/start.fish
```

Następnie zrestartuj fish lub wykonaj:
```fish
source ~/.config/fish/config.fish
```

### Opcja 2: Użyj bezpośrednio bash

Skrypty działają z bash (dostępny w systemie):
```bash
./start.sh --background
```

## Uruchomienie

### Metoda 1: Przez Fish (jeśli skonfigurowane)

```fish
paragon start      # Uruchom w tle
paragon status     # Sprawdź status
paragon manager    # GUI managera
```

### Metoda 2: Bezpośrednio przez bash

```bash
./start.sh --background
./start.sh --status
python manager.py  # GUI managera
```

## Dostosowania dla CachyOS

### Zastąpione narzędzia

- `lsof` → `ss` (iproute2) - sprawdzanie portów
- Wszystkie skrypty działają z bash (dostępny w systemie)

### Porty

- Manager: 8082
- Frontend: 8081
- Backend: 8000
- Open-WebUI: 8080 (już zajęty)

## Rozwiązywanie problemów

### Problem: "lsof: command not found"

**Rozwiązanie:** Skrypty zostały dostosowane do użycia `ss` zamiast `lsof`. `ss` jest częścią `iproute2` (domyślnie w CachyOS).

### Problem: Skrypty nie działają w Fish

**Rozwiązanie:** Skrypty są napisane w bash. Uruchamiaj je przez:
```bash
bash start.sh --background
```

Lub użyj wrappera fish (`start.fish`).

### Problem: Brak uprawnień

**Rozwiązanie:** Upewnij się, że skrypty mają uprawnienia do wykonania:
```bash
chmod +x start.sh manager.py
```

## Sprawdzenie instalacji

```bash
# Sprawdź dostępność narzędzi
which python3 ss curl ollama

# Sprawdź status aplikacji
./start.sh --status

# Uruchom GUI managera
python manager.py
```

Następnie otwórz: http://localhost:8082


