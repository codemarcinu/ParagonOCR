#!/bin/bash
# ============================================================================
# ParagonOCR - Skrypt uruchomieniowy aplikacji webowej
# ============================================================================
# 
# Użycie:
#   ./start.sh              - Uruchom w trybie interaktywnym (dwa terminale)
#   ./start.sh --background - Uruchom w tle (jako daemon)
#   ./start.sh --stop       - Zatrzymaj działające procesy
#   ./start.sh --status     - Sprawdź status aplikacji
#   ./start.sh --restart    - Restart aplikacji
#   ./start.sh --logs       - Pokaż logi
# ============================================================================

set -euo pipefail

# Kolory dla lepszej czytelności
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ścieżki
BASE_DIR=$(cd "$(dirname "$0")" && pwd)
VENV_DIR="$BASE_DIR/venv"
REQUIREMENTS_PATH="$BASE_DIR/ReceiptParser/requirements.txt"
PID_BACKEND="$BASE_DIR/.paragon_backend.pid"
PID_FRONTEND="$BASE_DIR/.paragon_frontend.pid"
LOG_BACKEND="$BASE_DIR/logs/backend.log"
LOG_FRONTEND="$BASE_DIR/logs/frontend.log"

# Porty
BACKEND_PORT=8000
FRONTEND_PORT=8081
OLLAMA_PORT=11434

# ============================================================================
# Funkcje pomocnicze
# ============================================================================

print_header() {
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}==========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ============================================================================
# Sprawdzanie zależności
# ============================================================================

check_requirements() {
    print_header "Sprawdzanie wymagań"
    
    # Sprawdź Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 nie jest zainstalowany!"
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version)
    print_success "Python: $PYTHON_VERSION"
    
    # Sprawdź venv
    if [ ! -d "$VENV_DIR" ]; then
        print_warning "Brak środowiska wirtualnego. Tworzę..."
        python3 -m venv "$VENV_DIR"
        print_success "Środowisko wirtualne utworzone"
    fi
    
    # Aktywuj venv
    source "$VENV_DIR/bin/activate"
    
    # Sprawdź czy wymagane moduły są zainstalowane
    if ! python -c "import fastapi, nicegui, uvicorn" 2>/dev/null; then
        print_warning "Brakujące zależności. Instaluję..."
        pip install -q -r "$REQUIREMENTS_PATH"
        print_success "Zależności zainstalowane"
    else
        print_success "Wszystkie zależności są zainstalowane"
    fi
    
    # Ustaw PYTHONPATH
    export PYTHONPATH="${PYTHONPATH}:$BASE_DIR/ReceiptParser"
    
    # Sprawdź bazę danych
    if [ ! -f "$BASE_DIR/ReceiptParser/data/receipts.db" ]; then
        print_warning "Baza danych nie istnieje. Inicjalizuję..."
        python -m ReceiptParser.src.main init-db 2>/dev/null || true
        print_success "Baza danych zainicjalizowana"
    fi
    
    echo ""
}

# ============================================================================
# Sprawdzanie portów
# ============================================================================

check_ports() {
    print_header "Sprawdzanie portów"
    
    # Sprawdź port backendu
    if lsof -i :$BACKEND_PORT 2>/dev/null | grep -q LISTEN; then
        print_error "Port $BACKEND_PORT jest zajęty!"
        print_info "Uruchom: ./start.sh --stop aby zatrzymać działające procesy"
        return 1
    else
        print_success "Port $BACKEND_PORT (backend) jest wolny"
    fi
    
    # Sprawdź port frontendu
    if lsof -i :$FRONTEND_PORT 2>/dev/null | grep -q LISTEN; then
        print_error "Port $FRONTEND_PORT jest zajęty!"
        print_info "Uruchom: ./start.sh --stop aby zatrzymać działające procesy"
        return 1
    else
        print_success "Port $FRONTEND_PORT (frontend) jest wolny"
    fi
    
    echo ""
    return 0
}

# ============================================================================
# Sprawdzanie Ollama
# ============================================================================

check_ollama() {
    print_header "Sprawdzanie Ollama"
    
    if curl --output /dev/null --silent --head --fail http://localhost:$OLLAMA_PORT; then
        print_success "Ollama działa na http://localhost:$OLLAMA_PORT"
        
        # Sprawdź modele
        if command -v ollama &> /dev/null; then
            MODELS=$(ollama list 2>/dev/null | grep -E "(llava|bielik)" | wc -l || echo "0")
            if [ "$MODELS" -gt 0 ]; then
                print_success "Wymagane modele są dostępne"
            else
                print_warning "Brakuje niektórych modeli. Sprawdź: ollama list"
            fi
        fi
    else
        print_warning "Ollama nie odpowiada na http://localhost:$OLLAMA_PORT"
        print_info "Upewnij się, że Ollama jest uruchomione: docker ps | grep ollama"
    fi
    
    echo ""
}

