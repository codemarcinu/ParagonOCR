#!/usr/bin/env bash
# ParagonOCR Web Edition - Development server with live backend logs
# Uruchamia backend i frontend, pokazuje logi backendu na bieżąco w konsoli

set -e

# Kolory
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Ścieżki
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_LOG="$PROJECT_ROOT/backend.log"
FRONTEND_LOG="$PROJECT_ROOT/frontend.log"

# PID pliki
BACKEND_PID_FILE="$PROJECT_ROOT/.backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/.frontend.pid"

# Funkcja sprawdzająca status
check_status() {
    echo ""
    echo "${CYAN}=== Status serwerów ===${NC}"
    
    # Sprawdź backend
    if [ -f "$BACKEND_PID_FILE" ]; then
        BACKEND_PID=$(cat "$BACKEND_PID_FILE")
        if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
            echo "${GREEN}✓ Backend:${NC} Działa (PID: $BACKEND_PID)"
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                echo "  ${GREEN}✓ API dostępne${NC} na http://localhost:8000"
            else
                echo "  ${YELLOW}⚠ API nie odpowiada${NC}"
            fi
        else
            echo "${RED}✗ Backend:${NC} Nie działa"
            rm -f "$BACKEND_PID_FILE"
        fi
    else
        echo "${RED}✗ Backend:${NC} Nie uruchomiony"
    fi
    
    # Sprawdź frontend
    if [ -f "$FRONTEND_PID_FILE" ]; then
        FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
        if ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
            echo "${GREEN}✓ Frontend:${NC} Działa (PID: $FRONTEND_PID)"
            if curl -s http://localhost:5173 > /dev/null 2>&1; then
                echo "  ${GREEN}✓ Frontend dostępny${NC} na http://localhost:5173"
            else
                echo "  ${YELLOW}⚠ Frontend nie odpowiada${NC}"
            fi
        else
            echo "${RED}✗ Frontend:${NC} Nie działa"
            rm -f "$FRONTEND_PID_FILE"
        fi
    else
        echo "${RED}✗ Frontend:${NC} Nie uruchomiony"
    fi
    
    # Sprawdź Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "${GREEN}✓ Ollama:${NC} Działa"
    else
        echo "${YELLOW}⚠ Ollama:${NC} Nie działa (wymagane dla AI)"
    fi
    
    echo ""
}

# Funkcja zatrzymująca serwery
stop_servers() {
    echo ""
    echo "${YELLOW}🛑 Zatrzymywanie serwerów...${NC}"
    
    # Zatrzymaj backend
    if [ -f "$BACKEND_PID_FILE" ]; then
        BACKEND_PID=$(cat "$BACKEND_PID_FILE")
        if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
            echo "Zatrzymywanie backendu (PID: $BACKEND_PID)..."
            kill "$BACKEND_PID" 2>/dev/null || true
            sleep 1
            kill -9 "$BACKEND_PID" 2>/dev/null || true
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    
    # Zatrzymaj frontend
    if [ -f "$FRONTEND_PID_FILE" ]; then
        FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
        if ps -p "$FRONTEND_PID" > /dev/null 2>&1; then
            echo "Zatrzymywanie frontendu (PID: $FRONTEND_PID)..."
            kill "$FRONTEND_PID" 2>/dev/null || true
            sleep 1
            kill -9 "$FRONTEND_PID" 2>/dev/null || true
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    # Zabij wszystkie procesy uvicorn i vite związane z projektem
    pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
    pkill -f "vite.*$FRONTEND_DIR" 2>/dev/null || true
    
    echo "${GREEN}✓ Serwery zatrzymane${NC}"
    echo ""
    exit 0
}

