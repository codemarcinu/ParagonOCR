# Użycie skryptów z Fish Shell

## Szybki start

### Opcja 1: Funkcja Fish (zalecane)
Po pierwszym uruchomieniu, funkcja `paragonocr_dev` będzie dostępna w fish:

```fish
# Uruchom serwery z logami
paragonocr_dev

# Sprawdź status
paragonocr_dev status

# Zatrzymaj serwery
paragonocr_dev stop
```

### Opcja 2: Bezpośrednie uruchomienie skryptu Fish
```fish
./scripts/start_dev.fish
./scripts/start_dev.fish status
./scripts/start_dev.fish stop
```

### Opcja 3: Użycie skryptu Bash (działa też w fish)
```fish
bash ./scripts/start_dev.sh
bash ./scripts/start_dev.sh status
bash ./scripts/start_dev.sh stop
```

## Instalacja funkcji Fish

Funkcja `paragonocr_dev` jest automatycznie dostępna jeśli:
- Katalog `.config/fish/functions` istnieje w projekcie
- Lub możesz dodać ręcznie do `~/.config/fish/functions/paragonocr_dev.fish`

Funkcja automatycznie wybiera odpowiedni skrypt (fish lub bash).

## Różnice między wersjami

### Fish Script (`start_dev.fish`)
- ✅ Natywna składnia fish
- ✅ Lepsza integracja z fish shell
- ✅ Funkcja `paragonocr_dev` dostępna globalnie

### Bash Script (`start_dev.sh`)
- ✅ Działa w każdym shellu (bash, zsh, fish)
- ✅ Standardowy shebang `#!/usr/bin/env bash`
- ✅ Może być uruchomiony bezpośrednio lub przez `bash`

## Przykłady użycia

```fish
# Terminal 1: Uruchom serwery
paragonocr_dev

# Terminal 2: Sprawdź status
paragonocr_dev status

# Terminal 3: Zobacz logi frontendu
tail -f frontend.log
```

## Rozwiązywanie problemów

### Funkcja nie jest dostępna
```fish
# Dodaj funkcję ręcznie
cp .config/fish/functions/paragonocr_dev.fish ~/.config/fish/functions/
# Lub uruchom bezpośrednio
./scripts/start_dev.fish
```

### Venv nie aktywuje się
Fish nie używa standardowego `activate`. Skrypt automatycznie ustawia:
- `VIRTUAL_ENV`
- `PATH` (dodaje `venv/bin` na początku)

Jeśli masz problemy, możesz ręcznie:
```fish
set -gx VIRTUAL_ENV /home/marcin/Projekty/ParagonOCR/backend/venv
set -gx PATH $VIRTUAL_ENV/bin $PATH
```

