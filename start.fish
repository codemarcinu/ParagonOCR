# ============================================================================
# ParagonOCR - Wrapper dla Fish Shell
# ============================================================================
# 
# Dodaj do ~/.config/fish/config.fish:
#   source /home/marcin/Projekty/ParagonOCR/start.fish
#
# Użycie:
#   paragon start      - Uruchom w tle
#   paragon stop       - Zatrzymaj
#   paragon status     - Status
#   paragon restart    - Restart
#   paragon logs       - Logi
#   paragon manager    - Uruchom GUI managera
# ============================================================================

function paragon -d "Zarządzanie aplikacją ParagonOCR"
    set BASE_DIR (dirname (status --current-filename))
    set START_SCRIPT "$BASE_DIR/start.sh"
    
    switch $argv[1]
        case start
            bash $START_SCRIPT --background
        case stop
            bash $START_SCRIPT --stop
        case status
            bash $START_SCRIPT --status
        case restart
            bash $START_SCRIPT --restart
        case logs
            bash $START_SCRIPT --logs
        case manager
            cd $BASE_DIR
            source venv/bin/activate.fish
            python manager.py
        case help
            echo "ParagonOCR - Zarządzanie aplikacją"
            echo ""
            echo "Użycie: paragon [komenda]"
            echo ""
            echo "Komendy:"
            echo "  start     - Uruchom aplikację w tle"
            echo "  stop      - Zatrzymaj aplikację"
            echo "  status    - Sprawdź status"
            echo "  restart   - Restart aplikacji"
            echo "  logs      - Pokaż logi"
            echo "  manager   - Uruchom GUI managera"
            echo "  help      - Pokaż tę pomoc"
        case '*'
            echo "Nieznana komenda: $argv[1]"
            echo "Użyj: paragon help"
    end
end