# Funkcja czyszcząca stare procesy
cleanup_old_processes() {
    # Sprawdź czy porty są zajęte
    if lsof -ti:8000 > /dev/null 2>&1; then
        echo "${YELLOW}⚠ Port 8000 jest zajęty. Próbuję zwolnić...${NC}"
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    if lsof -ti:5173 > /dev/null 2>&1; then
        echo "${YELLOW}⚠ Port 5173 jest zajęty. Próbuję zwolnić...${NC}"
        lsof -ti:5173 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Funkcja uruchamiająca backend
start_backend() {
    echo "${BLUE}🔧 Uruchamianie backendu...${NC}"
    
    cd "$BACKEND_DIR"
    
    # Sprawdź czy venv istnieje
    if [ ! -d "venv" ]; then
        echo "${RED}✗ Błąd: venv nie znaleziony w $BACKEND_DIR${NC}"
        exit 1
    fi
    
    # Aktywuj venv
    source venv/bin/activate
    
    # Sprawdź zależności
    if ! python3 -c "import uvicorn" 2>/dev/null; then
        echo "${YELLOW}⚠ Instalowanie zależności backendu...${NC}"
        pip install -q -r requirements.txt
    fi
    
    # Ustaw PYTHONPATH
    export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
    
    # Uruchom backend z logowaniem do pliku i konsoli
    echo "${CYAN}Backend loguje do: $BACKEND_LOG${NC}"
    echo "${CYAN}Backend dostępny na: http://localhost:8000${NC}"
    echo "${CYAN}API Docs: http://localhost:8000/docs${NC}"
    echo ""
    
    # Uruchom uvicorn w tle z logowaniem do pliku
    # Używamy named pipe lub uruchamiamy w tle i pokazujemy logi przez tail
    uvicorn app.main:app \
        --reload \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info \
        > "$BACKEND_LOG" 2>&1 &
    
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
    
    # Poczekaj na start
    echo "Czekam na uruchomienie backendu..."
    for i in {1..10}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo "${GREEN}✓ Backend uruchomiony (PID: $BACKEND_PID)${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo "${RED}✗ Backend nie odpowiada po 10 sekundach${NC}"
    return 1
}

# Funkcja uruchamiająca frontend
start_frontend() {
    echo "${BLUE}🎨 Uruchamianie frontendu...${NC}"
    
    cd "$FRONTEND_DIR"
    
    # Sprawdź czy node_modules istnieje
    if [ ! -d "node_modules" ]; then
        echo "${YELLOW}⚠ Instalowanie zależności frontendu...${NC}"
        npm install
    fi
    
    # Uruchom frontend w tle
    echo "${CYAN}Frontend loguje do: $FRONTEND_LOG${NC}"
    echo "${CYAN}Frontend dostępny na: http://localhost:5173${NC}"
    echo ""
    
    npm run dev > "$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE"
    
    # Poczekaj na start
    echo "Czekam na uruchomienie frontendu..."
    for i in {1..15}; do
        if curl -s http://localhost:5173 > /dev/null 2>&1; then
            echo "${GREEN}✓ Frontend uruchomiony (PID: $FRONTEND_PID)${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo "${YELLOW}⚠ Frontend może jeszcze się uruchamiać...${NC}"
    return 0
}

# Obsługa sygnałów
trap stop_servers SIGINT SIGTERM

# Główna logika
main() {
    # Sprawdź argumenty
    case "${1:-start}" in
        start)
            echo "${GREEN}🚀 ParagonOCR Web Edition - Development Server${NC}"
            echo ""
            
            # Sprawdź Ollama
            if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo "${YELLOW}⚠ Ostrzeżenie: Ollama nie działa${NC}"
                echo "   Uruchom: ${BLUE}ollama serve${NC}"
                echo ""
            fi
            
            # Wyczyść stare procesy
            cleanup_old_processes
            
            # Uruchom backend
            start_backend
            
            # Poczekaj chwilę
            sleep 1
            
            # Uruchom frontend (w tle)
            start_frontend
            
            echo ""
            echo "${GREEN}✅ Serwery uruchomione!${NC}"
            echo ""
            echo "${CYAN}=== Dostęp ===${NC}"
            echo "  Frontend: ${GREEN}http://localhost:5173${NC}"
            echo "  Backend:  ${GREEN}http://localhost:8000${NC}"
            echo "  API Docs: ${GREEN}http://localhost:8000/docs${NC}"
            echo ""
            echo "${CYAN}=== Logi ===${NC}"
            echo "  Backend:  ${BLUE}tail -f $BACKEND_LOG${NC} (widoczne poniżej)"
            echo "  Frontend: ${BLUE}tail -f $FRONTEND_LOG${NC}"
            echo ""
            echo "${CYAN}=== Komendy ===${NC}"
            echo "  Status:   ${BLUE}$0 status${NC} (w osobnym terminalu)"
            echo "  Stop:     ${BLUE}$0 stop${NC} lub Ctrl+C"
            echo ""
            echo "${YELLOW}Naciśnij Ctrl+C aby zatrzymać serwery${NC}"
            echo ""
            echo "${CYAN}════════════════════════════════════════════════════${NC}"
            echo "${CYAN}  LOGI BACKENDU (na bieżąco)${NC}"
            echo "${CYAN}════════════════════════════════════════════════════${NC}"
            echo ""
            
            # Pokaż ostatnie logi i kontynuuj pokazywanie na bieżąco
            if [ -f "$BACKEND_LOG" ]; then
                # Pokaż ostatnie 20 linii
                tail -n 20 "$BACKEND_LOG" 2>/dev/null
                echo ""
                echo "${CYAN}--- Nowe logi (Ctrl+C aby zatrzymać) ---${NC}"
                echo ""
            fi
            
            # Pokaż logi backendu na bieżąco (to zablokuje wykonanie)
            tail -f "$BACKEND_LOG" 2>/dev/null || {
                # Jeśli tail nie działa, pokaż ostatnie logi
                echo "Wyświetlanie ostatnich logów backendu..."
                tail -n 50 "$BACKEND_LOG" 2>/dev/null || echo "Brak logów"
                # Czekaj w pętli
                while true; do
                    sleep 1
                    if ! ps -p "$(cat "$BACKEND_PID_FILE" 2>/dev/null)" > /dev/null 2>&1; then
                        break
                    fi
                done
            }
            ;;
        status)
            check_status
            ;;
        stop)
            stop_servers
            ;;
        restart)
            stop_servers
            sleep 2
            main start
            ;;
        *)
            echo "Użycie: $0 {start|status|stop|restart}"
            echo ""
            echo "  start   - Uruchom backend i frontend (domyślnie)"
            echo "  status  - Sprawdź status serwerów"
            echo "  stop    - Zatrzymaj serwery"
            echo "  restart - Zatrzymaj i uruchom ponownie"
            exit 1
            ;;
    esac
}

# Uruchom główną funkcję
main "$@"

