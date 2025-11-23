# 🔧 ParagonOCR Manager - GUI do zarządzania aplikacją

## Opis

Manager to aplikacja webowa (NiceGUI) do zarządzania aplikacją ParagonOCR. Umożliwia:

- ✅ Sprawdzanie statusu aplikacji (backend/frontend)
- ▶️ Uruchamianie/zatrzymywanie/restart aplikacji
- 📋 Przeglądanie logów w czasie rzeczywistym
- 🔍 Sprawdzanie portów i Ollama
- 🔄 Automatyczne odświeżanie statusu co 5 sekund

## Uruchomienie

```bash
cd /home/marcin/Projekty/ParagonOCR
source venv/bin/activate
python manager.py
```

Następnie otwórz w przeglądarce:
**http://localhost:8082**

## Funkcje

### Status Aplikacji
- Sprawdza czy backend i frontend działają
- Sprawdza status Ollama
- Sprawdza dostępność portów (8000, 8081)

### Przyciski akcji
- **▶️ Start** - Uruchamia aplikację w tle
- **⏹️ Stop** - Zatrzymuje aplikację
- **🔄 Restart** - Restartuje aplikację
- **🔄 Odśwież** - Ręczne odświeżenie statusu

### Logi
- Wyświetla logi backendu i frontendu
- Automatyczne odświeżanie
- Możliwość ręcznego odświeżenia

### Adresy
- Frontend: http://localhost:8081
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Manager: http://localhost:8082

## Wymagania

- Python 3.13+
- Zainstalowane zależności z `requirements.txt`
- Skrypt `start.sh` w katalogu głównym projektu

## Uwagi

- Manager działa na porcie 8082 (nie koliduje z innymi aplikacjami)
- Wymaga uprawnień do wykonywania `start.sh`
- Automatycznie odświeża status co 5 sekund