# ============================================================================
# Uruchamianie procesów
# ============================================================================

start_backend() {
    local mode=$1
    print_info "Uruchamiam backend (FastAPI) na porcie $BACKEND_PORT..."
    
    cd "$BASE_DIR"
    source "$VENV_DIR/bin/activate"
    export PYTHONPATH="${PYTHONPATH}:$BASE_DIR/ReceiptParser"
    
    if [ "$mode" = "background" ]; then
        # Utwórz katalog na logi
        mkdir -p "$BASE_DIR/logs"
        
        # Uruchom w tle
        nohup python server.py > "$LOG_BACKEND" 2>&1 &
        BACKEND_PID=$!
        echo $BACKEND_PID > "$PID_BACKEND"
        print_success "Backend uruchomiony w tle (PID: $BACKEND_PID)"
        print_info "Logi: tail -f $LOG_BACKEND"
    else
        # Uruchom na pierwszym planie
        python server.py
    fi
}

start_frontend() {
    local mode=$1
    print_info "Uruchamiam frontend (NiceGUI) na porcie $FRONTEND_PORT..."
    
    cd "$BASE_DIR"
    source "$VENV_DIR/bin/activate"
    export PYTHONPATH="${PYTHONPATH}:$BASE_DIR/ReceiptParser"
    
    if [ "$mode" = "background" ]; then
        # Utwórz katalog na logi
        mkdir -p "$BASE_DIR/logs"
        
        # Uruchom w tle
        nohup python web_app.py > "$LOG_FRONTEND" 2>&1 &
        FRONTEND_PID=$!
        echo $FRONTEND_PID > "$PID_FRONTEND"
        print_success "Frontend uruchomiony w tle (PID: $FRONTEND_PID)"
        print_info "Logi: tail -f $LOG_FRONTEND"
    else
        # Uruchom na pierwszym planie
        python web_app.py
    fi
}

# ============================================================================
# Zatrzymywanie procesów
# ============================================================================

stop_processes() {
    print_header "Zatrzymywanie procesów"
    
    local stopped=0
    
    # Zatrzymaj backend
    if [ -f "$PID_BACKEND" ]; then
        BACKEND_PID=$(cat "$PID_BACKEND")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            kill "$BACKEND_PID" 2>/dev/null || true
            print_success "Backend zatrzymany (PID: $BACKEND_PID)"
            stopped=$((stopped + 1))
        else
            print_warning "Backend nie działa (stary PID: $BACKEND_PID)"
        fi
        rm -f "$PID_BACKEND"
    fi
    
    # Zatrzymaj frontend
    if [ -f "$PID_FRONTEND" ]; then
        FRONTEND_PID=$(cat "$PID_FRONTEND")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            kill "$FRONTEND_PID" 2>/dev/null || true
            print_success "Frontend zatrzymany (PID: $FRONTEND_PID)"
            stopped=$((stopped + 1))
        else
            print_warning "Frontend nie działa (stary PID: $FRONTEND_PID)"
        fi
        rm -f "$PID_FRONTEND"
    fi
    
    # Zatrzymaj procesy na portach (na wypadek gdyby PID nie działały)
    for port in $BACKEND_PORT $FRONTEND_PORT; do
        PID=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$PID" ]; then
            kill "$PID" 2>/dev/null || true
            print_info "Proces na porcie $port zatrzymany"
            stopped=$((stopped + 1))
        fi
    done
    
    if [ $stopped -eq 0 ]; then
        print_info "Brak działających procesów do zatrzymania"
    fi
    
    echo ""
}

# ============================================================================
# Status aplikacji
# ============================================================================

check_status() {
    print_header "Status aplikacji"
    
    # Backend
    if [ -f "$PID_BACKEND" ]; then
        BACKEND_PID=$(cat "$PID_BACKEND")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            print_success "Backend działa (PID: $BACKEND_PID)"
            if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
                print_success "Backend odpowiada na http://localhost:$BACKEND_PORT"
            else
                print_warning "Backend nie odpowiada na health check"
            fi
        else
            print_error "Backend nie działa (stary PID: $BACKEND_PID)"
        fi
    else
        print_warning "Backend nie jest uruchomiony"
    fi
    
    # Frontend
    if [ -f "$PID_FRONTEND" ]; then
        FRONTEND_PID=$(cat "$PID_FRONTEND")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            print_success "Frontend działa (PID: $FRONTEND_PID)"
            if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
                print_success "Frontend odpowiada na http://localhost:$FRONTEND_PORT"
            else
                print_warning "Frontend nie odpowiada"
            fi
        else
            print_error "Frontend nie działa (stary PID: $FRONTEND_PID)"
        fi
    else
        print_warning "Frontend nie jest uruchomiony"
    fi
    
    echo ""
    print_info "Adresy:"
    echo "  🌐 Frontend: http://localhost:$FRONTEND_PORT"
    echo "  📡 Backend:  http://localhost:$BACKEND_PORT"
    echo "  📚 API Docs: http://localhost:$BACKEND_PORT/docs"
    echo ""
}

