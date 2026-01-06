#!/usr/bin/env fish
# ParagonOCR Web Edition - Development server with live backend logs (Fish Shell version)
# Uruchamia backend i frontend, pokazuje logi backendu na bieżąco w konsoli

# Kolory
set -g GREEN '\033[0;32m'
set -g BLUE '\033[0;34m'
set -g YELLOW '\033[1;33m'
set -g RED '\033[0;31m'
set -g CYAN '\033[0;36m'
set -g NC '\033[0m'

# Ścieżki
set -g SCRIPT_DIR (dirname (status --current-filename))
set -g PROJECT_ROOT (dirname $SCRIPT_DIR)
set -g BACKEND_DIR "$PROJECT_ROOT/backend"
set -g FRONTEND_DIR "$PROJECT_ROOT/frontend"
set -g BACKEND_LOG "$PROJECT_ROOT/backend.log"
set -g FRONTEND_LOG "$PROJECT_ROOT/frontend.log"

# PID pliki
set -g BACKEND_PID_FILE "$PROJECT_ROOT/.backend.pid"
set -g FRONTEND_PID_FILE "$PROJECT_ROOT/.frontend.pid"

# Funkcja sprawdzająca status
function check_status
    echo ""
    echo -e "$CYAN=== Status serwerów ===$NC"
    
    # Sprawdź backend
    if test -f "$BACKEND_PID_FILE"
        set BACKEND_PID (cat "$BACKEND_PID_FILE")
        if ps -p $BACKEND_PID > /dev/null 2>&1
            echo -e "$GREEN✓ Backend:$NC Działa (PID: $BACKEND_PID)"
            if curl -s http://localhost:8000/health > /dev/null 2>&1
                echo -e "  $GREEN✓ API dostępne$NC na http://localhost:8000"
            else
                echo -e "  $YELLOW⚠ API nie odpowiada$NC"
            end
        else
            echo -e "$RED✗ Backend:$NC Nie działa"
            rm -f "$BACKEND_PID_FILE"
        end
    else
        echo -e "$RED✗ Backend:$NC Nie uruchomiony"
    end
    
    # Sprawdź frontend
    if test -f "$FRONTEND_PID_FILE"
        set FRONTEND_PID (cat "$FRONTEND_PID_FILE")
        if ps -p $FRONTEND_PID > /dev/null 2>&1
            echo -e "$GREEN✓ Frontend:$NC Działa (PID: $FRONTEND_PID)"
            if curl -s http://localhost:5173 > /dev/null 2>&1
                echo -e "  $GREEN✓ Frontend dostępny$NC na http://localhost:5173"
            else
                echo -e "  $YELLOW⚠ Frontend nie odpowiada$NC"
            end
        else
            echo -e "$RED✗ Frontend:$NC Nie działa"
            rm -f "$FRONTEND_PID_FILE"
        end
    else
        echo -e "$RED✗ Frontend:$NC Nie uruchomiony"
    end
    
    # Sprawdź Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1
        echo -e "$GREEN✓ Ollama:$NC Działa"
    else
        echo -e "$YELLOW⚠ Ollama:$NC Nie działa (wymagane dla AI)"
    end
    
    echo ""
end

# Funkcja zatrzymująca serwery
function stop_servers
    echo ""
    echo -e "$YELLOW🛑 Zatrzymywanie serwerów...$NC"
    
    # Zatrzymaj backend
    if test -f "$BACKEND_PID_FILE"
        set BACKEND_PID (cat "$BACKEND_PID_FILE")
        if ps -p $BACKEND_PID > /dev/null 2>&1
            echo "Zatrzymywanie backendu (PID: $BACKEND_PID)..."
            kill $BACKEND_PID 2>/dev/null; or true
            sleep 1
            kill -9 $BACKEND_PID 2>/dev/null; or true
        end
        rm -f "$BACKEND_PID_FILE"
    end
    
    # Zatrzymaj frontend
    if test -f "$FRONTEND_PID_FILE"
        set FRONTEND_PID (cat "$FRONTEND_PID_FILE")
        if ps -p $FRONTEND_PID > /dev/null 2>&1
            echo "Zatrzymywanie frontendu (PID: $FRONTEND_PID)..."
            kill $FRONTEND_PID 2>/dev/null; or true
            sleep 1
            kill -9 $FRONTEND_PID 2>/dev/null; or true
        end
        rm -f "$FRONTEND_PID_FILE"
    end
    
    # Zabij wszystkie procesy uvicorn i vite związane z projektem
    pkill -f "uvicorn.*app.main:app" 2>/dev/null; or true
    pkill -f "vite.*$FRONTEND_DIR" 2>/dev/null; or true
    
    echo -e "$GREEN✓ Serwery zatrzymane$NC"
    echo ""
    exit 0
end

