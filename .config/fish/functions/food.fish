# ParagonOCR - Alias do uruchamiania serwerów dev
# Użycie: food [start|status|stop|restart]

function food --description "Uruchom ParagonOCR dev servers (food = food tracking)"
    set script_path (dirname (dirname (dirname (status --current-filename))))/scripts/start_dev.fish
    
    if test -f "$script_path"
        fish "$script_path" $argv
    else
        # Fallback do bash version
        set bash_script (dirname (dirname (dirname (status --current-filename))))/scripts/start_dev.sh
        if test -f "$bash_script"
            bash "$bash_script" $argv
        else
            echo "❌ Nie znaleziono skryptu start_dev"
            echo "   Sprawdź czy jesteś w projekcie ParagonOCR"
            return 1
        end
    end
end