# ============================================================================
# Logi
# ============================================================================

show_logs() {
    print_header "Logi aplikacji"
    
    if [ -f "$LOG_BACKEND" ]; then
        echo -e "${BLUE}=== Backend Log ===${NC}"
        tail -n 50 "$LOG_BACKEND"
        echo ""
    else
        print_warning "Brak logów backendu"
    fi
    
    if [ -f "$LOG_FRONTEND" ]; then
        echo -e "${BLUE}=== Frontend Log ===${NC}"
        tail -n 50 "$LOG_FRONTEND"
        echo ""
    else
        print_warning "Brak logów frontendu"
    fi
}

# ============================================================================
# Tryb interaktywny
# ============================================================================

interactive_mode() {
    print_header "🚀 Uruchamianie ParagonOCR Web App"
    
    check_requirements
    check_ports || exit 1
    check_ollama
    
    print_header "Instrukcja uruchomienia"
    echo ""
    echo "Otwórz DWA terminale:"
    echo ""
    echo -e "${GREEN}Terminal 1 - Backend (FastAPI):${NC}"
    echo "  cd $BASE_DIR"
    echo "  source venv/bin/activate"
    echo "  python server.py"
    echo ""
    echo -e "${GREEN}Terminal 2 - Frontend (NiceGUI):${NC}"
    echo "  cd $BASE_DIR"
    echo "  source venv/bin/activate"
    echo "  python web_app.py"
    echo ""
    echo -e "${BLUE}Adresy po uruchomieniu:${NC}"
    echo "  🌐 Frontend: http://localhost:$FRONTEND_PORT"
    echo "  📡 Backend:  http://localhost:$BACKEND_PORT"
    echo "  📚 API Docs: http://localhost:$BACKEND_PORT/docs"
    echo ""
    echo -e "${YELLOW}⚠️  Uwaga: Port 8080 jest zajęty przez open-webui,${NC}"
    echo "   więc ParagonOCR używa portu $FRONTEND_PORT"
    echo ""
    
    read -p "Czy chcesz uruchomić backend teraz? (t/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Tt]$ ]]; then
        start_backend "foreground"
    fi
}

# ============================================================================
# Tryb w tle
# ============================================================================

background_mode() {
    print_header "🚀 Uruchamianie ParagonOCR w tle"
    
    check_requirements
    check_ports || exit 1
    check_ollama
    
    # Zatrzymaj stare procesy jeśli działają
    stop_processes
    
    # Uruchom w tle
    start_backend "background"
    sleep 2  # Daj backendowi czas na start
    
    start_frontend "background"
    sleep 2  # Daj frontendowi czas na start
    
    echo ""
    print_header "Aplikacja uruchomiona"
    print_success "Backend i frontend działają w tle"
    echo ""
    print_info "Adresy:"
    echo "  🌐 Frontend: http://localhost:$FRONTEND_PORT"
    echo "  📡 Backend:  http://localhost:$BACKEND_PORT"
    echo "  📚 API Docs: http://localhost:$BACKEND_PORT/docs"
    echo ""
    print_info "Polecenia:"
    echo "  ./start.sh --status  - Sprawdź status"
    echo "  ./start.sh --stop    - Zatrzymaj aplikację"
    echo "  ./start.sh --logs    - Pokaż logi"
    echo ""
}

# ============================================================================
# Główna logika
# ============================================================================

case "${1:-}" in
    --background|--bg|-b)
        background_mode
        ;;
    --stop|-s)
        stop_processes
        ;;
    --status|--stat)
        check_status
        ;;
    --restart|-r)
        stop_processes
        sleep 2
        background_mode
        ;;
    --logs|-l)
        show_logs
        ;;
    --help|-h)
        print_header "ParagonOCR - Skrypt uruchomieniowy"
        echo ""
        echo "Użycie:"
        echo "  ./start.sh              - Tryb interaktywny (dwa terminale)"
        echo "  ./start.sh --background - Uruchom w tle"
        echo "  ./start.sh --stop       - Zatrzymaj aplikację"
        echo "  ./start.sh --status     - Sprawdź status"
        echo "  ./start.sh --restart    - Restart aplikacji"
        echo "  ./start.sh --logs       - Pokaż logi"
        echo "  ./start.sh --help       - Pokaż tę pomoc"
        echo ""
        ;;
    "")
        interactive_mode
        ;;
    *)
        print_error "Nieznana opcja: $1"
        echo "Użyj: ./start.sh --help aby zobaczyć dostępne opcje"
        exit 1
        ;;
esac

