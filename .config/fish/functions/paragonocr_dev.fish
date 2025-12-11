# ParagonOCR Development Server - Fish function
# Uruchamia backend i frontend z logami

function paragonocr_dev --description "Uruchom ParagonOCR dev servers z logami"
    set script_path (dirname (dirname (status --current-filename)))/scripts/start_dev.fish
    
    if test -f "$script_path"
        fish "$script_path" $argv
    else
        # Fallback do bash version
        set bash_script (dirname (dirname (status --current-filename)))/scripts/start_dev.sh
        if test -f "$bash_script"
            bash "$bash_script" $argv
        else
            echo "❌ Nie znaleziono skryptu start_dev"
            return 1
        end
    end
end