# Funkcja czyszcząca stare procesy
function cleanup_old_processes
    # Sprawdź czy porty są zajęte - użyj dostępnego narzędzia
    # Priorytet: fuser > lsof > ss > netstat
    if command -v fuser > /dev/null 2>&1
        if fuser -k 5173/tcp > /dev/null 2>&1
            echo "♻️  Zwolniono port 5173"
            sleep 1
        end
    end

    if command -v lsof > /dev/null 2>&1
        # Użyj lsof - może zabić procesy
        if lsof -ti:8000 > /dev/null 2>&1
            echo -e "$YELLOW⚠ Port 8000 jest zajęty. Próbuję zwolnić...$NC"
            lsof -ti:8000 | xargs kill -9 2>/dev/null; or true
            sleep 1
        end
        if lsof -ti:5173 > /dev/null 2>&1
            echo -e "$YELLOW⚠ Port 5173 jest zajęty. Próbuję zwolnić...$NC"
            lsof -ti:5173 | xargs kill -9 2>/dev/null; or true
            sleep 1
        end
    else if command -v ss > /dev/null 2>&1
        # Użyj ss - tylko sprawdzenie, nie zabija procesów
        if ss -tlnp 2>/dev/null | grep -q ":8000"
            echo -e "$YELLOW⚠ Port 8000 jest zajęty. Zatrzymaj proces ręcznie.$NC"
        end
        if ss -tlnp 2>/dev/null | grep -q ":5173"
            echo -e "$YELLOW⚠ Port 5173 jest zajęty. Zatrzymaj proces ręcznie.$NC"
        end
    else if command -v netstat > /dev/null 2>&1
        # Użyj netstat - tylko sprawdzenie
        if netstat -tlnp 2>/dev/null | grep -q ":8000"
            echo -e "$YELLOW⚠ Port 8000 jest zajęty. Zatrzymaj proces ręcznie.$NC"
        end
        if netstat -tlnp 2>/dev/null | grep -q ":5173"
            echo -e "$YELLOW⚠ Port 5173 jest zajęty. Zatrzymaj proces ręcznie.$NC"
        end
    else
        echo -e "$YELLOW⚠ Nie znaleziono narzędzia do sprawdzania portów$NC"
        echo "   Upewnij się, że porty 8000 i 5173 są wolne"
    end
end

# Funkcja uruchamiająca backend
function start_backend
    echo -e "$BLUE🔧 Uruchamianie backendu...$NC"
    
    cd "$BACKEND_DIR"
    
    # Sprawdź czy venv istnieje
    if not test -d "venv"
        echo -e "$RED✗ Błąd: venv nie znaleziony w $BACKEND_DIR$NC"
        exit 1
    end
    
    # Aktywuj venv - fish używa activate.fish jeśli istnieje
    if test -f venv/bin/activate.fish
        source venv/bin/activate.fish
    else
        # Fallback - ustaw zmienne ręcznie
        set -gx VIRTUAL_ENV "$BACKEND_DIR/venv"
        set -gx PATH "$VIRTUAL_ENV/bin" $PATH
    end
    
    # Sprawdź zależności
    if not python3 -c "import uvicorn" 2>/dev/null
        echo -e "$YELLOW⚠ Instalowanie zależności backendu...$NC"
        pip install -q -r requirements.txt
    end
    
    # Ustaw PYTHONPATH
    set -gx PYTHONPATH "$BACKEND_DIR:$PYTHONPATH"
    
    # Uruchom backend z logowaniem do pliku i konsoli
    echo -e "$CYANBackend loguje do: $BACKEND_LOG$NC"
    echo -e "$CYANBackend dostępny na: http://localhost:8000$NC"
    echo -e "$CYANAPI Docs: http://localhost:8000/docs$NC"
    echo ""
    
    # Uruchom uvicorn w tle z logowaniem do pliku
    # W fish używamy begin/end do uruchomienia w tle
    uvicorn app.main:app \
        --reload \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level info \
        > "$BACKEND_LOG" 2>&1 &
    
    set -g BACKEND_PID $last_pid
    echo $BACKEND_PID > "$BACKEND_PID_FILE"
    
    # Poczekaj na start
    echo "Czekam na uruchomienie backendu..."
    for i in (seq 1 10)
        if curl -s http://localhost:8000/health > /dev/null 2>&1
            echo -e "$GREEN✓ Backend uruchomiony (PID: $BACKEND_PID)$NC"
            return 0
        end
        sleep 1
    end
    
    echo -e "$RED✗ Backend nie odpowiada po 10 sekundach$NC"
    return 1
end

