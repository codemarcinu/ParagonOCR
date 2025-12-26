# 🍽️ Aliasy ParagonOCR

Krótkie komendy do uruchamiania serwerów dev z dowolnego miejsca w systemie.

## Instalacja

### Automatyczna (zalecane)
```bash
./scripts/install_aliases.sh
```

### Ręczna
Funkcje fish są już zainstalowane w `~/.config/fish/functions/`. Jeśli nie działają:
```fish
# Załaduj funkcje
source ~/.config/fish/config.fish
# Lub zrestartuj terminal
```

## Dostępne komendy

### `food` - Główna komenda
Uruchamia serwery dev z logami backendu na bieżąco.

```fish
# Uruchom serwery (domyślnie start)
food

# Sprawdź status
food status

# Zatrzymaj serwery
food stop

# Restart serwerów
food restart
```

### `foodstop` - Szybkie zatrzymanie
Zatrzymuje wszystkie serwery dev.

```fish
foodstop
```

### `foodstatus` - Szybki status
Sprawdza status serwerów.

```fish
foodstatus
```

### `foodollama` - Uruchom Ollama
Uruchamia Ollama w tle (wymagane dla AI).

```fish
foodollama
```

## Przykłady użycia

### Podstawowe
```fish
# Z dowolnego miejsca w systemie
cd /tmp
food              # Uruchom serwery
foodstatus        # Sprawdź status
foodstop          # Zatrzymaj
foodollama        # Uruchom Ollama
```

### Pełny workflow
```fish
# Terminal 1: Uruchom wszystko
foodollama        # Najpierw Ollama
food              # Potem serwery

# Terminal 2: Sprawdź status
foodstatus

# Terminal 3: Zatrzymaj wszystko
foodstop
```

## Jak to działa?

Funkcje fish są zdefiniowane w:
- `~/.config/fish/functions/food.fish`
- `~/.config/fish/functions/foodstop.fish`
- `~/.config/fish/functions/foodstatus.fish`
- `~/.config/fish/functions/foodollama.fish`

Każda funkcja automatycznie znajduje projekt ParagonOCR i uruchamia odpowiedni skrypt.

## Rozwiązywanie problemów

### Funkcje nie są dostępne
```fish
# Sprawdź czy funkcje istnieją
ls ~/.config/fish/functions/food*.fish

# Załaduj funkcje ręcznie
source ~/.config/fish/config.fish

# Lub zrestartuj terminal
```

### Błąd: "Nie znaleziono skryptu"
Sprawdź czy projekt ParagonOCR istnieje w:
```
/home/marcin/Projekty/ParagonOCR
```

Jeśli projekt jest w innym miejscu, edytuj funkcje:
```fish
# Edytuj funkcję
nano ~/.config/fish/functions/food.fish
# Zmień ścieżkę project_path
```

### Ollama nie działa
```fish
# Uruchom Ollama
foodollama

# Lub ręcznie
ollama serve

# Sprawdź czy działa
curl http://localhost:11434/api/tags
```

### Funkcje nie działają po restarcie
Upewnij się, że fish ładuje funkcje automatycznie. Sprawdź:
```fish
# Sprawdź konfigurację
cat ~/.config/fish/config.fish
```

## Dodatkowe informacje

- Funkcje działają z dowolnego katalogu
- Automatycznie wybierają skrypt fish lub bash
- Wszystkie logi są widoczne w czasie rzeczywistym
- Ctrl+C zatrzymuje serwery

## Odinstalowanie

Aby usunąć aliasy:
```bash
rm ~/.config/fish/functions/food*.fish
```
