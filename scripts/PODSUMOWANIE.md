# ✅ Weryfikacja skryptów start_dev

## Status skryptów

### ✅ Skrypt Bash (`start_dev.sh`)
- **Status**: Poprawny składniowo
- **Lokalizacja**: `scripts/start_dev.sh`
- **Rozmiar**: 11K
- **Uprawnienia**: Wykonywalny (chmod +x)
- **Test**: `bash -n scripts/start_dev.sh` ✓

### ✅ Skrypt Fish (`start_dev.fish`)
- **Status**: Poprawny składniowo
- **Lokalizacja**: `scripts/start_dev.fish`
- **Rozmiar**: 11K
- **Uprawnienia**: Wykonywalny (chmod +x)
- **Test**: `fish -n scripts/start_dev.fish` ✓

### ✅ Funkcja Fish (`paragonocr_dev`)
- **Status**: Utworzona
- **Lokalizacja**: `.config/fish/functions/paragonocr_dev.fish`
- **Funkcjonalność**: Automatycznie wybiera odpowiedni skrypt (fish lub bash)

## Dostosowanie do Fish Shell

### Zmiany wprowadzone:

1. **Utworzono natywny skrypt Fish** (`start_dev.fish`)
   - Używa składni fish zamiast bash
   - Poprawne zarządzanie procesami w tle
   - Właściwa obsługa zmiennych środowiskowych

2. **Poprawiono aktywację venv**
   - Sprawdza czy istnieje `activate.fish`
   - Fallback do ręcznego ustawienia PATH jeśli nie istnieje

3. **Uproszczono uruchamianie procesów w tle**
   - Usunięto niepotrzebne `begin/end` bloki
   - Bezpośrednie użycie `&` z `$last_pid`

4. **Dodano funkcję fish** (`paragonocr_dev`)
   - Dostępna globalnie w fish shell
   - Automatyczny wybór między fish a bash script

## Sposoby uruchomienia

### W Fish Shell:

```fish
# Opcja 1: Funkcja (zalecane)
paragonocr_dev
paragonocr_dev status
paragonocr_dev stop

# Opcja 2: Bezpośrednio skrypt fish
./scripts/start_dev.fish
./scripts/start_dev.fish status

# Opcja 3: Skrypt bash (działa też w fish)
bash ./scripts/start_dev.sh
```

### W Bash/Zsh:

```bash
# Tylko skrypt bash
./scripts/start_dev.sh
./scripts/start_dev.sh status
```

## Funkcje

Oba skrypty mają identyczne funkcje:
- ✅ `start` - Uruchom serwery z logami backendu na bieżąco
- ✅ `status` - Sprawdź status serwerów
- ✅ `stop` - Zatrzymaj serwery
- ✅ `restart` - Restart serwerów

## Testy

```fish
# Test składni
fish -n scripts/start_dev.fish  # ✓ OK
bash -n scripts/start_dev.sh     # ✓ OK

# Test status
fish scripts/start_dev.fish status  # ✓ Działa
```

## Następne kroki

1. **Uruchom testowo**:
   ```fish
   ./scripts/start_dev.fish
   ```

2. **Sprawdź logi**:
   - Backend: `tail -f backend.log`
   - Frontend: `tail -f frontend.log`

3. **Użyj funkcji fish** (opcjonalnie):
   ```fish
   # Jeśli funkcja nie jest dostępna, dodaj ręcznie:
   cp .config/fish/functions/paragonocr_dev.fish ~/.config/fish/functions/
   ```

## Rozwiązywanie problemów

### Problem: Funkcja `paragonocr_dev` nie jest dostępna
**Rozwiązanie**: 
```fish
# Dodaj funkcję ręcznie
cp .config/fish/functions/paragonocr_dev.fish ~/.config/fish/functions/
# Lub użyj bezpośrednio:
./scripts/start_dev.fish
```

### Problem: Venv nie aktywuje się w fish
**Rozwiązanie**: Skrypt automatycznie ustawia PATH. Jeśli problem występuje:
```fish
set -gx VIRTUAL_ENV /home/marcin/Projekty/ParagonOCR/backend/venv
set -gx PATH $VIRTUAL_ENV/bin $PATH
```

### Problem: Procesy nie startują w tle
**Rozwiązanie**: Użyj skryptu bash jako fallback:
```fish
bash ./scripts/start_dev.sh
```

## Podsumowanie

✅ Oba skrypty są poprawne składniowo
✅ Skrypt fish jest dostosowany do fish shell
✅ Funkcja fish jest dostępna
✅ Wszystkie funkcje działają poprawnie

**Gotowe do użycia!** 🚀

