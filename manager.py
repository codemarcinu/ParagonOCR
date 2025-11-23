"""
GUI do zarządzania aplikacją ParagonOCR.

Umożliwia:
- Sprawdzanie statusu aplikacji
- Uruchamianie/zatrzymywanie/restart
- Przeglądanie logów
- Sprawdzanie portów i Ollama
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Optional

from nicegui import ui, app

# Ścieżki
BASE_DIR = Path(__file__).parent.absolute()
START_SCRIPT = BASE_DIR / "start.sh"
PID_BACKEND = BASE_DIR / ".paragon_backend.pid"
PID_FRONTEND = BASE_DIR / ".paragon_frontend.pid"
LOG_BACKEND = BASE_DIR / "logs" / "backend.log"
LOG_FRONTEND = BASE_DIR / "logs" / "frontend.log"

# Porty
BACKEND_PORT = 8000
FRONTEND_PORT = 8081
OLLAMA_PORT = 11434


# ============================================================================
# Funkcje pomocnicze
# ============================================================================

def run_command(cmd: list, check: bool = False) -> tuple[int, str, str]:
    """Wykonuje komendę i zwraca kod wyjścia, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def check_port(port: int) -> bool:
    """Sprawdza czy port jest zajęty."""
    code, _, _ = run_command(["lsof", "-i", f":{port}"])
    return code == 0


def check_ollama() -> tuple[bool, str]:
    """Sprawdza czy Ollama działa."""
    try:
        import httpx
        response = httpx.get(f"http://localhost:{OLLAMA_PORT}/api/tags", timeout=2)
        if response.status_code == 200:
            return True, "Działa"
        return False, f"Status: {response.status_code}"
    except Exception as e:
        return False, str(e)


def get_process_status(pid_file: Path) -> tuple[bool, Optional[int], str]:
    """Sprawdza status procesu na podstawie pliku PID."""
    if not pid_file.exists():
        return False, None, "Nie uruchomiony"
    
    try:
        pid = int(pid_file.read_text().strip())
        # Sprawdź czy proces istnieje
        code, _, _ = run_command(["kill", "-0", str(pid)])
        if code == 0:
            return True, pid, f"Działa (PID: {pid})"
        else:
            return False, pid, "Proces nie istnieje (stary PID)"
    except Exception as e:
        return False, None, f"Błąd: {str(e)}"


def get_logs(log_file: Path, lines: int = 50) -> str:
    """Pobiera ostatnie linie z pliku logów."""
    if not log_file.exists():
        return "Brak pliku logów"
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            return ''.join(all_lines[-lines:])
    except Exception as e:
        return f"Błąd odczytu: {str(e)}"


# ============================================================================
# Funkcje akcji
# ============================================================================

# Funkcje akcji są zdefiniowane wewnątrz strony


# ============================================================================
# Strona główna
# ============================================================================

