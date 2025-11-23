#!/bin/bash
# Skrypt do uruchomienia aplikacji webowej ParagonOCR

set -e

BASE_DIR=$(cd "$(dirname "$0")" && pwd)
VENV_DIR="$BASE_DIR/venv"

echo "=========================================="
echo "🚀 Uruchamianie ParagonOCR Web App"
echo "=========================================="

# Aktywuj środowisko wirtualne
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Brak środowiska wirtualnego! Uruchom najpierw instalację zależności."
    exit 1
fi

source "$VENV_DIR/bin/activate"

# Ustaw PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$BASE_DIR/ReceiptParser"

# Sprawdź czy Ollama działa
if curl --output /dev/null --silent --head --fail http://localhost:11434; then
    echo "✅ Ollama działa na http://localhost:11434"
else
    echo "⚠️  Ollama nie odpowiada na http://localhost:11434"
    echo "   Upewnij się, że Ollama jest uruchomione: docker ps | grep ollama"
fi

echo ""
echo "=========================================="
echo "📋 Instrukcja uruchomienia:"
echo "=========================================="
echo ""
echo "Otwórz DWA terminale:"
echo ""
echo "Terminal 1 - Backend (FastAPI):"
echo "  cd $BASE_DIR"
echo "  source venv/bin/activate"
echo "  python server.py"
echo ""
echo "Terminal 2 - Frontend (NiceGUI):"
echo "  cd $BASE_DIR"
echo "  source venv/bin/activate"
echo "  python web_app.py"
echo ""
echo "Następnie otwórz w przeglądarce:"
echo "  🌐 Frontend: http://localhost:8080"
echo "  📡 Backend API: http://localhost:8000"
echo "  📚 Dokumentacja API: http://localhost:8000/docs"
echo ""
echo "=========================================="
echo ""
read -p "Czy chcesz uruchomić backend teraz? (t/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Tt]$ ]]; then
    echo "Uruchamiam backend..."
    python server.py
fi

