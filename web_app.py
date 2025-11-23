"""
NiceGUI frontend dla ParagonWeb.

Prosty, nowoczesny interfejs webowy dla osoby nietechnicznej.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime

from nicegui import ui, app
import httpx

# Dodaj ReceiptParser do ścieżki
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ReceiptParser'))

# URL API (domyślnie localhost, można zmienić przez zmienną środowiskową)
API_URL = os.getenv("API_URL", "http://localhost:8000")


# --- Design System ---

class AppColors:
    """Spójna paleta kolorów dla aplikacji webowej."""
    # Kolory główne
    PRIMARY = "#1f538d"
    PRIMARY_DARK = "#1a4470"
    PRIMARY_LIGHT = "#2563eb"
    
    # Kolory statusów
    SUCCESS = "#10b981"
    WARNING = "#f59e0b"
    ERROR = "#ef4444"
    INFO = "#3b82f6"
    
    # Kolory tła
    BG_LIGHT = "#f8fafc"
    BG_DARK = "#0f172a"
    CARD_LIGHT = "#ffffff"
    CARD_DARK = "#1e293b"
    
    # Kolory tekstu
    TEXT_PRIMARY = "#1e293b"
    TEXT_SECONDARY = "#64748b"
    TEXT_DARK = "#f1f5f9"
    
    # Gradienty
    GRADIENT_PRIMARY = "linear-gradient(135deg, #1f538d 0%, #2563eb 100%)"
    GRADIENT_SUCCESS = "linear-gradient(135deg, #10b981 0%, #34d399 100%)"
    GRADIENT_WARNING = "linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)"


# --- Stylowanie ---

def setup_styles():
    """Konfiguruje style CSS dla aplikacji."""
    ui.add_head_html(f"""
    <style>
        :root {{
            --primary: {AppColors.PRIMARY};
            --primary-dark: {AppColors.PRIMARY_DARK};
            --primary-light: {AppColors.PRIMARY_LIGHT};
            --success: {AppColors.SUCCESS};
            --warning: {AppColors.WARNING};
            --error: {AppColors.ERROR};
            --info: {AppColors.INFO};
            
            /* Light mode (domyślne) */
            --bg: {AppColors.BG_LIGHT};
            --card: {AppColors.CARD_LIGHT};
            --text-primary: {AppColors.TEXT_PRIMARY};
            --text-secondary: {AppColors.TEXT_SECONDARY};
        }}
        
        * {{
            transition: background-color 0.3s ease, color 0.3s ease;
        }}
        
        body {{
            background: var(--bg);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 0;
        }}
        
        .app-container {{
            display: flex;
            min-height: 100vh;
        }}
        
        .sidebar {{
            width: 260px;
            background: var(--card);
            border-right: 1px solid rgba(0,0,0,0.1);
            padding: 20px;
            position: fixed;
            height: 100vh;
            overflow-y: auto;
            box-shadow: 2px 0 8px rgba(0,0,0,0.05);
        }}
        
        .sidebar-logo {{
            font-size: 1.5em;
            font-weight: bold;
            color: var(--primary);
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid rgba(0,0,0,0.1);
        }}
        
        .nav-item {{
            display: block;
            padding: 12px 16px;
            margin: 8px 0;
            border-radius: 8px;
            text-decoration: none;
            color: var(--text-primary);
            transition: all 0.2s ease;
            font-weight: 500;
        }}
        
        .nav-item:hover {{
            background: rgba(31, 83, 141, 0.1);
            transform: translateX(4px);
        }}
        
        .nav-item.active {{
            background: var(--primary);
            color: white;
        }}
        
        .main-content {{
            margin-left: 260px;
            flex: 1;
            padding: 30px;
            max-width: calc(100vw - 260px);
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .page-header {{
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 30px;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .card {{
            background: var(--card);
            border-radius: 12px;
            padding: 24px;
            margin: 16px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.06);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05);
        }}
        
        .card-title {{
            font-size: 1.3em;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text-primary);
        }}
        
        .btn-primary {{
            background: var(--primary);
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(31, 83, 141, 0.2);
        }}
        
        .btn-primary:hover {{
            background: var(--primary-dark);
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(31, 83, 141, 0.3);
        }}
        
        .btn-primary:active {{
            transform: translateY(0);
        }}
        
        .stat-card {{
            text-align: center;
            padding: 28px;
            background: var(--card);
            border-radius: 12px;
            position: relative;
            overflow: hidden;
            transition: transform 0.2s ease;
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gradient);
        }}
        
        .stat-card:hover {{
            transform: translateY(-4px);
        }}
        
        .stat-card.primary::before {{
            background: {AppColors.GRADIENT_PRIMARY};
        }}
        
        .stat-card.success::before {{
            background: {AppColors.GRADIENT_SUCCESS};
        }}
        
        .stat-card.warning::before {{
            background: {AppColors.GRADIENT_WARNING};
        }}
        
        .stat-icon {{
            font-size: 2.5em;
            margin-bottom: 12px;
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: 700;
            color: var(--primary);
            margin: 8px 0;
        }}
        
        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.95em;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .upload-area {{
            border: 2px dashed rgba(31, 83, 141, 0.3);
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s ease;
            background: rgba(31, 83, 141, 0.02);
        }}
        
        .upload-area:hover {{
            border-color: var(--primary);
            background: rgba(31, 83, 141, 0.05);
        }}
        
        .chat-container {{
            max-height: 500px;
            overflow-y: auto;
            padding: 16px;
            background: var(--bg);
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        
        .chat-message {{
            padding: 12px 16px;
            border-radius: 12px;
            margin: 8px 0;
            max-width: 80%;
            word-wrap: break-word;
        }}
        
        .chat-message.user {{
            background: rgba(31, 83, 141, 0.1);
            margin-left: auto;
            text-align: right;
        }}
        
        .chat-message.bot {{
            background: var(--primary);
            color: white;
            margin-right: auto;
        }}
        
        .table-container {{
            overflow-x: auto;
        }}
        
        .table-container table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .table-container th {{
            background: rgba(31, 83, 141, 0.1);
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: var(--text-primary);
            border-bottom: 2px solid var(--primary);
        }}
        
        .table-container td {{
            padding: 12px;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }}
        
        .table-container tr:hover {{
            background: rgba(31, 83, 141, 0.05);
        }}
        
        .loading-skeleton {{
            background: linear-gradient(90deg, rgba(0,0,0,0.05) 25%, rgba(0,0,0,0.1) 50%, rgba(0,0,0,0.05) 75%);
            background-size: 200% 100%;
            animation: loading 1.5s ease-in-out infinite;
            border-radius: 8px;
            height: 20px;
            margin: 8px 0;
        }}
        
        @keyframes loading {{
            0% {{ background-position: 200% 0; }}
            100% {{ background-position: -200% 0; }}
        }}
        
        .dark-mode-toggle {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: var(--primary);
            color: white;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-size: 1.3em;
            z-index: 1000;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .dark-mode-toggle:hover {{
            transform: scale(1.1) rotate(15deg);
            box-shadow: 0 6px 16px rgba(0,0,0,0.2);
        }}
        
        body.dark-mode {{
            --bg: {AppColors.BG_DARK};
            --card: {AppColors.CARD_DARK};
            --text-primary: {AppColors.TEXT_DARK};
            --text-secondary: {AppColors.TEXT_SECONDARY};
        }}
        
        body.dark-mode .sidebar {{
            border-right-color: rgba(255,255,255,0.1);
        }}
        
        body.dark-mode .upload-area {{
            border-color: rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.02);
        }}
        
        body.dark-mode .upload-area:hover {{
            border-color: var(--primary);
            background: rgba(255,255,255,0.05);
        }}
        
        body.dark-mode .table-container th {{
            background: rgba(255,255,255,0.05);
            border-bottom-color: var(--primary);
        }}
        
        body.dark-mode .table-container td {{
            border-bottom-color: rgba(255,255,255,0.1);
        }}
        
        body.dark-mode .table-container tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        
        body.dark-mode .card {{
            box-shadow: 0 4px 6px rgba(0,0,0,0.3), 0 1px 3px rgba(0,0,0,0.2);
        }}
        
        body.dark-mode .card:hover {{
            box-shadow: 0 10px 15px rgba(0,0,0,0.4), 0 4px 6px rgba(0,0,0,0.3);
        }}
        
        body.dark-mode .upload-area {{
            border-color: rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.02);
        }}
        
        body.dark-mode .upload-area:hover {{
            border-color: var(--primary);
            background: rgba(255,255,255,0.05);
        }}
        
        /* Styl dla obszaru logów */
        .process-logs {{
            max-height: 300px;
            overflow-y: auto;
            background: var(--bg);
            border: 1px solid rgba(0,0,0,0.1);
            border-radius: 8px;
            padding: 12px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
        }}
        
        body.dark-mode .process-logs {{
            border-color: rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.2);
        }}
        
        @media (max-width: 768px) {{
            .sidebar {{
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }}
            
            .sidebar.open {{
                transform: translateX(0);
            }}
            
            .main-content {{
                margin-left: 0;
                max-width: 100vw;
            }}
        }}
    </style>
    """)


# --- Funkcje pomocnicze ---

async def api_call(method: str, endpoint: str, data: Optional[dict] = None, files: Optional[dict] = None):
    """Wykonuje wywołanie API z obsługą błędów."""
    url = f"{API_URL}{endpoint}"
    timeout = httpx.Timeout(30.0, connect=10.0)  # 30s timeout, 10s na połączenie
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                if files:
                    response = await client.post(url, data=data, files=files)
                else:
                    response = await client.post(url, json=data)
            elif method == "PUT":
                response = await client.put(url, json=data)
            elif method == "DELETE":
                response = await client.delete(url)
            else:
                raise ValueError(f"Nieobsługiwana metoda: {method}")
            
            response.raise_for_status()
            # DELETE może zwracać 204 No Content
            if response.status_code == 204:
                return {}
            return response.json()
    except httpx.TimeoutException:
        raise Exception(f"Przekroczono limit czasu połączenia z API ({API_URL})")
    except httpx.ConnectError:
        raise Exception(f"Nie można połączyć się z API ({API_URL}). Sprawdź czy serwer działa.")
    except httpx.HTTPStatusError as e:
        error_detail = "Błąd serwera"
        try:
            error_data = e.response.json()
            error_detail = error_data.get("detail", error_detail)
        except:
            error_detail = e.response.text or error_detail
        raise Exception(f"Błąd HTTP {e.response.status_code}: {error_detail}")
    except httpx.RequestError as e:
        raise Exception(f"Błąd podczas wykonywania requestu: {str(e)}")


# --- Komponenty nawigacji ---

def create_sidebar(current_page: str = '/'):
    """Tworzy sidebar nawigacyjny."""
    with ui.column().classes('sidebar'):
        ui.label('📄 ParagonWeb').classes('sidebar-logo')
        
        nav_items = [
            ('/', '🏠', 'Dashboard'),
            ('/magazyn', '📦', 'Spiżarnia'),
            ('/bielik', '🦅', 'Bielik'),
            ('/ustawienia', '⚙️', 'Ustawienia'),
        ]
        
        for path, icon, label in nav_items:
            classes = 'nav-item'
            if path == current_page:
                classes += ' active'
            
            ui.link(f'{icon} {label}', path).classes(classes)


# --- Dark Mode ---

def setup_dark_mode_script():
    """Dodaje skrypt do obsługi dark mode."""
    ui.add_head_html('''
    <script>
        // Sprawdź localStorage przy ładowaniu
        (function() {
            if (localStorage.getItem('darkMode') === 'true') {
                document.body.classList.add('dark-mode');
            }
        })();
    </script>
    ''')

def create_dark_mode_toggle():
    """Tworzy przycisk przełączania dark mode z dynamiczną ikoną."""
    # Domyślnie light mode (🌙 oznacza "przełącz na dark")
    initial_icon = '🌙'
    
    toggle_button = ui.button(initial_icon)
    toggle_button.classes('dark-mode-toggle')
    
    def toggle_handler():
        """Przełącza tryb ciemny bez przeładowania strony."""
        ui.run_javascript('''
            (function() {
                const body = document.body;
                const isDark = body.classList.toggle('dark-mode');
                localStorage.setItem('darkMode', isDark);
                
                // Zaktualizuj ikonę wszystkich przycisków dark mode
                const toggleButtons = document.querySelectorAll('.dark-mode-toggle');
                toggleButtons.forEach(button => {
                    button.textContent = isDark ? '☀️' : '🌙';
                });
            })();
        ''')
    
    toggle_button.on('click', toggle_handler)
    
    # Ustaw początkową ikonę na podstawie localStorage
    ui.run_javascript('''
        (function() {
            const isDark = localStorage.getItem('darkMode') === 'true';
            const buttons = document.querySelectorAll('.dark-mode-toggle');
            buttons.forEach(button => {
                button.textContent = isDark ? '☀️' : '🌙';
            });
        })();
    ''')
    
    return toggle_button


# --- Strony ---

@ui.page('/')
async def dashboard():
    """Strona główna - Dashboard."""
    setup_dark_mode_script()
    setup_styles()
    
    with ui.row().classes('app-container'):
        create_sidebar('/')
        
        with ui.column().classes('main-content'):
            with ui.column().classes('container'):
                ui.label('📄 Dashboard').classes('page-header')
                
                # Przycisk dodawania paragonu
                with ui.card():
                    ui.label('Dodaj nowy paragon').classes('card-title')
                    
                    # Status i postęp
                    status_container = ui.column().style('margin-top: 10px;')
                    with status_container:
                        status_label = ui.label('Gotowy').style('color: var(--text-secondary); font-weight: 600; margin-bottom: 8px;')
                        progress_bar = ui.linear_progress(value=0).style('margin-bottom: 8px;')
                        progress_bar.visible = False
                    
                    # Obszar z logami procesu
                    logs_container = ui.column().style('display: none; margin-top: 16px;')
                    with logs_container:
                        ui.label('📋 Szczegóły procesu').style('font-weight: 600; margin-bottom: 8px; color: var(--text-primary);')
                        logs_area = ui.column().classes('process-logs')
                        logs_area.visible = False
                    
                    async def handle_upload_wrapper(e):
                        """Wrapper dla handle_upload z śledzeniem postępu."""
                        # Pobierz nazwę pliku z obiektu upload
                        file_name = getattr(e, 'name', None) or 'paragon'
                        if hasattr(e, 'content'):
                            # NiceGUI upload event
                            file_name = getattr(e, 'name', 'paragon')
                        
                        # Reset UI
                        status_label.text = f"📤 Przesyłanie pliku: {file_name}..."
                        progress_bar.visible = True
                        progress_bar.value = 0.05
                        logs_container.style('display: block;')
                        logs_area.visible = True
                        logs_area.clear()
                        
                        # Dodaj początkową wiadomość
                        with logs_area:
                            ui.html(f'<div style="color: var(--info);">📤 Rozpoczynam przetwarzanie paragonu: {file_name}...</div>', sanitize=False)
                        
                        try:
                            task_id = await handle_upload(e)
                            if task_id:
                                # Dodaj informację o rozpoczęciu
                                with logs_area:
                                    ui.html('<div style="color: var(--success);">✓ Plik przesłany pomyślnie. Rozpoczynam przetwarzanie...</div>', sanitize=False)
                                
                                # Śledź postęp zadania
                                await track_task_progress(task_id, status_label, progress_bar, logs_area)
                            else:
                                progress_bar.value = 1.0
                                status_label.text = "Gotowy"
                                progress_bar.visible = False
                                logs_area.visible = False
                        except Exception as ex:
                            status_label.text = f"❌ Błąd: {str(ex)}"
                            progress_bar.visible = False
                            with logs_area:
                                ui.html(f'<div style="color: var(--error);">❌ Błąd: {str(ex)}</div>', sanitize=False)
                            ui.notify(f"Błąd: {str(ex)}", type='negative')
                    
                    async def track_task_progress(task_id: str, status_label, progress_bar, logs_area):
                        """Śledzi postęp zadania przez polling z wyświetlaniem logów."""
                        import asyncio
                        max_attempts = 600  # 10 minut (1 sekunda * 600)
                        attempt = 0
                        last_log_count = 0
                        client_active = True  # Flaga do śledzenia czy klient jest aktywny
                        
                        def safe_ui_update(update_func):
                            """Bezpiecznie wykonuje aktualizację UI, zwraca False jeśli klient został usunięty."""
                            nonlocal client_active
                            if not client_active:
                                return False
                            try:
                                update_func()
                                return True
                            except Exception as e:
                                # Sprawdź czy to błąd związany z usuniętym klientem
                                error_msg = str(e).lower()
                                if "client has been deleted" in error_msg or "client" in error_msg and "deleted" in error_msg:
                                    client_active = False
                                    return False
                                # Inne błędy - loguj ale kontynuuj
                                print(f"UI update warning: {e}")
                                return True
                        
                        while attempt < max_attempts and client_active:
                            try:
                                task_data = await api_call("GET", f"/api/task/{task_id}")
                                status = task_data.get("status", "unknown")
                                progress = task_data.get("progress", 0)
                                message = task_data.get("message", "")
                                recent_logs = task_data.get("recent_logs", [])
                                
                                # Aktualizuj postęp
                                if not safe_ui_update(lambda: setattr(progress_bar, 'value', progress / 100.0 if progress >= 0 else 0)):
                                    break
                                
                                # Aktualizuj status
                                status_emoji = {
                                    "processing": "⏳",
                                    "completed": "✓",
                                    "error": "❌",
                                    "timeout": "⏱️"
                                }.get(status, "⏳")
                                if not safe_ui_update(lambda: setattr(status_label, 'text', f"{status_emoji} {message}")):
                                    break
                                
                                # Dodaj nowe logi
                                if len(recent_logs) > last_log_count:
                                    new_logs = recent_logs[last_log_count:]
                                    for log_entry in new_logs:
                                        log_msg = log_entry.get("message", "")
                                        log_progress = log_entry.get("progress")
                                        log_status = log_entry.get("status")
                                        
                                        # Określ kolor na podstawie typu wiadomości
                                        color = "var(--text-secondary)"
                                        if "BŁĄD" in log_msg.upper() or "ERROR" in log_msg.upper():
                                            color = "var(--error)"
                                        elif "INFO" in log_msg.upper() or "SUKCES" in log_msg.upper() or "✓" in log_msg:
                                            color = "var(--success)"
                                        elif "WARNING" in log_msg.upper() or "OSTRZEŻENIE" in log_msg.upper():
                                            color = "var(--warning)"
                                        elif "OCR" in log_msg.upper():
                                            color = "var(--info)"
                                        
                                        # Formatuj wiadomość
                                        progress_text = f" [{log_progress}%]" if log_progress is not None else ""
                                        formatted_msg = f"{log_msg}{progress_text}"
                                        
                                        # Bezpiecznie dodaj log
                                        def add_log():
                                            with logs_area:
                                                ui.html(f'<div style="color: {color}; margin: 2px 0;">{formatted_msg}</div>', sanitize=False)
                                        
                                        if not safe_ui_update(add_log):
                                            break
                                        
                                        # Przewiń do dołu
                                        safe_ui_update(lambda: ui.run_javascript('''
                                            const logsArea = document.querySelector('.process-logs');
                                            if (logsArea) {
                                                logsArea.scrollTop = logsArea.scrollHeight;
                                            }
                                        '''))
                                    
                                    last_log_count = len(recent_logs)
                                
                                # Sprawdź czy wymagana edycja magazynu
                                if status == "awaiting_inventory_review":
                                    inventory_items = task_data.get("inventory_items", [])
                                    if inventory_items:
                                        if not safe_ui_update(lambda: setattr(status_label, 'text', "📝 Oczekiwanie na edycję produktów do spiżarni")):
                                            break
                                        if not safe_ui_update(lambda: setattr(progress_bar, 'value', 0.95)):
                                            break
                                        
                                        # Pokaż interfejs edycji
                                        try:
                                            await show_inventory_edit_dialog(task_id, inventory_items, status_label, progress_bar, logs_area)
                                        except Exception as e:
                                            if "client has been deleted" in str(e).lower():
                                                client_active = False
                                                break
                                        break
                                
                                # Sprawdź czy zakończone
                                if status in ["completed", "error", "timeout"]:
                                    if status == "completed":
                                        if not safe_ui_update(lambda: setattr(status_label, 'text', "✓ Przetwarzanie zakończone pomyślnie!")):
                                            break
                                        
                                        def add_success_log():
                                            with logs_area:
                                                ui.html('<div style="color: var(--success); font-weight: 600; margin-top: 8px;">✓ ✓ ✓ Paragon został pomyślnie przetworzony i zapisany w bazie danych!</div>', sanitize=False)
                                        
                                        if not safe_ui_update(add_success_log):
                                            break
                                        
                                        safe_ui_update(lambda: ui.notify("Paragon został pomyślnie przetworzony!", type='positive'))
                                        
                                        # Odśwież listę paragonów po 2 sekundach
                                        await asyncio.sleep(2)
                                        safe_ui_update(lambda: ui.run_javascript('location.reload()'))
                                    else:
                                        if not safe_ui_update(lambda: setattr(status_label, 'text', f"❌ {message}")):
                                            break
                                        
                                        def add_error_log():
                                            with logs_area:
                                                ui.html(f'<div style="color: var(--error); font-weight: 600; margin-top: 8px;">❌ Błąd przetwarzania: {message}</div>', sanitize=False)
                                        
                                        if not safe_ui_update(add_error_log):
                                            break
                                        
                                        safe_ui_update(lambda: ui.notify(f"Błąd przetwarzania: {message}", type='negative'))
                                    
                                    safe_ui_update(lambda: setattr(progress_bar, 'value', 1.0 if status == "completed" else 0))
                                    break
                                
                                await asyncio.sleep(1)  # Polling co 1 sekundę
                                attempt += 1
                            except Exception as e:
                                # Sprawdź czy to błąd związany z usuniętym klientem
                                error_msg = str(e).lower()
                                if "client has been deleted" in error_msg:
                                    client_active = False
                                    break
                                
                                # Inne błędy - spróbuj zaktualizować UI
                                def update_error():
                                    status_label.text = f"❌ Błąd śledzenia: {str(e)}"
                                    with logs_area:
                                        ui.html(f'<div style="color: var(--error);">❌ Błąd śledzenia postępu: {str(e)}</div>', sanitize=False)
                                    progress_bar.visible = False
                                
                                if not safe_ui_update(update_error):
                                    break
                                break
                        else:
                            if client_active:
                                def update_timeout():
                                    status_label.text = "⏱️ Przekroczono limit czasu śledzenia"
                                    with logs_area:
                                        ui.html('<div style="color: var(--warning);">⏱️ Przekroczono limit czasu śledzenia postępu</div>', sanitize=False)
                                    progress_bar.visible = False
                                
                                safe_ui_update(update_timeout)
                    
                    with ui.column().classes('upload-area'):
                        file_upload = ui.upload(
                            label='Wybierz plik paragonu (PNG, JPG, PDF)',
                            auto_upload=True,
                            on_upload=handle_upload_wrapper,
                        ).props('accept=".png,.jpg,.jpeg,.pdf"').style('width: 100%;')
                
                # Statystyki
                with ui.row().classes('w-full gap-4'):
                    try:
                        stats = await api_call("GET", "/api/stats")
                        total_stats = stats.get("total_statistics", {})
                        
                        with ui.card().classes('stat-card primary'):
                            ui.label('📊').classes('stat-icon')
                            ui.label(f'{total_stats.get("total_receipts", 0)}').classes('stat-value')
                            ui.label('Paragonów').classes('stat-label')
                        
                        with ui.card().classes('stat-card success'):
                            ui.label('💰').classes('stat-icon')
                            ui.label(f'{total_stats.get("total_spent", 0):.2f} PLN').classes('stat-value')
                            ui.label('Wydatki').classes('stat-label')
                        
                        with ui.card().classes('stat-card warning'):
                            ui.label('🛒').classes('stat-icon')
                            ui.label(f'{total_stats.get("total_items", 0)}').classes('stat-value')
                            ui.label('Pozycji').classes('stat-label')
                    except Exception as e:
                        ui.label(f'Błąd podczas ładowania statystyk: {str(e)}').style('color: var(--error);')
                
                # Ostatnie paragony
                with ui.card():
                    ui.label('Ostatnie paragony').classes('card-title')
                    
                    try:
                        receipts = await api_call("GET", "/api/receipts?limit=10")
                        receipt_list = receipts.get("receipts", [])
                        
                        if receipt_list:
                            with ui.column().classes('table-container'):
                                table_html = '''
                                    <table style="width: 100%; border-collapse: collapse;">
                                        <thead>
                                            <tr>
                                                <th>Data</th>
                                                <th>Sklep</th>
                                                <th>Suma</th>
                                                <th>Pozycje</th>
                                                <th>Akcje</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                '''
                                for r in receipt_list:
                                    receipt_id = r['paragon_id']
                                    table_html += f'''
                                        <tr>
                                            <td>{r['data_zakupu']}</td>
                                            <td>{r['sklep']}</td>
                                            <td><strong>{r['suma_paragonu']:.2f} PLN</strong></td>
                                            <td>{r['liczba_pozycji']}</td>
                                            <td><a href="/paragon/{receipt_id}" style="color: var(--primary); text-decoration: none;">📝 Szczegóły</a></td>
                                        </tr>
                                    '''
                                table_html += '</tbody></table>'
                                ui.html(table_html, sanitize=False)
                        else:
                            ui.label('Brak paragonów. Dodaj pierwszy paragon!').style('color: var(--text-secondary); text-align: center; padding: 40px;')
                    except Exception as e:
                        ui.label(f'Błąd podczas ładowania paragonów: {str(e)}').style('color: var(--error);')
    
    # Dark mode toggle
    create_dark_mode_toggle()


@ui.page('/magazyn')
async def inventory_page():
    """Strona spiżarni."""
    setup_dark_mode_script()
    setup_styles()
    
    with ui.row().classes('app-container'):
        create_sidebar('/magazyn')
        
        with ui.column().classes('main-content'):
            with ui.column().classes('container'):
                ui.label('📦 Spiżarnia').classes('page-header')
                
                try:
                    inventory_data = await api_call("GET", "/api/inventory")
                    items = inventory_data.get("inventory", [])
                    
                    if items:
                        with ui.card():
                            ui.label('Stan spiżarni').classes('card-title')
                            
                            with ui.column().classes('table-container'):
                                table_html = '''
                                    <table style="width: 100%; border-collapse: collapse;">
                                        <thead>
                                            <tr>
                                                <th>Produkt</th>
                                                <th>Ilość</th>
                                                <th>Jednostka</th>
                                                <th>Data ważności</th>
                                                <th>Kategoria</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                '''
                                for item in items:
                                    table_html += f'''
                                        <tr>
                                            <td><strong>{item['nazwa']}</strong></td>
                                            <td>{item['ilosc']}</td>
                                            <td>{item['jednostka']}</td>
                                            <td>{item['data_waznosci'] or '—'}</td>
                                            <td>{item['kategoria'] or '—'}</td>
                                        </tr>
                                    '''
                                table_html += '</tbody></table>'
                                ui.html(table_html, sanitize=False)
                    else:
                        with ui.card():
                            ui.label('Spiżarnia jest pusta. Dodaj paragony, aby wypełnić spiżarnię!').style('color: var(--text-secondary); text-align: center; padding: 40px;')
                except Exception as e:
                    ui.label(f'Błąd podczas ładowania spiżarni: {str(e)}').style('color: var(--error);')
    
    create_dark_mode_toggle()


@ui.page('/bielik')
async def bielik_page():
    """Strona czatu z Bielikiem."""
    setup_dark_mode_script()
    setup_styles()
    
    with ui.row().classes('app-container'):
        create_sidebar('/bielik')
        
        with ui.column().classes('main-content'):
            with ui.column().classes('container'):
                ui.label('🦅 Bielik - Asystent Kulinarny').classes('page-header')
                
                with ui.card():
                    ui.label('Czat z Bielikiem').classes('card-title')
                    
                    chat_container = ui.column().classes('chat-container')
                    
                    # Wiadomość powitalna
                    with chat_container:
                        with ui.html('<div class="chat-message bot">🦅 Cześć! Jestem Bielik, Twój asystent kulinarny. Jak mogę Ci pomóc?</div>', sanitize=False):
                            pass
                    
                    async def send_message():
                        question = input_field.value
                        if not question.strip():
                            return
                        
                        # Dodaj wiadomość użytkownika
                        with chat_container:
                            with ui.html(f'<div class="chat-message user"><strong>Ty:</strong> {question}</div>', sanitize=False):
                                pass
                        
                        input_field.value = ""
                        
                        # Pokaż wskaźnik ładowania
                        loading_msg = None
                        with chat_container:
                            loading_msg = ui.html('<div class="chat-message bot">⏳ Bielik myśli...</div>', sanitize=False)
                        
                        # Wyślij do API
                        try:
                            response = await api_call("POST", "/api/chat", {"question": question})
                            answer = response.get("answer", "Przepraszam, nie mogę odpowiedzieć.")
                            
                            # Usuń wskaźnik ładowania i dodaj odpowiedź
                            loading_msg.delete()
                            with chat_container:
                                with ui.html(f'<div class="chat-message bot"><strong>🦅 Bielik:</strong> {answer}</div>', sanitize=False):
                                    pass
                            
                            # Przewiń do dołu
                            ui.run_javascript('''
                                const container = document.querySelector('.chat-container');
                                container.scrollTop = container.scrollHeight;
                            ''')
                        except Exception as e:
                            loading_msg.delete()
                            with chat_container:
                                with ui.html(f'<div class="chat-message bot" style="background: var(--error);"><strong>❌ Błąd:</strong> {str(e)}</div>', sanitize=False):
                                    pass
                    
                    with ui.row().classes('w-full gap-2').style('margin-top: 16px;'):
                        input_field = ui.input('Zadaj pytanie Bielikowi...').classes('flex-1').props('autofocus')
                        input_field.on('keydown.enter', send_message)
                        
                        ui.button('Wyślij ➤', on_click=send_message).classes('btn-primary')
    
    create_dark_mode_toggle()


@ui.page('/paragon/{receipt_id}')
async def receipt_detail_page(receipt_id: int):
    """Strona szczegółów paragonu z możliwością edycji."""
    setup_dark_mode_script()
    setup_styles()
    
    with ui.row().classes('app-container'):
        create_sidebar('/')
        
        with ui.column().classes('main-content'):
            with ui.column().classes('container'):
                ui.label('📄 Szczegóły paragonu').classes('page-header')
                
                try:
                    receipt = await api_call("GET", f"/api/receipts/{receipt_id}")
                    
                    # Informacje o paragonie
                    with ui.card():
                        ui.label('Informacje o paragonie').classes('card-title')
                        
                        # Pobierz listę sklepów
                        stores_data = await api_call("GET", "/api/stores")
                        stores = stores_data.get("stores", [])
                        store_options = {s["nazwa_sklepu"]: s["sklep_id"] for s in stores}
                        
                        with ui.row().classes('w-full gap-4'):
                            sklep_select = ui.select(
                                options=store_options,
                                label='Sklep',
                                value=receipt.get("sklep_id")
                            ).classes('flex-1')
                            
                            # Pobierz datę z paragonu
                            receipt_date = receipt.get("data_zakupu")
                            if receipt_date:
                                # Jeśli data jest w formacie ISO string, użyj jej bezpośrednio
                                if isinstance(receipt_date, str):
                                    data_input = ui.input(
                                        label='Data zakupu (YYYY-MM-DD)',
                                        value=receipt_date
                                    ).classes('flex-1')
                                else:
                                    data_input = ui.input(
                                        label='Data zakupu (YYYY-MM-DD)',
                                        value=str(receipt_date)
                                    ).classes('flex-1')
                            else:
                                data_input = ui.input(
                                    label='Data zakupu (YYYY-MM-DD)',
                                    value=''
                                ).classes('flex-1')
                            
                            suma_input = ui.number(
                                label='Suma paragonu',
                                value=float(receipt.get("suma_paragonu", 0)),
                                format='%.2f'
                            ).classes('flex-1')
                        
                        async def save_receipt():
                            try:
                                from datetime import datetime
                                # Waliduj i przekonwertuj datę
                                date_value = None
                                if data_input.value:
                                    try:
                                        # Spróbuj sparsować datę
                                        date_value = datetime.strptime(data_input.value, "%Y-%m-%d").date()
                                    except ValueError:
                                        ui.notify("❌ Nieprawidłowy format daty. Użyj YYYY-MM-DD", type='negative')
                                        return
                                
                                update_data = {
                                    "sklep_id": sklep_select.value,
                                    "suma_paragonu": float(suma_input.value) if suma_input.value else 0,
                                }
                                if date_value:
                                    update_data["data_zakupu"] = date_value.isoformat()
                                
                                await api_call("PUT", f"/api/receipts/{receipt_id}", update_data)
                                ui.notify("✓ Paragon zaktualizowany!", type='positive')
                            except Exception as e:
                                ui.notify(f"❌ Błąd: {str(e)}", type='negative')
                        
                        async def delete_receipt():
                            try:
                                await api_call("DELETE", f"/api/receipts/{receipt_id}")
                                ui.notify("✓ Paragon usunięty!", type='positive')
                                ui.run_javascript('window.location.href = "/"')
                            except Exception as e:
                                ui.notify(f"❌ Błąd: {str(e)}", type='negative')
                        
                        with ui.row().classes('w-full gap-2').style('margin-top: 16px;'):
                            ui.button('💾 Zapisz zmiany', on_click=save_receipt).classes('btn-primary')
                            ui.button('🗑️ Usuń paragon', on_click=delete_receipt).style('background: var(--error); color: white;')
                    
                    # Pozycje paragonu
                    with ui.card():
                        ui.label('Pozycje paragonu').classes('card-title')
                        
                        pozycje = receipt.get("pozycje", [])
                        if pozycje:
                            # Pobierz listę produktów
                            products_data = await api_call("GET", "/api/products")
                            products = products_data.get("products", [])
                            product_options = {p["nazwa"]: p["produkt_id"] for p in products}
                            
                            with ui.column().classes('table-container'):
                                table_html = '''
                                    <table style="width: 100%; border-collapse: collapse;">
                                        <thead>
                                            <tr>
                                                <th>Nazwa (raw)</th>
                                                <th>Produkt</th>
                                                <th>Ilość</th>
                                                <th>Cena jedn.</th>
                                                <th>Wartość</th>
                                                <th>Akcje</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                '''
                                for pozycja in pozycje:
                                    pozycja_id = pozycja['pozycja_id']
                                    nazwa_znormalizowana = pozycja.get('nazwa_znormalizowana', '—')
                                    table_html += f'''
                                        <tr id="item-{pozycja_id}">
                                            <td>{pozycja['nazwa_z_paragonu_raw']}</td>
                                            <td>{nazwa_znormalizowana}</td>
                                            <td>{pozycja['ilosc']} {pozycja.get('jednostka_miary', '')}</td>
                                            <td>{pozycja.get('cena_jednostkowa', 0):.2f} PLN</td>
                                            <td><strong>{pozycja['cena_calkowita']:.2f} PLN</strong></td>
                                            <td>
                                                <button onclick="editItem({pozycja_id}, {receipt_id})" style="background: var(--primary); color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">✏️</button>
                                                <button onclick="deleteItem({pozycja_id}, {receipt_id})" style="background: var(--error); color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; margin-left: 4px;">🗑️</button>
                                            </td>
                                        </tr>
                                    '''
                                table_html += '</tbody></table>'
                                ui.html(table_html, sanitize=False)
                                
                                # JavaScript do edycji/usuwania pozycji
                                ui.add_head_html(f'''
                                <script>
                                async function editItem(itemId, receiptId) {{
                                    // Prosty prompt do edycji - można rozbudować o modal
                                    const newQty = prompt("Nowa ilość:", "");
                                    if (newQty !== null && newQty !== "") {{
                                        try {{
                                            const response = await fetch(`${{API_URL}}/api/receipts/${{receiptId}}/items/${{itemId}}`, {{
                                                method: 'PUT',
                                                headers: {{ 'Content-Type': 'application/json' }},
                                                body: JSON.stringify({{ ilosc: parseFloat(newQty) }})
                                            }});
                                            if (response.ok) {{
                                                alert("✓ Pozycja zaktualizowana!");
                                                location.reload();
                                            }} else {{
                                                const error = await response.json();
                                                alert("❌ Błąd: " + error.detail);
                                            }}
                                        }} catch (e) {{
                                            alert("❌ Błąd: " + e.message);
                                        }}
                                    }}
                                }}
                                
                                async function deleteItem(itemId, receiptId) {{
                                    if (!confirm("Czy na pewno chcesz usunąć tę pozycję?")) return;
                                    try {{
                                        const response = await fetch(`${{API_URL}}/api/receipts/${{receiptId}}/items/${{itemId}}`, {{
                                            method: 'DELETE'
                                        }});
                                        if (response.ok) {{
                                            alert("✓ Pozycja usunięta!");
                                            location.reload();
                                        }} else {{
                                            const error = await response.json();
                                            alert("❌ Błąd: " + error.detail);
                                        }}
                                    }} catch (e) {{
                                        alert("❌ Błąd: " + e.message);
                                    }}
                                }}
                                </script>
                                '''.replace('${API_URL}', API_URL))
                        else:
                            ui.label('Brak pozycji w paragonie.').style('color: var(--text-secondary); text-align: center; padding: 40px;')
                    
                except Exception as e:
                    ui.label(f'Błąd podczas ładowania paragonu: {str(e)}').style('color: var(--error);')
                    if "404" in str(e):
                        ui.link('← Powrót do listy', '/').style('margin-top: 20px; color: var(--primary);')
    
    create_dark_mode_toggle()


@ui.page('/ustawienia')
async def settings_page():
    """Strona ustawień."""
    setup_dark_mode_script()
    setup_styles()
    
    with ui.row().classes('app-container'):
        create_sidebar('/ustawienia')
        
        with ui.column().classes('main-content'):
            with ui.column().classes('container'):
                ui.label('⚙️ Ustawienia').classes('page-header')
                
                try:
                    settings = await api_call("GET", "/api/settings")
                    
                    with ui.card():
                        ui.label('Tryb działania').classes('card-title')
                        
                        # W wersji webowej zawsze używamy Cloud (Mistral OCR + OpenAI API)
                        ui.label('✓ Cloud AI (OpenAI) - zawsze włączone').style('margin: 12px 0; color: var(--text-secondary);')
                        ui.label('✓ Cloud OCR (Mistral) - zawsze włączone').style('margin: 12px 0; color: var(--text-secondary);')
                        ui.label('Wersja webowa działa wyłącznie z Mistral OCR i OpenAI API.').style('margin: 12px 0; font-size: 0.9em; color: var(--text-secondary);')
                    
                    with ui.card():
                        ui.label('Klucze API').classes('card-title')
                        
                        openai_key = ui.input(
                            'OpenAI API Key',
                            placeholder='sk-...',
                            password=True
                        ).classes('w-full').style('margin: 8px 0;')
                        
                        if settings.get("openai_api_key_set"):
                            ui.label('✓ Klucz OpenAI jest ustawiony').style('color: var(--success); font-size: 0.9em; margin: 4px 0;')
                        
                        mistral_key = ui.input(
                            'Mistral API Key',
                            placeholder='...',
                            password=True
                        ).classes('w-full').style('margin: 8px 0;')
                        
                        if settings.get("mistral_api_key_set"):
                            ui.label('✓ Klucz Mistral jest ustawiony').style('color: var(--success); font-size: 0.9em; margin: 4px 0;')
                        
                        async def save_settings():
                            update_data = {
                                # W wersji webowej zawsze wymuszamy Cloud
                                "use_cloud_ai": True,
                                "use_cloud_ocr": True,
                            }
                            
                            if openai_key.value:
                                update_data["openai_api_key"] = openai_key.value
                            
                            if mistral_key.value:
                                update_data["mistral_api_key"] = mistral_key.value
                            
                            try:
                                await api_call("POST", "/api/settings", update_data)
                                ui.notify("✓ Ustawienia zapisane!", type='positive', timeout=3000)
                            except Exception as e:
                                ui.notify(f"❌ Błąd: {str(e)}", type='negative', timeout=5000)
                        
                        ui.button('💾 Zapisz ustawienia', on_click=save_settings).classes('btn-primary').style('margin-top: 20px;')
                except Exception as e:
                    ui.label(f'Błąd podczas ładowania ustawień: {str(e)}').style('color: var(--error);')
    
    create_dark_mode_toggle()


async def show_inventory_edit_dialog(task_id: str, inventory_items: list, status_label, progress_bar, logs_area):
    """Pokazuje dialog edycji produktów przed dodaniem do spiżarni."""
    dialog = ui.dialog()
    dialog.classes('w-full max-w-4xl')
    
    with dialog:
        with ui.card().classes('w-full'):
            ui.label('📦 Edycja produktów przed dodaniem do spiżarni').classes('text-2xl font-bold mb-4')
            ui.label('Sprawdź i edytuj produkty przed dodaniem do spiżarni:').classes('text-lg mb-4')
            
            # Tabelka edycji
            edit_items = []
            with ui.column().classes('w-full gap-2'):
                for item in inventory_items:
                    with ui.row().classes('w-full items-center gap-4 p-3 border rounded'):
                        # Nazwa produktu (nieedytowalna)
                        ui.label(item['nazwa']).classes('flex-1 font-semibold')
                        
                        # Ilość
                        ilosc_input = ui.number(
                            label='Ilość',
                            value=item['ilosc'],
                            format='%.2f'
                        ).classes('w-32')
                        
                        # Jednostka
                        jednostka_input = ui.input(
                            label='Jednostka',
                            value=item.get('jednostka', 'szt')
                        ).classes('w-32')
                        
                        # Data ważności
                        data_waznosci = item.get('data_waznosci')
                        data_input = ui.input(
                            label='Data ważności (YYYY-MM-DD)',
                            value=data_waznosci or ''
                        ).classes('w-40')
                        
                        edit_items.append({
                            'produkt_id': item['produkt_id'],
                            'ilosc_input': ilosc_input,
                            'jednostka_input': jednostka_input,
                            'data_input': data_input,
                        })
            
            # Przyciski
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                async def confirm_edit():
                    try:
                        # Przygotuj dane do zapisu
                        items_to_save = []
                        for edit_item in edit_items:
                            ilosc = edit_item['ilosc_input'].value
                            jednostka = edit_item['jednostka_input'].value or 'szt'
                            data_waznosci = edit_item['data_input'].value or None
                            
                            items_to_save.append({
                                'produkt_id': edit_item['produkt_id'],
                                'ilosc': float(ilosc) if ilosc else 0,
                                'jednostka': jednostka,
                                'data_waznosci': data_waznosci,
                            })
                        
                        # Wyślij do API
                        await api_call("POST", "/api/inventory/confirm", {
                            "task_id": task_id,
                            "items": items_to_save
                        })
                        
                        # Bezpiecznie zaktualizuj UI
                        try:
                            dialog.close()
                            status_label.text = "✓ Produkty dodane do spiżarni!"
                            progress_bar.value = 1.0
                            with logs_area:
                                ui.html('<div style="color: var(--success); font-weight: 600; margin-top: 8px;">✓ ✓ ✓ Produkty zostały dodane do spiżarni!</div>', sanitize=False)
                            ui.notify("Produkty zostały dodane do spiżarni!", type='positive')
                            
                            # Odśwież stronę po 2 sekundach
                            await asyncio.sleep(2)
                            ui.run_javascript('location.reload()')
                        except Exception as ui_error:
                            # Jeśli klient został usunięty, po prostu zignoruj błąd UI
                            if "client has been deleted" not in str(ui_error).lower():
                                raise
                    except Exception as e:
                        try:
                            ui.notify(f"Błąd podczas zapisu: {str(e)}", type='negative')
                        except:
                            # Ignoruj błędy UI jeśli klient został usunięty
                            pass
                
                ui.button('✓ Zatwierdź i dodaj do spiżarni', on_click=confirm_edit).classes('btn-primary')
                ui.button('Anuluj', on_click=dialog.close).style('background: var(--error); color: white;')
    
    dialog.open()


async def handle_upload(e):
    """Obsługuje upload pliku w NiceGUI."""
    try:
        # Pobierz nazwę pliku z rozszerzeniem
        file_name = getattr(e, 'name', None)
        file_type = getattr(e, 'type', 'application/pdf')
        
        # Mapowanie typu MIME do rozszerzeń
        mime_to_ext = {
            'application/pdf': '.pdf',
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
        }
        
        # Jeśli brak nazwy lub nazwa bez rozszerzenia, użyj typu MIME
        if not file_name or file_name == 'paragon':
            ext = mime_to_ext.get(file_type, '.pdf')
            file_name = f'paragon{ext}'
        elif not Path(file_name).suffix:
            # Jeśli nazwa istnieje ale brak rozszerzenia, dodaj na podstawie typu MIME
            ext = mime_to_ext.get(file_type, '.pdf')
            file_name = f"{file_name}{ext}"
        
        print(f"DEBUG UPLOAD: file_name={file_name}, type={file_type}")
        
        # Weryfikacja obiektu pliku (kompatybilność wsteczna NiceGUI)
        if hasattr(e, 'content'):
            file_obj = e.content
        elif hasattr(e, 'file'):
            file_obj = e.file
        else:
            raise Exception("Nie znaleziono zawartości pliku")

        # --- ZABEZPIECZENIE PRZED OOM (Out Of Memory) ---
        # Sprawdzamy rozmiar PRZED wczytaniem do RAM
        try:
            file_obj.seek(0, 2)  # Idź na koniec
            size = file_obj.tell()  # Sprawdź pozycję
            file_obj.seek(0)  # Wróć na początek
            
            MAX_SIZE_MB = 50
            if size > MAX_SIZE_MB * 1024 * 1024:
                ui.notify(f"Plik jest za duży (> {MAX_SIZE_MB}MB). Odrzucono.", type='negative')
                return None
        except (AttributeError, ValueError):
            # Jeśli obiekt nie obsługuje seek, ryzykujemy
            pass

        # --- KLUCZOWA POPRAWKA ASYNC ---
        # Musi być await, inaczej leci RuntimeWarning i błąd 400
        file_content = await file_obj.read()
        
        if not file_content:
            raise Exception("Pusty plik")

        # Wyślij do API z timeoutem (bo duże pliki idą długo)
        timeout = httpx.Timeout(60.0, connect=10.0) 
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Jawnie podajemy typ content-type, żeby FastAPI nie zgłupiało
            files = {"file": (file_name, file_content, getattr(e, 'type', 'application/pdf'))}
            response = await client.post(f"{API_URL}/api/upload", files=files)
            
            if response.status_code == 400:
                error_detail = response.json().get('detail', 'Błąd walidacji')
                raise Exception(f"Backend odrzucił plik: {error_detail}")
                
            response.raise_for_status()
            result = response.json()
        
        return result.get("task_id")

    except Exception as ex:
        print(f"UPLOAD ERROR: {str(ex)}")  # Log do konsoli Dockera
        ui.notify(f"Błąd przesyłania: {str(ex)}", type='negative')
        return None




if __name__ in {"__main__", "__mp_main__"}:
    # Port 8081, bo 8080 jest zajęty przez open-webui
    ui.run(port=8081, title="ParagonWeb")

