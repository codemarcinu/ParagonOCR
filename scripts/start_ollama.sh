#!/usr/bin/env bash
# Uruchomienie Ollama w tle

set -e

echo "🔧 Uruchamianie Ollama..."

# Sprawdź czy Ollama jest zainstalowane
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama nie jest zainstalowane"
    echo "   Zainstaluj z: https://ollama.ai"
    exit 1
fi

# Sprawdź czy już działa
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama już działa"
    exit 0
fi

# Uruchom Ollama w tle
echo "🚀 Uruchamianie Ollama w tle..."
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!

echo "Ollama PID: $OLLAMA_PID"
echo "Logi: tail -f /tmp/ollama.log"

# Poczekaj na start
echo "Czekam na uruchomienie Ollama..."
for i in {1..10}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama uruchomione!"
        exit 0
    fi
    sleep 1
done

echo "⚠️  Ollama może jeszcze się uruchamiać..."
echo "   Sprawdź logi: tail -f /tmp/ollama.log"

