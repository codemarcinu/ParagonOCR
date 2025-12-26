#!/bin/bash
set -e

# Ustawiamy sciezke do glownego folderu projektu
BASE_DIR=$(cd "$(dirname "$0")" && pwd)
VENV_DIR="$BASE_DIR/venv"
REQUIREMENTS_PATH="$BASE_DIR/ReceiptParser/requirements.txt"

echo "[INFO] Startujemy z katalogu: $BASE_DIR"

# --- KRYTYCZNA POPRAWKA ---
# Dodajemy folder ReceiptParser do PYTHONPATH
# Dzieki temu import 'from src.main...' w gui.py zadziala,
# bo Python bedzie szukal 'src' takze w $BASE_DIR/ReceiptParser/
export PYTHONPATH="${PYTHONPATH}:$BASE_DIR/ReceiptParser"
echo "[INFO] PYTHONPATH ustawiony."


# 2. Tworzenie/Aktywacja srodowiska wirtualnego
if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Tworze nowe srodowisko wirtualne w $VENV_DIR..."
    python -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
echo "[INFO] Srodowisko wirtualne aktywowane."

# 3. Instalacja zaleznosci Python (z pliku requirements.txt)
# Sprawdzamy, czy glowny pakiet jest juz zainstalowany, zeby nie robic tego za kazdym razem
    echo "[INFO] Instaluje zaleznosci Pythona z $REQUIREMENTS_PATH..."
    ./venv/bin/pip install -r "$REQUIREMENTS_PATH"

# 4. Sprawdzenie serwera Ollama
if curl --output /dev/null --silent --head --fail http://localhost:11434; then
    echo "[OK] Serwer Ollama (http://localhost:11434) odpowiada."
    echo "     Opcja 'Uzyj LLM' bedzie dzialac."
else
    echo "[OSTRZEZENIE] Serwer Ollama (http://localhost:11434) nie odpowiada."
    echo "               Jesli chcesz uzyc LLM, uruchom go: systemctl --user start ollama"
fi

# 5. Uruchomienie aplikacji
echo "[INFO] Uruchamiam aplikacje GUI..."
echo "------------------------------------------------"
"$VENV_DIR/bin/python" "$BASE_DIR/gui.py"
echo "------------------------------------------------"

# 6. Deaktywacja
deactivate
echo "[INFO] Aplikacja zamknieta. Srodowisko zdeaktywowane."