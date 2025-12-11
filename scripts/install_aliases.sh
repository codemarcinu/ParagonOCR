#!/usr/bin/env bash
# Instalacja aliasów/funkcji fish do uruchamiania ParagonOCR z dowolnego miejsca

set -e

echo "🔧 Instalowanie aliasów ParagonOCR dla Fish Shell..."
echo ""

# Kolory
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Ścieżki
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FISH_FUNCTIONS_DIR="$HOME/.config/fish/functions"

# Utwórz katalog funkcji fish jeśli nie istnieje
mkdir -p "$FISH_FUNCTIONS_DIR"

# Funkcje do zainstalowania
FUNCTIONS=(
    "food"
    "foodstop"
    "foodstatus"
)

echo "📁 Katalog funkcji: $FISH_FUNCTIONS_DIR"
echo "📁 Projekt: $PROJECT_ROOT"
echo ""

# Zainstaluj każdą funkcję
for func in "${FUNCTIONS[@]}"; do
    source_file="$PROJECT_ROOT/.config/fish/functions/${func}.fish"
    target_file="$FISH_FUNCTIONS_DIR/${func}.fish"
    
    if [ -f "$source_file" ]; then
        # Zastąp ścieżkę projektu w funkcji
        sed "s|/home/marcin/Projekty/ParagonOCR|$PROJECT_ROOT|g" "$source_file" > "$target_file"
        chmod +x "$target_file"
        echo "${GREEN}✓${NC} Zainstalowano: ${BLUE}$func${NC}"
    else
        echo "${YELLOW}⚠${NC} Nie znaleziono: $source_file"
    fi
done

echo ""
echo "${GREEN}✅ Instalacja zakończona!${NC}"
echo ""
echo "Dostępne komendy:"
echo "  ${BLUE}food${NC}        - Uruchom serwery dev (lub: food start/status/stop/restart)"
echo "  ${BLUE}foodstop${NC}    - Zatrzymaj serwery dev"
echo "  ${BLUE}foodstatus${NC}  - Sprawdź status serwerów"
echo ""
echo "Uruchom nową sesję fish lub wykonaj: ${BLUE}source ~/.config/fish/config.fish${NC}"
echo ""

