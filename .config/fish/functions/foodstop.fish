# ParagonOCR - Alias do zatrzymywania serwerów dev
# Użycie: foodstop

function foodstop --description "Zatrzymaj ParagonOCR dev servers"
    set script_path (dirname (dirname (dirname (status --current-filename))))/scripts/start_dev.fish
    
    if test -f "$script_path"
        fish "$script_path" stop
    else
        # Fallback do bash version
        set bash_script (dirname (dirname (dirname (status --current-filename))))/scripts/start_dev.sh
        if test -f "$bash_script"
            bash "$bash_script" stop
        else
            echo "❌ Nie znaleziono skryptu start_dev"
            echo "   Sprawdź czy jesteś w projekcie ParagonOCR"
            return 1
        end
    end
end

