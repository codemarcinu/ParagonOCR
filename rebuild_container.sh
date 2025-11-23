#!/bin/bash
# Skrypt do przebudowy kontenera ParagonOCR z nowym kodem
# Użycie: ./rebuild_container.sh

set -e  # Zatrzymaj przy błędzie

echo "🛑 Zatrzymywanie i usuwanie starych kontenerów..."
docker-compose down

echo "🧹 Czyszczenie starych obrazów (opcjonalne, ale zalecane)..."
docker-compose build --no-cache

echo "🚀 Uruchamianie kontenerów z nowym kodem..."
docker-compose up -d

echo "📋 Sprawdzanie logów (naciśnij Ctrl+C aby wyjść)..."
docker-compose logs -f paragon-web