# Funkcja uruchamiająca frontend
function start_frontend
    echo -e "$BLUE🎨 Uruchamianie frontendu...$NC"
    
    cd "$FRONTEND_DIR"
    
    # Sprawdź czy node_modules istnieje
    if not test -d "node_modules"
        echo -e "$YELLOW⚠ Instalowanie zależności frontendu...$NC"
        npm install
    end
    
    # Uruchom frontend w tle
    echo -e "$CYANFrontend loguje do: $FRONTEND_LOG$NC"
    echo -e "$CYANFrontend dostępny na: http://localhost:5173$NC"
    echo ""
    
    npm run dev > "$FRONTEND_LOG" 2>&1 &
    
    set -g FRONTEND_PID $last_pid
    echo $FRONTEND_PID > "$FRONTEND_PID_FILE"
    
    # Poczekaj na start
    echo "Czekam na uruchomienie frontendu..."
    for i in (seq 1 15)
        if curl -s http://localhost:5173 > /dev/null 2>&1
            echo -e "$GREEN✓ Frontend uruchomiony (PID: $FRONTEND_PID)$NC"
            return 0
        end
        sleep 1
    end
    
    echo -e "$YELLOW⚠ Frontend może jeszcze się uruchamiać...$NC"
    return 0
end

# Obsługa sygnałów
function on_exit --on-signal INT --on-signal TERM
    stop_servers
end

# Główna logika
function main
    if test (count $argv) -gt 0
        set command $argv[1]
    else
        set command "start"
    end
    
    switch $command
        case start
            echo -e "$GREEN🚀 ParagonOCR Web Edition - Development Server$NC"
            echo ""
            
            # Sprawdź Ollama
            if not curl -s http://localhost:11434/api/tags > /dev/null 2>&1
                echo -e "$YELLOW⚠ Ostrzeżenie: Ollama nie działa$NC"
                echo "   Uruchom: $BLUEollama serve$NC"
                echo ""
            end
            
            # Wyczyść stare procesy
            cleanup_old_processes
            
            # Uruchom backend
            start_backend
            
            # Poczekaj chwilę
            sleep 1
            
            # Uruchom frontend (w tle)
            start_frontend
            
            echo ""
            printf "%s✅ Serwery uruchomione!%s\n" $GREEN $NC
            echo ""
            printf "%s=== Dostęp ===%s\n" $CYAN $NC
            printf "  Frontend: %shttp://localhost:5173%s\n" $GREEN $NC
            printf "  Backend:  %shttp://localhost:8000%s\n" $GREEN $NC
            printf "  API Docs: %shttp://localhost:8000/docs%s\n" $GREEN $NC
            echo ""
            printf "%s=== Logi ===%s\n" $CYAN $NC
            printf "  Backend:  %stail -f %s%s (widoczne poniżej)\n" $BLUE $BACKEND_LOG $NC
            printf "  Frontend: %stail -f %s%s\n" $BLUE $FRONTEND_LOG $NC
            echo ""
            printf "%s=== Komendy ===%s\n" $CYAN $NC
            printf "  Status:   %s%s/start_dev.fish status%s (w osobnym terminalu)\n" $BLUE $SCRIPT_DIR $NC
            printf "  Stop:     %s%s/start_dev.fish stop%s lub Ctrl+C\n" $BLUE $SCRIPT_DIR $NC
            echo ""
            printf "%sNaciśnij Ctrl+C aby zatrzymać serwery%s\n" $YELLOW $NC
            echo ""
            printf "%s════════════════════════════════════════════════════%s\n" $CYAN $NC
            printf "%s  LOGI BACKENDU (na bieżąco)%s\n" $CYAN $NC
            printf "%s════════════════════════════════════════════════════%s\n" $CYAN $NC
            echo ""
            
            # Pokaż ostatnie logi i kontynuuj pokazywanie na bieżąco
            if test -f "$BACKEND_LOG"
                # Pokaż ostatnie 20 linii
                tail -n 20 "$BACKEND_LOG" 2>/dev/null
                echo ""
                printf "%s--- Nowe logi (Ctrl+C aby zatrzymać) ---%s\n" $CYAN $NC
                echo ""
            end
            
            # Pokaż logi backendu na bieżąco (to zablokuje wykonanie)
            tail -f "$BACKEND_LOG" 2>/dev/null; or begin
                # Jeśli tail nie działa, pokaż ostatnie logi
                echo "Wyświetlanie ostatnich logów backendu..."
                tail -n 50 "$BACKEND_LOG" 2>/dev/null; or echo "Brak logów"
                # Czekaj w pętli
                while true
                    sleep 1
                    if not test -f "$BACKEND_PID_FILE"
                        break
                    end
                    if not ps -p (cat "$BACKEND_PID_FILE" 2>/dev/null) > /dev/null 2>&1
                        break
                    end
                end
            end
            
        case status
            check_status
        case stop
            stop_servers
        case restart
            stop_servers
            sleep 2
            main start
        case '*'
            echo "Użycie: $SCRIPT_DIR/start_dev.fish {start|status|stop|restart}"
            echo ""
            echo "  start   - Uruchom backend i frontend (domyślnie)"
            echo "  status  - Sprawdź status serwerów"
            echo "  stop    - Zatrzymaj serwery"
            echo "  restart - Zatrzymaj i uruchom ponownie"
            exit 1
    end
end

# Uruchom główną funkcję
main $argv