@ui.page('/')
def main_page():
    """Główna strona zarządzania."""
    
    ui.add_head_html("""
    <style>
        .status-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status-running {
            color: #22c55e;
            font-weight: bold;
        }
        .status-stopped {
            color: #ef4444;
            font-weight: bold;
        }
        .status-warning {
            color: #f59e0b;
            font-weight: bold;
        }
        .btn-group {
            display: flex;
            gap: 10px;
            margin: 10px 0;
        }
        .log-container {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
    </style>
    """)
    
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('🔧 ParagonOCR - Manager').style('font-size: 2em; font-weight: bold; margin-bottom: 20px;')
        
        # Status aplikacji
        with ui.card().classes('status-card'):
            ui.label('📊 Status Aplikacji').style('font-size: 1.3em; font-weight: bold; margin-bottom: 15px;')
            
            backend_status_label = ui.label('Sprawdzam...').classes('text-lg')
            frontend_status_label = ui.label('Sprawdzam...').classes('text-lg')
            
            # Status Ollama
            ollama_status_label = ui.label('Sprawdzam Ollama...').classes('text-lg')
            
            # Status portów
            with ui.row().classes('w-full mt-4'):
                with ui.column().classes('flex-1'):
                    ui.label('Porty:').style('font-weight: bold;')
                    port_backend_label = ui.label('Port 8000: sprawdzam...')
                    port_frontend_label = ui.label('Port 8081: sprawdzam...')
            
            # Funkcje akcji (muszą być zdefiniowane przed użyciem w przyciskach)
            def start_backend():
                """Uruchamia backend."""
                if check_port(BACKEND_PORT):
                    ui.notify("Port 8000 jest już zajęty!", type='negative')
                    return
                
                ui.notify("Uruchamiam backend...", type='info')
                
                # Uruchom w tle przez skrypt
                code, stdout, stderr = run_command([
                    str(START_SCRIPT), "--background"
                ])
                
                if code == 0:
                    ui.notify("Backend uruchomiony!", type='positive')
                    refresh_status()
                else:
                    ui.notify(f"Błąd: {stderr}", type='negative')
            
            def stop_backend():
                """Zatrzymuje backend."""
                ui.notify("Zatrzymuję backend...", type='info')
                
                code, stdout, stderr = run_command([
                    str(START_SCRIPT), "--stop"
                ])
                
                if code == 0:
                    ui.notify("Backend zatrzymany!", type='positive')
                    refresh_status()
                else:
                    ui.notify(f"Błąd: {stderr}", type='negative')
            
            def restart_backend():
                """Restartuje backend."""
                ui.notify("Restartuję backend...", type='info')
                
                code, stdout, stderr = run_command([
                    str(START_SCRIPT), "--restart"
                ])
                
                if code == 0:
                    ui.notify("Backend zrestartowany!", type='positive')
                    refresh_status()
                else:
                    ui.notify(f"Błąd: {stderr}", type='negative')
            
            # Przyciski akcji
            with ui.row().classes('btn-group mt-4'):
                start_btn = ui.button('▶️ Start', on_click=start_backend).props('color=positive')
                stop_btn = ui.button('⏹️ Stop', on_click=stop_backend).props('color=negative')
                restart_btn = ui.button('🔄 Restart', on_click=restart_backend).props('color=primary')
                refresh_btn = ui.button('🔄 Odśwież', on_click=refresh_status).props('color=secondary')
        
        # Logi
        with ui.card().classes('status-card'):
            ui.label('📋 Logi').style('font-size: 1.3em; font-weight: bold; margin-bottom: 15px;')
            
            log_tabs = ui.tabs([
                ui.tab('Backend', name='backend'),
                ui.tab('Frontend', name='frontend'),
            ]).classes('w-full')
            
            with ui.tab_panels(log_tabs, value='backend').classes('w-full'):
                with ui.tab_panel('backend'):
                    backend_log = ui.label('Ładuję logi...').classes('log-container')
                
                with ui.tab_panel('frontend'):
                    frontend_log = ui.label('Ładuję logi...').classes('log-container')
            
            with ui.row().classes('mt-2'):
                ui.button('🔄 Odśwież logi', on_click=lambda: refresh_logs()).props('size=sm')
        
        # Informacje o adresach
        with ui.card().classes('status-card'):
            ui.label('🌐 Adresy').style('font-size: 1.3em; font-weight: bold; margin-bottom: 15px;')
            
            with ui.column():
                ui.label(f'Frontend: http://localhost:{FRONTEND_PORT}').classes('text-lg')
                ui.label(f'Backend API: http://localhost:{BACKEND_PORT}').classes('text-lg')
                ui.label(f'API Docs: http://localhost:{BACKEND_PORT}/docs').classes('text-lg')
                ui.label(f'Manager: http://localhost:8082').classes('text-lg')
        
        # Funkcja odświeżania statusu
        def refresh_status():
            """Odświeża status wszystkich komponentów."""
            backend_status_label.text = 'Sprawdzam...'
            frontend_status_label.text = 'Sprawdzam...'
            ollama_status_label.text = 'Sprawdzam...'
            port_backend_label.text = 'Sprawdzam port 8000...'
            port_frontend_label.text = 'Sprawdzam port 8081...'
            
            # Sprawdź backend
            backend_running, backend_pid, backend_msg = get_process_status(PID_BACKEND)
            if backend_running:
                backend_status_label.text = f'✅ Backend: {backend_msg}'
                backend_status_label.classes('status-running')
            else:
                backend_status_label.text = f'❌ Backend: {backend_msg}'
                backend_status_label.classes('status-stopped')
            
            # Sprawdź frontend
            frontend_running, frontend_pid, frontend_msg = get_process_status(PID_FRONTEND)
            if frontend_running:
                frontend_status_label.text = f'✅ Frontend: {frontend_msg}'
                frontend_status_label.classes('status-running')
            else:
                frontend_status_label.text = f'❌ Frontend: {frontend_msg}'
                frontend_status_label.classes('status-stopped')
            
            # Sprawdź Ollama
            ollama_ok, ollama_msg = check_ollama()
            if ollama_ok:
                ollama_status_label.text = f'✅ Ollama: {ollama_msg}'
                ollama_status_label.classes('status-running')
            else:
                ollama_status_label.text = f'⚠️ Ollama: {ollama_msg}'
                ollama_status_label.classes('status-warning')
            
            # Sprawdź porty
            if check_port(BACKEND_PORT):
                port_backend_label.text = '🔴 Port 8000: zajęty'
            else:
                port_backend_label.text = '🟢 Port 8000: wolny'
            
            if check_port(FRONTEND_PORT):
                port_frontend_label.text = '🔴 Port 8081: zajęty'
            else:
                port_frontend_label.text = '🟢 Port 8081: wolny'
            
            # Odśwież logi
            refresh_logs()
        
        # Funkcja odświeżania logów
        def refresh_logs():
            """Odświeża logi."""
            backend_log.text = get_logs(LOG_BACKEND)
            frontend_log.text = get_logs(LOG_FRONTEND)
        
        # Automatyczne odświeżanie co 5 sekund
        ui.timer(5.0, refresh_status)
        
        # Odśwież przy starcie
        refresh_status()


# ============================================================================
# Uruchomienie
# ============================================================================

if __name__ in {"__main__", "__mp_main__"}:
    # Port 8082 dla managera (żeby nie kolidował z innymi)
    ui.run(port=8082, title="ParagonOCR Manager", show=False)

