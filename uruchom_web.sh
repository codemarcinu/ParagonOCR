#!/bin/bash
# ============================================================================
# ParagonOCR - Skrypt uruchomieniowy (przekierowanie do start.sh)
# ============================================================================
# 
# Ten skrypt jest zachowany dla kompatybilności wstecznej.
# Użyj nowego skryptu: ./start.sh
# ============================================================================

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
NEW_SCRIPT="$SCRIPT_DIR/start.sh"

if [ -f "$NEW_SCRIPT" ]; then
    echo "Przekierowuję do nowego skryptu: ./start.sh"
    echo ""
    exec "$NEW_SCRIPT" "$@"
else
    echo "❌ Nie znaleziono skryptu start.sh"
    echo "Upewnij się, że jesteś w katalogu głównym projektu"
    exit 1
fi

