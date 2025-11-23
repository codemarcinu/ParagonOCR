"""
NiceGUI frontend dla ParagonWeb.

Prosty, nowoczesny interfejs webowy dla osoby nietechnicznej.
"""

import os
import sys
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

def setup_styles(dark_mode: bool = False):
    """Konfiguruje style CSS dla aplikacji."""
    bg_color = AppColors.BG_DARK if dark_mode else AppColors.BG_LIGHT
    card_color = AppColors.CARD_DARK if dark_mode else AppColors.CARD_LIGHT
    text_primary = AppColors.TEXT_DARK if dark_mode else AppColors.TEXT_PRIMARY
    text_secondary = AppColors.TEXT_SECONDARY
    
    ui.add_head_html(f"""
    <style>
        :root {{
            --primary: {AppColors.PRIMARY};
            --primary-dark: {AppColors.PRIMARY_DARK};
            --primary-light: {AppColors.PRIMARY_LIGHT};
            --success: {AppColors.SUCCESS};
            --warning: {AppColors.WARNING};
            --error: {AppColors.ERROR};
            --bg: {bg_color};
            --card: {card_color};
            --text-primary: {text_primary};
            --text-secondary: {text_secondary};
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
            else:
                raise ValueError(f"Nieobsługiwana metoda: {method}")
            
            response.raise_for_status()
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
            ('/magazyn', '📦', 'Magazyn'),
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
        if (localStorage.getItem('darkMode') === 'true') {
            document.body.classList.add('dark-mode');
        }
    </script>
    ''')

def toggle_dark_mode():
    """Przełącza tryb ciemny."""
    ui.run_javascript('''
        const isDark = document.body.classList.toggle('dark-mode');
        localStorage.setItem('darkMode', isDark);
        location.reload();
    ''')


# --- Strony ---

@ui.page('/')
async def dashboard():
    """Strona główna - Dashboard."""
    setup_dark_mode_script()
    setup_styles(False)  # Dark mode jest obsługiwany przez CSS i JavaScript
    
    with ui.row().classes('app-container'):
        create_sidebar('/')
        
        with ui.column().classes('main-content'):
            with ui.column().classes('container'):
                ui.label('📄 Dashboard').classes('page-header')
                
                # Przycisk dodawania paragonu
                with ui.card():
                    ui.label('Dodaj nowy paragon').classes('card-title')
                    
                    status_label = ui.label('Gotowy').style('margin-top: 10px; color: var(--text-secondary);')
                    progress_bar = ui.linear_progress(value=0).style('margin-top: 10px;')
                    
                    async def handle_upload_wrapper(e):
                        """Wrapper dla handle_upload."""
                        status_label.text = f"Przesyłanie {e.name}..."
                        progress_bar.value = 0.3
                        await handle_upload(e)
                        progress_bar.value = 1.0
                        status_label.text = "Gotowy"
                    
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
                                            </tr>
                                        </thead>
                                        <tbody>
                                '''
                                for r in receipt_list:
                                    table_html += f'''
                                        <tr>
                                            <td>{r['data_zakupu']}</td>
                                            <td>{r['sklep']}</td>
                                            <td><strong>{r['suma_paragonu']:.2f} PLN</strong></td>
                                            <td>{r['liczba_pozycji']}</td>
                                        </tr>
                                    '''
                                table_html += '</tbody></table>'
                                ui.html(table_html)
                        else:
                            ui.label('Brak paragonów. Dodaj pierwszy paragon!').style('color: var(--text-secondary); text-align: center; padding: 40px;')
                    except Exception as e:
                        ui.label(f'Błąd podczas ładowania paragonów: {str(e)}').style('color: var(--error);')
    
    # Dark mode toggle
    ui.button('🌙', on_click=toggle_dark_mode).classes('dark-mode-toggle')


@ui.page('/magazyn')
async def inventory_page():
    """Strona magazynu."""
    setup_dark_mode_script()
    setup_styles(False)
    
    with ui.row().classes('app-container'):
        create_sidebar('/magazyn')
        
        with ui.column().classes('main-content'):
            with ui.column().classes('container'):
                ui.label('📦 Magazyn').classes('page-header')
                
                try:
                    inventory_data = await api_call("GET", "/api/inventory")
                    items = inventory_data.get("inventory", [])
                    
                    if items:
                        with ui.card():
                            ui.label('Stan magazynu').classes('card-title')
                            
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
                                ui.html(table_html)
                    else:
                        with ui.card():
                            ui.label('Magazyn jest pusty. Dodaj paragony, aby wypełnić magazyn!').style('color: var(--text-secondary); text-align: center; padding: 40px;')
                except Exception as e:
                    ui.label(f'Błąd podczas ładowania magazynu: {str(e)}').style('color: var(--error);')
    
    ui.button('🌙', on_click=toggle_dark_mode).classes('dark-mode-toggle')


@ui.page('/bielik')
async def bielik_page():
    """Strona czatu z Bielikiem."""
    setup_dark_mode_script()
    setup_styles(False)
    
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
                        with ui.html('<div class="chat-message bot">🦅 Cześć! Jestem Bielik, Twój asystent kulinarny. Jak mogę Ci pomóc?</div>'):
                            pass
                    
                    async def send_message():
                        question = input_field.value
                        if not question.strip():
                            return
                        
                        # Dodaj wiadomość użytkownika
                        with chat_container:
                            with ui.html(f'<div class="chat-message user"><strong>Ty:</strong> {question}</div>'):
                                pass
                        
                        input_field.value = ""
                        
                        # Pokaż wskaźnik ładowania
                        loading_msg = None
                        with chat_container:
                            loading_msg = ui.html('<div class="chat-message bot">⏳ Bielik myśli...</div>')
                        
                        # Wyślij do API
                        try:
                            response = await api_call("POST", "/api/chat", {"question": question})
                            answer = response.get("answer", "Przepraszam, nie mogę odpowiedzieć.")
                            
                            # Usuń wskaźnik ładowania i dodaj odpowiedź
                            loading_msg.delete()
                            with chat_container:
                                with ui.html(f'<div class="chat-message bot"><strong>🦅 Bielik:</strong> {answer}</div>'):
                                    pass
                            
                            # Przewiń do dołu
                            ui.run_javascript('''
                                const container = document.querySelector('.chat-container');
                                container.scrollTop = container.scrollHeight;
                            ''')
                        except Exception as e:
                            loading_msg.delete()
                            with chat_container:
                                with ui.html(f'<div class="chat-message bot" style="background: var(--error);"><strong>❌ Błąd:</strong> {str(e)}</div>'):
                                    pass
                    
                    with ui.row().classes('w-full gap-2').style('margin-top: 16px;'):
                        input_field = ui.input('Zadaj pytanie Bielikowi...').classes('flex-1').props('autofocus')
                        input_field.on('keydown.enter', send_message)
                        
                        ui.button('Wyślij ➤', on_click=send_message).classes('btn-primary')
    
    ui.button('🌙', on_click=toggle_dark_mode).classes('dark-mode-toggle')


@ui.page('/ustawienia')
async def settings_page():
    """Strona ustawień."""
    setup_dark_mode_script()
    setup_styles(False)
    
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
    
    ui.button('🌙', on_click=toggle_dark_mode).classes('dark-mode-toggle')


async def handle_upload(e):
    """Obsługuje upload pliku."""
    try:
        # NiceGUI: e.name zawiera tylko nazwę pliku, nie ścieżkę
        # e.content jest file-like obiektem z danymi pliku
        file_name = e.name
        file_content = await e.content.read()
        
        # Wyślij do API używając httpx z timeout (spójnie z api_call)
        timeout = httpx.Timeout(30.0, connect=10.0)  # 30s timeout, 10s na połączenie
        async with httpx.AsyncClient(timeout=timeout) as client:
            files = {"file": (file_name, file_content, e.type)}
            response = await client.post(f"{API_URL}/api/upload", files=files)
            response.raise_for_status()
            result = response.json()
        
        task_id = result.get("task_id")
        ui.notify(f"Plik {file_name} został przesłany! ID zadania: {task_id}", type='positive')
        
        # Można tutaj dodać śledzenie postępu zadania
        # np. przez polling /api/task/{task_id}
    except Exception as ex:
        ui.notify(f"Błąd podczas przesyłania pliku: {str(ex)}", type='negative')




if __name__ in {"__main__", "__mp_main__"}:
    # Port 8081, bo 8080 jest zajęty przez open-webui
    ui.run(port=8081, title="ParagonWeb")

