"""
Nowoczesny interfejs użytkownika dla ParagonWeb - "Spiżarnia AI"

Mobile-first design z kartami, ikonami i gestami.
Paleta kolorów: szałwiowa zieleń, ciepły beż, terracotta.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime, date, timedelta

from nicegui import ui, app
import httpx

# Dodaj ReceiptParser do ścieżki
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ReceiptParser'))

# URL API
API_URL = os.getenv("API_URL", "http://localhost:8000")


# --- Nowoczesna Paleta Kolorów (KitchenOS Theme) ---
class Theme:
    """Paleta kolorów w stylu organicznym - szałwiowa zieleń, beż, terracotta."""
    # Kolory główne
    BG_MAIN = 'bg-slate-50'  # Bardzo jasny szary, czysty
    SURFACE = 'bg-white shadow-sm rounded-xl'  # Karty
    PRIMARY = 'bg-emerald-600'  # Nowoczesna zieleń
    PRIMARY_HOVER = 'hover:bg-emerald-700'
    PRIMARY_LIGHT = 'bg-emerald-50 text-emerald-700'
    
    # Kolory akcentów
    ACCENT_WARN = 'bg-orange-100 text-orange-700 border-orange-200'  # Terracotta dla ostrzeżeń
    ACCENT_BAD = 'bg-red-100 text-red-700 border-red-200'
    ACCENT_GOOD = 'bg-green-100 text-green-700 border-green-200'
    
    # Tekst
    TEXT_MAIN = 'text-slate-800'
    TEXT_MUTED = 'text-slate-500'
    TEXT_LIGHT = 'text-slate-400'
    
    # Kolory kategorii (emoji-based)
    CATEGORY_COLORS = {
        'Nabiał': 'bg-blue-50 border-blue-200',
        'Warzywa': 'bg-green-50 border-green-200',
        'Owoce': 'bg-yellow-50 border-yellow-200',
        'Mięso': 'bg-red-50 border-red-200',
        'Pieczywo': 'bg-amber-50 border-amber-200',
        'Inne': 'bg-gray-50 border-gray-200',
    }


# --- Funkcje pomocnicze API ---
async def api_call(method: str, endpoint: str, data: Optional[dict] = None, files: Optional[dict] = None):
    """Wykonuje wywołanie API z obsługą błędów."""
    url = f"{API_URL}{endpoint}"
    timeout = httpx.Timeout(30.0, connect=10.0)
    
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


# --- Komponenty UI ---
def get_category_emoji(kategoria: Optional[str]) -> str:
    """Zwraca emoji dla kategorii produktu."""
    if not kategoria:
        return "📦"
    
    emoji_map = {
        'Nabiał': '🥛',
        'Warzywa': '🥦',
        'Owoce': '🍎',
        'Mięso': '🥩',
        'Pieczywo': '🍞',
        'Słodycze': '🍫',
        'Napoje': '🥤',
        'Chemia': '🧴',
    }
    return emoji_map.get(kategoria, '📦')


def get_freshness_color(days_left: int) -> tuple[str, str]:
    """
    Zwraca kolor paska świeżości na podstawie liczby dni do końca.
    Returns: (bg_color, border_color)
    """
    if days_left < 0:
        return ('bg-red-500', 'border-red-600')  # Przeterminowane
    elif days_left <= 3:
        return ('bg-orange-500', 'border-orange-600')  # Wkrótce przeterminowane
    elif days_left <= 7:
        return ('bg-yellow-400', 'border-yellow-500')  # Tydzień do końca
    else:
        return ('bg-green-500', 'border-green-600')  # OK


def calculate_freshness_percentage(data_waznosci: Optional[str], typical_shelf_life_days: int = 14) -> tuple[int, int]:
    """
    Oblicza procent świeżości produktu.
    Returns: (percentage 0-100, days_left)
    """
    if not data_waznosci:
        return (100, 999)  # Brak daty = zawsze świeże
    
    try:
        expiry_date = datetime.fromisoformat(data_waznosci).date() if isinstance(data_waznosci, str) else data_waznosci
        today = date.today()
        days_left = (expiry_date - today).days
        
        if days_left < 0:
            return (0, days_left)  # Przeterminowane
        
        # Zakładamy typowy okres przydatności (np. 14 dni)
        # Jeśli produkt ma więcej niż typowy okres, traktujemy jako 100%
        if days_left >= typical_shelf_life_days:
            return (100, days_left)
        
        # Oblicz procent: (dni_pozostałe / typowy_okres) * 100
        percentage = max(0, min(100, int((days_left / typical_shelf_life_days) * 100)))
        return (percentage, days_left)
    except:
        return (100, 999)


def format_date_relative(data_str: Optional[str]) -> str:
    """Formatuje datę w sposób relatywny (dzisiaj, jutro, za X dni)."""
    if not data_str:
        return "—"
    
    try:
        expiry_date = datetime.fromisoformat(data_str).date() if isinstance(data_str, str) else data_str
        today = date.today()
        delta = (expiry_date - today).days
        
        if delta < 0:
            return f"Przeterminowane ({abs(delta)} dni temu)"
        elif delta == 0:
            return "Dzisiaj!"
        elif delta == 1:
            return "Jutro!"
        elif delta <= 7:
            return f"Za {delta} dni"
        else:
            return expiry_date.strftime("%d.%m.%Y")
    except:
        return data_str if isinstance(data_str, str) else "—"


def create_compact_product_card(item):
    """Tworzy kompaktową kartę produktu dla dashboardu."""
    kategoria = item.get('kategoria', 'Inne')
    emoji = get_category_emoji(kategoria)
    
    # Oblicz świeżość
    freshness_pct, days_left = calculate_freshness_percentage(item.get('data_waznosci'))
    freshness_bg, _ = get_freshness_color(days_left)
    
    with ui.card().classes(f'{Theme.SURFACE} p-3 flex flex-col gap-2 relative overflow-hidden'):
        # Ikona i Nazwa
        with ui.row().classes('items-center gap-2'):
            ui.label(emoji).classes('text-2xl')
            with ui.column().classes('gap-0 overflow-hidden flex-1'):
                ui.label(item.get('nazwa', '—')).classes('font-semibold text-sm truncate leading-tight')
                ui.label(f"{item.get('ilosc', 0)} {item.get('jednostka', 'szt')}").classes('text-xs text-slate-400')
        
        # Pasek świeżości (wizualizacja)
        if item.get('data_waznosci'):
            with ui.element('div').classes('w-full h-1.5 bg-slate-100 rounded-full mt-auto overflow-hidden'):
                ui.element('div').classes(f'h-full {freshness_bg}').style(f'width: {freshness_pct}%')


# --- Setup Global Styles ---
def setup_modern_styles():
    """Konfiguruje nowoczesne style CSS."""
    ui.add_head_html("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        body {
            background: #f8fafc;
            margin: 0;
            padding: 0;
        }
        
        /* Smooth scrolling */
        html {
            scroll-behavior: smooth;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
        
        /* Animacje */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .fade-in {
            animation: fadeIn 0.3s ease-out;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .pulse {
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        
        /* Floating Action Button */
        .fab {
            position: fixed;
            bottom: 80px;
            right: 20px;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .fab:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
        }
        
        .fab:active {
            transform: scale(0.95);
        }
        
        /* Bottom Navigation (Mobile) */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: white;
            border-top: 1px solid #e2e8f0;
            padding: 8px 0;
            display: flex;
            justify-content: space-around;
            align-items: center;
            z-index: 999;
            box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
        }
        
        @media (min-width: 768px) {
            .bottom-nav {
                display: none;
            }
        }
        
        /* Product Card Hover */
        .product-card {
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .product-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        }
        
        /* Freshness Bar */
        .freshness-bar {
            height: 4px;
            border-radius: 2px;
            transition: width 0.3s ease;
        }
    </style>
    """)


# --- Strony ---
@ui.page('/')
async def modern_dashboard():
    """Dashboard - Centrum Dowodzenia."""
    setup_modern_styles()
    
    # Globalny layout
    ui.query('body').classes('bg-slate-50')
    
    # Header (Mobile friendly)
    with ui.header().classes('bg-white text-slate-800 shadow-sm h-16 flex items-center px-4 justify-between fixed top-0 left-0 right-0 z-50'):
        with ui.row().classes('items-center gap-2'):
            ui.label('🍽️').classes('text-2xl')
            ui.label('Spiżarnia AI').classes('text-xl font-bold tracking-tight text-emerald-700')
        
        # Avatar / Settings (desktop)
        with ui.row().classes('items-center gap-2 hidden md:flex'):
            ui.button(icon='settings', on_click=lambda: ui.open('/ustawienia')).props('flat round color=grey')
    
    # Main Content (z paddingiem dla fixed header i bottom nav)
    with ui.column().classes('w-full max-w-md mx-auto pt-20 pb-24 px-4 gap-6'):
        
        # 1. Sekcja powitalna
        ui.label('Cześć! 👋').classes('text-2xl font-bold text-slate-800 mt-4')
        
        # 2. SEKCJA: "ZJEDZ MNIE TERAZ" (Priority Dashboard - Karuzela)
        ui.label('⚠️ Do zużycia wkrótce').classes('text-xs font-bold uppercase text-slate-400 tracking-wider ml-1')
        
        try:
            inventory_data = await api_call("GET", "/api/inventory")
            items = inventory_data.get("inventory", [])
            
            # Filtruj produkty pilne (do 3 dni)
            today = date.today()
            urgent_items = []
            for item in items:
                if item.get('data_waznosci'):
                    try:
                        expiry = datetime.fromisoformat(item['data_waznosci']).date() if isinstance(item['data_waznosci'], str) else item['data_waznosci']
                        days_left = (expiry - today).days
                        if days_left <= 3:
                            item_copy = item.copy()
                            item_copy['days_left'] = days_left
                            item_copy['emoji'] = get_category_emoji(item.get('kategoria'))
                            urgent_items.append(item_copy)
                    except:
                        pass
            
            if urgent_items:
                # Scroll area dla karuzeli
                with ui.scroll_area().classes('w-full h-48'):
                    with ui.row().classes('flex-nowrap gap-4 pb-2'):
                        for item in urgent_items:
                            days_left = item.get('days_left', 0)
                            days_text = "Dziś!" if days_left == 0 else ("Po terminie!" if days_left < 0 else f"{days_left} dni")
                            
                            # Karta pilnego produktu
                            with ui.card().classes(f'{Theme.SURFACE} w-40 h-44 flex flex-col justify-between shrink-0 bg-red-50 border-red-200 p-4'):
                                with ui.column().classes('gap-2'):
                                    ui.label(item.get('emoji', '📦')).classes('text-4xl')
                                    ui.label(item.get('nazwa', '—')).classes('font-bold text-slate-800 text-sm truncate')
                                    ui.label(days_text).classes('text-red-600 font-bold text-xs')
                                    ui.label(f"{item.get('ilosc', 0)} {item.get('jednostka', 'szt')}").classes('text-xs text-slate-500')
                                
                                with ui.row().classes('w-full gap-2'):
                                    ui.button('🍽️ Zużyj', on_click=lambda n=item.get('nazwa'): ui.notify(f'Zużyto: {n}')).classes('flex-1 bg-white text-red-600 border border-red-200 hover:bg-red-100 text-xs rounded-lg')
                                    ui.button('❄️', on_click=lambda n=item.get('nazwa'): ui.notify(f'Zamrożono: {n}')).classes('bg-white text-blue-600 border border-blue-200 hover:bg-blue-100 text-xs rounded-lg px-2')
            else:
                with ui.card().classes(f'{Theme.SURFACE} w-full bg-emerald-50 border-emerald-200 flex items-center justify-center p-6'):
                    ui.label('🎉 Wszystko świeże!').classes('text-emerald-700 font-bold')
        
        except Exception as e:
            with ui.card().classes(f'{Theme.SURFACE} p-4'):
                ui.label(f'Błąd: {str(e)}').classes('text-red-600')
        
        # 3. SEKCJA: "WIRTUALNA LODÓWKA" (Podgląd - ostatnie produkty)
        ui.label('📦 Ostatnie produkty').classes('text-xs font-bold uppercase text-slate-400 tracking-wider ml-1 mt-2')
        
        try:
            # Pokaż ostatnie 4 produkty
            recent_items = items[:4] if items else []
            
            if recent_items:
                with ui.grid(columns=2).classes('w-full gap-3'):
                    for item in recent_items:
                        create_compact_product_card(item)
            else:
                with ui.card().classes(f'{Theme.SURFACE} p-6'):
                    ui.label('Brak produktów w magazynie').classes('text-center text-slate-400 text-sm')
        except:
            pass
        
        # 4. Sekcja "Ostatnie Paragony"
        ui.label('Ostatnia aktywność').classes('text-xs font-bold uppercase text-slate-400 tracking-wider ml-1 mt-2')
        
        try:
            receipts = await api_call("GET", "/api/receipts?limit=3")
            receipt_list = receipts.get("receipts", [])
            
            if receipt_list:
                with ui.column().classes(f'w-full {Theme.SURFACE} divide-y divide-slate-100 rounded-xl'):
                    for r in receipt_list:
                        with ui.row().classes('w-full p-3 items-center justify-between hover:bg-slate-50 cursor-pointer').on('click', lambda r=r: ui.open(f'/paragon/{r["paragon_id"]}')):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('receipt', size='1.2em').classes('text-slate-400')
                                with ui.column().classes('gap-0'):
                                    ui.label(r.get('sklep', 'Nieznany sklep')).classes('font-medium text-slate-800 text-sm')
                                    ui.label(r.get('data_zakupu', '—')).classes('text-xs text-slate-400')
                            ui.label(f'{r.get("suma_paragonu", 0):.2f} PLN').classes('font-bold text-emerald-600 text-sm')
            else:
                with ui.card().classes(f'{Theme.SURFACE} p-6'):
                    ui.label('Brak paragonów').classes('text-center text-slate-400 text-sm')
        except Exception as e:
            pass
    
    # Dialog Uploadu (Wizard)
    upload_dialog = ui.dialog()
    with upload_dialog, ui.card().classes('w-full max-w-sm p-6 rounded-3xl'):
        ui.label('Dodaj Paragon').classes('text-xl font-bold text-center mb-6 text-slate-800')
        
        # Dropzone - ładny wizualny obszar
        dropzone_container = ui.column().classes('w-full relative')
        with dropzone_container:
            # Wizualny dropzone
            dropzone_visual = ui.element('div').classes('w-full h-40 border-2 border-dashed border-emerald-200 bg-emerald-50 rounded-2xl flex flex-col items-center justify-center gap-2 cursor-pointer hover:bg-emerald-100 transition-colors group')
            with dropzone_visual:
                ui.icon('cloud_upload', size='48px').classes('text-emerald-400 group-hover:text-emerald-500')
                ui.label('Dotknij, aby zeskanować').classes('text-emerald-700 font-medium text-sm')
            
            # Ukryty upload (na wierzchu dropzone)
            file_upload = ui.upload(
                label='',
                auto_upload=True,
            ).props('accept=".png,.jpg,.jpeg,.pdf"').classes('absolute inset-0 opacity-0 cursor-pointer')
            
            # Handler dla uploadu
            async def handle_upload_wrapper(e):
                upload_dialog.close()
                await handle_receipt_upload(e, dropzone_container)
            
            file_upload.on_upload(handle_upload_wrapper)
        
        ui.label('lub').classes('text-center text-slate-400 my-2 text-xs')
        
        ui.button('✍️ Wpisz ręcznie', icon='edit', on_click=lambda: ui.notify('Funkcja w przygotowaniu')).classes('w-full bg-slate-100 text-slate-700 hover:bg-slate-200 shadow-none')
        
        ui.button('Anuluj', on_click=upload_dialog.close).props('flat color=grey').classes('w-full mt-2')
    
    # Bottom Navigation (Mobile) - z FAB na środku
    with ui.footer().classes('bg-white border-t border-slate-200 h-20 fixed bottom-0 w-full z-50'):
        with ui.row().classes('w-full justify-around items-center h-full pb-2'):
            # Home
            with ui.column().classes('items-center gap-0 cursor-pointer').on('click', lambda: ui.open('/')):
                ui.icon('home', size='28px').classes('text-emerald-600')
                ui.label('Dom').classes('text-[10px] text-emerald-600 font-medium')
            
            # Lista Zakupów
            with ui.column().classes('items-center gap-0 cursor-pointer').on('click', lambda: ui.open('/lista')):
                ui.icon('checklist', size='28px').classes('text-slate-400 hover:text-emerald-600 transition-colors')
                ui.label('Lista').classes('text-[10px] text-slate-400 font-medium')
            
            # FAB (Floating Action Button) - SCAN
            with ui.column().classes('items-center relative -top-6'):
                with ui.button(on_click=upload_dialog.open).classes('rounded-full w-16 h-16 shadow-lg shadow-emerald-200 bg-emerald-600 hover:bg-emerald-700 flex items-center justify-center border-4 border-slate-50'):
                    ui.icon('document_scanner', size='32px').classes('text-white')
            
            # Asystent (Chat)
            with ui.column().classes('items-center gap-0 cursor-pointer').on('click', lambda: ui.open('/chat')):
                ui.icon('restaurant_menu', size='28px').classes('text-slate-400 hover:text-emerald-600 transition-colors')
                ui.label('Asystent').classes('text-[10px] text-slate-400 font-medium')
            
            # Magazyn
            with ui.column().classes('items-center gap-0 cursor-pointer').on('click', lambda: ui.open('/magazyn')):
                ui.icon('inventory_2', size='28px').classes('text-slate-400 hover:text-emerald-600 transition-colors')
                ui.label('Magazyn').classes('text-[10px] text-slate-400 font-medium')


async def handle_receipt_upload(e, container):
    """Obsługuje upload paragonu z wizardem i animacjami."""
    try:
        file_name = getattr(e, 'name', 'paragon')
        
        # Pobierz zawartość pliku
        if hasattr(e, 'content'):
            file_obj = e.content
        elif hasattr(e, 'file'):
            file_obj = e.file
        else:
            raise Exception("Nie znaleziono zawartości pliku")
        
        file_content = await file_obj.read()
        
        # Wyślij do API
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            files = {"file": (file_name, file_content, getattr(e, 'type', 'application/pdf'))}
            response = await client.post(f"{API_URL}/api/upload", files=files)
            response.raise_for_status()
            result = response.json()
        
        task_id = result.get("task_id")
        if task_id:
            # Pokaż wizard z animacjami
            await show_upload_wizard(task_id, file_name)
    except Exception as ex:
        ui.notify(f"Błąd: {str(ex)}", type='negative')


async def show_upload_wizard(task_id: str, file_name: str):
    """Pokazuje wizard uploadu z animacjami postępu."""
    dialog = ui.dialog()
    dialog.classes('w-full max-w-2xl')
    
    with dialog:
        with ui.card().classes('w-full p-6'):
            ui.label('🔍 Przetwarzanie paragonu').classes('text-2xl font-bold text-slate-800 mb-4')
            
            # Status message
            status_label = ui.label('📤 Przesyłanie pliku...').classes('text-lg text-slate-600 mb-4')
            
            # Progress bar
            progress_bar = ui.linear_progress(value=0.05).classes('w-full mb-4')
            
            # Steps container
            steps_container = ui.column().classes('w-full gap-3 mb-4')
            
            # Human-readable steps
            steps = [
                {'icon': '📤', 'text': 'Przesyłanie pliku...', 'done': False},
                {'icon': '🔍', 'text': 'Analizuję obraz...', 'done': False},
                {'icon': '🤖', 'text': 'Asystent czyta produkty...', 'done': False},
                {'icon': '📦', 'text': 'Układam na półkach...', 'done': False},
            ]
            
            step_elements = []
            for step in steps:
                with steps_container:
                    step_row = ui.row().classes('w-full items-center gap-3 p-3 bg-slate-50 rounded-lg')
                    with step_row:
                        step_icon = ui.label(step['icon']).classes('text-2xl')
                        step_text = ui.label(step['text']).classes('text-slate-600')
                        step_check = ui.icon('check_circle', size='1.5em').classes('text-emerald-600 ml-auto')
                        step_check.visible = False
                    step_elements.append({
                        'row': step_row,
                        'icon': step_icon,
                        'text': step_text,
                        'check': step_check,
                    })
            
            # Logs area (optional, collapsible)
            logs_expanded = {'value': False}
            logs_container = ui.column().classes('w-full mt-4')
            logs_area = ui.column().classes('w-full max-h-48 overflow-y-auto bg-slate-50 p-3 rounded-lg text-xs font-mono')
            logs_area.visible = False
            
            def toggle_logs():
                logs_expanded['value'] = not logs_expanded['value']
                logs_area.visible = logs_expanded['value']
            
            with logs_container:
                ui.button('📋 Pokaż szczegóły', on_click=toggle_logs).props('flat').classes('text-sm text-slate-500')
                with logs_area:
                    pass
            
            # Track progress
            await track_upload_progress(task_id, status_label, progress_bar, step_elements, logs_area, dialog)
    
    dialog.open()


async def track_upload_progress(task_id: str, status_label, progress_bar, step_elements, logs_area, dialog):
    """Śledzi postęp przetwarzania z animacjami."""
    max_attempts = 600  # 10 minut
    attempt = 0
    last_log_count = 0
    current_step = 0
    
    # Mapowanie statusów na kroki
    status_to_step = {
        'uploading': 0,
        'ocr': 1,
        'llm': 2,
        'database': 3,
    }
    
    while attempt < max_attempts:
        try:
            task_data = await api_call("GET", f"/api/task/{task_id}")
            status = task_data.get("status", "unknown")
            progress = task_data.get("progress", 0)
            message = task_data.get("message", "")
            recent_logs = task_data.get("recent_logs", [])
            
            # Aktualizuj postęp
            progress_bar.value = progress / 100.0 if progress >= 0 else 0.05
            
            # Aktualizuj status
            status_emoji = {
                "processing": "⏳",
                "completed": "✓",
                "error": "❌",
                "timeout": "⏱️",
                "awaiting_inventory_review": "📝",
            }.get(status, "⏳")
            
            status_label.text = f"{status_emoji} {message}"
            
            # Aktualizuj kroki na podstawie logów
            for log_entry in recent_logs:
                log_msg = log_entry.get("message", "").upper()
                
                # Określ krok na podstawie wiadomości
                if "OCR" in log_msg or "ANALIZUJĘ" in log_msg:
                    if current_step < 1:
                        current_step = 1
                        mark_step_done(step_elements, 0)
                        mark_step_active(step_elements, 1)
                elif "LLM" in log_msg or "ASYSTENT" in log_msg or "PRZETWARZANIE" in log_msg:
                    if current_step < 2:
                        current_step = 2
                        mark_step_done(step_elements, 1)
                        mark_step_active(step_elements, 2)
                elif "BAZA" in log_msg or "ZAPISUJĘ" in log_msg or "PÓŁKACH" in log_msg:
                    if current_step < 3:
                        current_step = 3
                        mark_step_done(step_elements, 2)
                        mark_step_active(step_elements, 3)
            
            # Dodaj nowe logi
            if len(recent_logs) > last_log_count:
                new_logs = recent_logs[last_log_count:]
                for log_entry in new_logs:
                    log_msg = log_entry.get("message", "")
                    color = "text-slate-600"
                    if "BŁĄD" in log_msg.upper() or "ERROR" in log_msg.upper():
                        color = "text-red-600"
                    elif "SUKCES" in log_msg.upper() or "✓" in log_msg:
                        color = "text-emerald-600"
                    elif "WARNING" in log_msg.upper():
                        color = "text-orange-600"
                    
                    with logs_area:
                        ui.label(log_msg).classes(f'{color} mb-1')
                
                last_log_count = len(recent_logs)
                
                # Przewiń do dołu
                ui.run_javascript('''
                    const area = arguments[0];
                    if (area) {
                        area.scrollTop = area.scrollHeight;
                    }
                ''', logs_area)
            
            # Sprawdź czy wymagana edycja magazynu
            if status == "awaiting_inventory_review":
                inventory_items = task_data.get("inventory_items", [])
                if inventory_items:
                    mark_step_done(step_elements, 3)
                    status_label.text = "📝 Oczekiwanie na edycję produktów..."
                    progress_bar.value = 0.95
                    
                    # Pokaż dialog edycji
                    dialog.close()
                    await show_inventory_edit_dialog_modern(task_id, inventory_items)
                    break
            
            # Sprawdź czy zakończone
            if status in ["completed", "error", "timeout"]:
                if status == "completed":
                    mark_step_done(step_elements, 3)
                    status_label.text = "✓ Przetwarzanie zakończone pomyślnie!"
                    progress_bar.value = 1.0
                    
                    # Sukces - zamknij dialog i odśwież
                    await asyncio.sleep(2)
                    dialog.close()
                    ui.notify("Paragon został pomyślnie przetworzony!", type='positive')
                    ui.open('/')
                else:
                    status_label.text = f"❌ {message}"
                    progress_bar.value = 0
                    ui.notify(f"Błąd: {message}", type='negative')
                
                break
            
            await asyncio.sleep(1)
            attempt += 1
        except Exception as e:
            status_label.text = f"❌ Błąd śledzenia: {str(e)}"
            break
    
    if attempt >= max_attempts:
        status_label.text = "⏱️ Przekroczono limit czasu"
        ui.notify("Przetwarzanie trwa zbyt długo", type='warning')


def mark_step_done(step_elements, index):
    """Oznacza krok jako zakończony."""
    if index < len(step_elements):
        step = step_elements[index]
        step['row'].classes('bg-emerald-50 border border-emerald-200')
        step['text'].classes('text-emerald-700 font-semibold')
        step['check'].visible = True


def mark_step_active(step_elements, index):
    """Oznacza krok jako aktywny."""
    if index < len(step_elements):
        step = step_elements[index]
        step['row'].classes('bg-blue-50 border border-blue-200')
        step['text'].classes('text-blue-700 font-semibold')


async def show_inventory_edit_dialog_modern(task_id: str, inventory_items: list):
    """Nowoczesny dialog edycji produktów przed dodaniem do magazynu."""
    dialog = ui.dialog()
    dialog.classes('w-full max-w-4xl')
    
    with dialog:
        with ui.card().classes('w-full p-6'):
            ui.label('📦 Edycja produktów przed dodaniem do spiżarni').classes('text-2xl font-bold text-slate-800 mb-4')
            ui.label('Sprawdź i edytuj produkty przed dodaniem do spiżarni:').classes('text-lg text-slate-600 mb-6')
            
            # Grid produktów do edycji
            edit_items = []
            items_container = ui.column().classes('w-full gap-4 max-h-96 overflow-y-auto')
            
            for item in inventory_items:
                with items_container:
                    with ui.card().classes(f'{Theme.SURFACE} p-4'):
                        # Nazwa produktu
                        ui.label(item['nazwa']).classes('text-lg font-semibold text-slate-800 mb-3')
                        
                        # Pola edycji
                        with ui.row().classes('w-full gap-4 items-end'):
                            ilosc_input = ui.number(
                                label='Ilość',
                                value=item['ilosc'],
                                format='%.2f'
                            ).classes('flex-1')
                            
                            jednostka_input = ui.input(
                                label='Jednostka',
                                value=item.get('jednostka', 'szt')
                            ).classes('w-32')
                            
                            data_input = ui.input(
                                label='Data ważności (YYYY-MM-DD)',
                                value=item.get('data_waznosci') or ''
                            ).classes('w-40')
                        
                        edit_items.append({
                            'produkt_id': item['produkt_id'],
                            'ilosc_input': ilosc_input,
                            'jednostka_input': jednostka_input,
                            'data_input': data_input,
                        })
            
            # Przyciski
            with ui.row().classes('w-full justify-end gap-2 mt-6'):
                async def confirm_edit():
                    try:
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
                        
                        await api_call("POST", "/api/inventory/confirm", {
                            "task_id": task_id,
                            "items": items_to_save
                        })
                        
                        dialog.close()
                        ui.notify("Produkty zostały dodane do spiżarni!", type='positive')
                        await asyncio.sleep(1)
                        ui.open('/')
                    except Exception as e:
                        ui.notify(f"Błąd: {str(e)}", type='negative')
                
                ui.button('✓ Zatwierdź i dodaj do spiżarni', on_click=confirm_edit).classes('bg-emerald-600 text-white')
                ui.button('Anuluj', on_click=dialog.close).classes('bg-slate-200 text-slate-700')
    
    dialog.open()


@ui.page('/magazyn')
async def modern_inventory():
    """Wirtualna Lodówka - widok grid z kartami produktów."""
    setup_modern_styles()
    ui.query('body').classes('bg-slate-50')
    
    # Header
    with ui.header().classes('bg-white text-slate-800 shadow-sm h-16 flex items-center px-4 justify-between fixed top-0 left-0 right-0 z-50'):
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='arrow_back', on_click=lambda: ui.open('/')).props('flat round color=grey')
            ui.label('📦 Wirtualna Lodówka').classes('text-xl font-bold text-slate-800')
        ui.button(icon='settings', on_click=lambda: ui.open('/ustawienia')).props('flat round color=grey').classes('hidden md:flex')
    
    # Main Content
    with ui.column().classes('w-full max-w-6xl mx-auto p-4 gap-4 mt-16 mb-20'):
        
        # Filtry (Chips)
        ui.label('Kategorie').classes('text-sm font-semibold text-slate-600')
        filter_chips = ui.row().classes('w-full gap-2 flex-wrap')
        
        # Pobierz unikalne kategorie
        try:
            inventory_data = await api_call("GET", "/api/inventory")
            items = inventory_data.get("inventory", [])
            
            categories = set()
            for item in items:
                cat = item.get('kategoria')
                if cat:
                    categories.add(cat)
            
            selected_category = {'value': None}
            
            def create_chip(cat_name: Optional[str]):
                label = cat_name or "Wszystkie"
                chip = ui.button(label, on_click=lambda c=cat_name: filter_items(c)).classes('rounded-full px-4 py-2 text-sm')
                if cat_name is None:
                    chip.classes('bg-emerald-600 text-white')
                else:
                    chip.classes('bg-slate-100 text-slate-700 hover:bg-slate-200')
                return chip
            
            with filter_chips:
                create_chip(None)  # "Wszystkie"
                for cat in sorted(categories):
                    create_chip(cat)
            
            # Grid produktów
            products_grid = ui.row().classes('w-full gap-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4')
            
            def filter_items(category: Optional[str]):
                selected_category['value'] = category
                products_grid.clear()
                
                filtered = items if not category else [item for item in items if item.get('kategoria') == category]
                
                with products_grid:
                    for item in filtered:
                        create_product_card(item)
            
            def create_product_card(item):
                """Tworzy kartę produktu."""
                kategoria = item.get('kategoria', 'Inne')
                emoji = get_category_emoji(kategoria)
                bg_color = Theme.CATEGORY_COLORS.get(kategoria, Theme.CATEGORY_COLORS['Inne'])
                freshness_bg, freshness_border = get_freshness_color(item.get('data_waznosci'))
                
                with ui.card().classes(f'{Theme.SURFACE} p-4 product-card cursor-pointer'):
                    # Emoji kategorii
                    ui.label(emoji).classes('text-3xl mb-2')
                    
                    # Nazwa produktu
                    ui.label(item.get('nazwa', '—')).classes('font-semibold text-slate-800 text-lg mb-1')
                    
                    # Ilość i jednostka
                    ui.label(f"{item.get('ilosc', 0)} {item.get('jednostka', 'szt')}").classes('text-sm text-slate-500 mb-2')
                    
                    # Pasek świeżości z obliczaniem procentu
                    if item.get('data_waznosci'):
                        freshness_pct, days_left = calculate_freshness_percentage(item.get('data_waznosci'))
                        freshness_bg, _ = get_freshness_color(days_left)
                        
                        with ui.row().classes('w-full items-center gap-2 mb-2'):
                            ui.label('📅').classes('text-xs')
                            ui.label(format_date_relative(item.get('data_waznosci'))).classes('text-xs text-slate-600')
                        
                        # Wizualny pasek z procentem
                        with ui.row().classes('w-full h-2 bg-slate-200 rounded-full overflow-hidden'):
                            ui.element('div').classes(f'freshness-bar {freshness_bg}').style(f'width: {freshness_pct}%')
                    
                    # Kategoria (chip)
                    if kategoria:
                        ui.label(kategoria).classes(f'text-xs px-2 py-1 rounded-full {bg_color} inline-block mt-2')
            
            # Początkowo pokaż wszystkie
            filter_items(None)
            
        except Exception as e:
            with ui.card().classes(f'{Theme.SURFACE} p-8'):
                ui.label(f'Błąd podczas ładowania magazynu: {str(e)}').classes('text-red-600')
    
    # Bottom Navigation
    with ui.row().classes('bottom-nav'):
        ui.button(icon='home', on_click=lambda: ui.open('/')).props('flat round color=grey')
        ui.button(icon='inventory', on_click=lambda: ui.open('/magazyn')).props('flat round color=green')
        ui.button(icon='add', on_click=lambda: ui.open('/')).props('round color=green').classes('-mt-8 shadow-lg border-4 border-slate-50 scale-125')
        ui.button(icon='shopping_cart', on_click=lambda: ui.open('/lista')).props('flat round color=grey')
        ui.button(icon='chat', on_click=lambda: ui.open('/chat')).props('flat round color=grey')


@ui.page('/chat')
async def modern_chat():
    """Nowoczesny chat z asystentem AI - dymki jak w Messengerze."""
    setup_modern_styles()
    ui.query('body').classes('bg-slate-50')
    
    # Header
    with ui.header().classes('bg-white text-slate-800 shadow-sm h-16 flex items-center px-4 justify-between fixed top-0 left-0 right-0 z-50'):
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='arrow_back', on_click=lambda: ui.open('/')).props('flat round color=grey')
            with ui.row().classes('items-center gap-2'):
                ui.icon('chat', size='1.5em').classes('text-emerald-600')
                ui.label('Asystent AI').classes('text-xl font-bold text-slate-800')
        ui.button(icon='settings', on_click=lambda: ui.open('/ustawienia')).props('flat round color=grey').classes('hidden md:flex')
    
    # Main Content (Chat)
    with ui.column().classes('w-full max-w-3xl mx-auto h-screen flex flex-col mt-16 mb-20'):
        
        # Chat Container (scrollable)
        chat_container = ui.column().classes('flex-1 overflow-y-auto p-4 gap-3')
        
        # Wiadomość powitalna
        with chat_container:
            with ui.row().classes('w-full justify-start'):
                with ui.card().classes('bg-emerald-100 border-emerald-200 max-w-[80%] rounded-2xl rounded-tl-none p-3'):
                    ui.label('👋 Cześć! Jestem Twoim asystentem kulinarnym. Jak mogę Ci pomóc?').classes('text-slate-800')
        
        # Input Area (fixed at bottom)
        with ui.row().classes('w-full p-4 bg-white border-t border-slate-200 gap-2'):
            input_field = ui.input(placeholder='Zadaj pytanie asystentowi...').classes('flex-1').props('autofocus')
            
            async def send_message():
                question = input_field.value
                if not question.strip():
                    return
                
                # Dodaj wiadomość użytkownika (po prawej)
                with chat_container:
                    with ui.row().classes('w-full justify-end'):
                        with ui.card().classes('bg-emerald-600 text-white max-w-[80%] rounded-2xl rounded-tr-none p-3'):
                            ui.label(question).classes('text-white')
                
                input_field.value = ""
                
                # Pokaż wskaźnik ładowania (po lewej)
                loading_msg = None
                with chat_container:
                    with ui.row().classes('w-full justify-start'):
                        loading_card = ui.card().classes('bg-slate-100 border-slate-200 max-w-[80%] rounded-2xl rounded-tl-none p-3')
                        with loading_card:
                            loading_msg = ui.label('⏳ Asystent myśli...').classes('text-slate-600 pulse')
                
                # Wyślij do API
                try:
                    response = await api_call("POST", "/api/chat", {"question": question})
                    answer = response.get("answer", "Przepraszam, nie mogę odpowiedzieć.")
                    
                    # Usuń wskaźnik ładowania i dodaj odpowiedź
                    loading_card.delete()
                    with chat_container:
                        with ui.row().classes('w-full justify-start'):
                            with ui.card().classes('bg-emerald-100 border-emerald-200 max-w-[80%] rounded-2xl rounded-tl-none p-3'):
                                ui.label(f'🤖 {answer}').classes('text-slate-800')
                    
                    # Przewiń do dołu
                    ui.run_javascript('''
                        const container = document.querySelector('.overflow-y-auto');
                        if (container) {
                            container.scrollTop = container.scrollHeight;
                        }
                    ''')
                except Exception as e:
                    loading_card.delete()
                    with chat_container:
                        with ui.row().classes('w-full justify-start'):
                            with ui.card().classes('bg-red-100 border-red-200 max-w-[80%] rounded-2xl rounded-tl-none p-3'):
                                ui.label(f'❌ Błąd: {str(e)}').classes('text-red-800')
            
            input_field.on('keydown.enter', send_message)
            ui.button(icon='send', on_click=send_message).classes('bg-emerald-600 text-white').props('round')
    
    # Bottom Navigation
    with ui.row().classes('bottom-nav'):
        ui.button(icon='home', on_click=lambda: ui.open('/')).props('flat round color=grey')
        ui.button(icon='inventory', on_click=lambda: ui.open('/magazyn')).props('flat round color=grey')
        ui.button(icon='add', on_click=lambda: ui.open('/')).props('round color=green').classes('-mt-8 shadow-lg border-4 border-slate-50 scale-125')
        ui.button(icon='shopping_cart', on_click=lambda: ui.open('/lista')).props('flat round color=grey')
        ui.button(icon='chat', on_click=lambda: ui.open('/bielik')).props('flat round color=green')


@ui.page('/paragon/{receipt_id}')
async def modern_receipt_detail(receipt_id: int):
    """Strona szczegółów paragonu."""
    setup_modern_styles()
    ui.query('body').classes('bg-slate-50')
    
    # Header
    with ui.header().classes('bg-white text-slate-800 shadow-sm h-16 flex items-center px-4 justify-between fixed top-0 left-0 right-0 z-50'):
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='arrow_back', on_click=lambda: ui.open('/')).props('flat round color=grey')
            ui.label('📄 Szczegóły paragonu').classes('text-xl font-bold text-slate-800')
    
    # Main Content
    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-6 mt-16 mb-20'):
        try:
            receipt = await api_call("GET", f"/api/receipts/{receipt_id}")
            
            # Informacje o paragonie
            with ui.card().classes(f'{Theme.SURFACE} p-6'):
                ui.label('Informacje o paragonie').classes('text-lg font-semibold text-slate-800 mb-4')
                
                # Pobierz listę sklepów
                stores_data = await api_call("GET", "/api/stores")
                stores = stores_data.get("stores", [])
                store_options = {s["nazwa_sklepu"]: s["sklep_id"] for s in stores}
                
                with ui.column().classes('w-full gap-4'):
                    sklep_select = ui.select(
                        options=store_options,
                        label='Sklep',
                        value=receipt.get("sklep_id")
                    ).classes('w-full')
                    
                    receipt_date = receipt.get("data_zakupu")
                    if receipt_date:
                        if isinstance(receipt_date, str):
                            data_input = ui.input(
                                label='Data zakupu (YYYY-MM-DD)',
                                value=receipt_date
                            ).classes('w-full')
                        else:
                            data_input = ui.input(
                                label='Data zakupu (YYYY-MM-DD)',
                                value=str(receipt_date)
                            ).classes('w-full')
                    else:
                        data_input = ui.input(
                            label='Data zakupu (YYYY-MM-DD)',
                            value=''
                        ).classes('w-full')
                    
                    suma_input = ui.number(
                        label='Suma paragonu',
                        value=float(receipt.get("suma_paragonu", 0)),
                        format='%.2f'
                    ).classes('w-full')
                
                async def save_receipt():
                    try:
                        from datetime import datetime
                        date_value = None
                        if data_input.value:
                            try:
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
                        await asyncio.sleep(1)
                        ui.open('/')
                    except Exception as e:
                        ui.notify(f"❌ Błąd: {str(e)}", type='negative')
                
                with ui.row().classes('w-full gap-2 mt-4'):
                    ui.button('💾 Zapisz zmiany', on_click=save_receipt).classes('bg-emerald-600 text-white')
                    ui.button('🗑️ Usuń paragon', on_click=delete_receipt).classes('bg-red-600 text-white')
            
            # Pozycje paragonu
            with ui.card().classes(f'{Theme.SURFACE} p-6'):
                ui.label('Pozycje paragonu').classes('text-lg font-semibold text-slate-800 mb-4')
                
                pozycje = receipt.get("pozycje", [])
                if pozycje:
                    with ui.column().classes('w-full gap-2'):
                        for pozycja in pozycje:
                            with ui.card().classes('bg-slate-50 p-4'):
                                with ui.row().classes('w-full items-center justify-between'):
                                    with ui.column().classes('flex-1'):
                                        ui.label(pozycja.get('nazwa_znormalizowana', pozycja.get('nazwa_z_paragonu_raw', '—'))).classes('font-semibold text-slate-800')
                                        ui.label(f"{pozycja.get('ilosc', 0)} {pozycja.get('jednostka_miary', '')}").classes('text-sm text-slate-500')
                                    ui.label(f"{pozycja.get('cena_calkowita', 0):.2f} PLN").classes('font-bold text-emerald-600')
                else:
                    ui.label('Brak pozycji w paragonie.').classes('text-slate-400 text-center py-8')
        except Exception as e:
            with ui.card().classes(f'{Theme.SURFACE} p-4'):
                ui.label(f'Błąd: {str(e)}').classes('text-red-600')
                if "404" in str(e):
                    ui.button('← Powrót do listy', on_click=lambda: ui.open('/')).classes('mt-4 bg-emerald-600 text-white')
    
    # Bottom Navigation
    with ui.row().classes('bottom-nav'):
        ui.button(icon='home', on_click=lambda: ui.open('/')).props('flat round color=grey')
        ui.button(icon='inventory', on_click=lambda: ui.open('/magazyn')).props('flat round color=grey')
        ui.button(icon='add', on_click=lambda: ui.open('/')).props('round color=green').classes('-mt-8 shadow-lg border-4 border-slate-50 scale-125')
        ui.button(icon='shopping_cart', on_click=lambda: ui.open('/lista')).props('flat round color=grey')
        ui.button(icon='chat', on_click=lambda: ui.open('/chat')).props('flat round color=grey')


@ui.page('/lista')
async def modern_shopping_list():
    """Lista zakupów (placeholder)."""
    setup_modern_styles()
    ui.query('body').classes('bg-slate-50')
    
    # Header
    with ui.header().classes('bg-white text-slate-800 shadow-sm h-16 flex items-center px-4 justify-between fixed top-0 left-0 right-0 z-50'):
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='arrow_back', on_click=lambda: ui.open('/')).props('flat round color=grey')
            ui.label('🛒 Lista zakupów').classes('text-xl font-bold text-slate-800')
    
    # Main Content
    with ui.column().classes('w-full max-w-2xl mx-auto p-4 gap-6 mt-16 mb-20'):
        with ui.card().classes(f'{Theme.SURFACE} p-8'):
            ui.label('Lista zakupów').classes('text-lg font-semibold text-slate-800 mb-4')
            ui.label('Ta funkcja będzie dostępna wkrótce!').classes('text-slate-400 text-center py-8')
            ui.label('Asystent będzie mógł generować listy zakupów na podstawie braków w magazynie.').classes('text-sm text-slate-500 text-center')
    
    # Bottom Navigation
    with ui.row().classes('bottom-nav'):
        ui.button(icon='home', on_click=lambda: ui.open('/')).props('flat round color=grey')
        ui.button(icon='inventory', on_click=lambda: ui.open('/magazyn')).props('flat round color=grey')
        ui.button(icon='add', on_click=lambda: ui.open('/')).props('round color=green').classes('-mt-8 shadow-lg border-4 border-slate-50 scale-125')
        ui.button(icon='shopping_cart', on_click=lambda: ui.open('/lista')).props('flat round color=green')
        ui.button(icon='chat', on_click=lambda: ui.open('/chat')).props('flat round color=grey')


@ui.page('/ustawienia')
async def modern_settings():
    """Strona ustawień."""
    setup_modern_styles()
    ui.query('body').classes('bg-slate-50')
    
    # Header
    with ui.header().classes('bg-white text-slate-800 shadow-sm h-16 flex items-center px-4 justify-between fixed top-0 left-0 right-0 z-50'):
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='arrow_back', on_click=lambda: ui.open('/')).props('flat round color=grey')
            ui.label('⚙️ Ustawienia').classes('text-xl font-bold text-slate-800')
    
    # Main Content
    with ui.column().classes('w-full max-w-2xl mx-auto p-4 gap-6 mt-16 mb-20'):
        try:
            settings = await api_call("GET", "/api/settings")
            
            with ui.card().classes(f'{Theme.SURFACE} p-6'):
                ui.label('Tryb działania').classes('text-lg font-semibold text-slate-800 mb-4')
                ui.label('✓ Cloud AI (OpenAI) - zawsze włączone').classes('text-sm text-slate-600 mb-2')
                ui.label('✓ Cloud OCR (Mistral) - zawsze włączone').classes('text-sm text-slate-600')
            
            with ui.card().classes(f'{Theme.SURFACE} p-6'):
                ui.label('Klucze API').classes('text-lg font-semibold text-slate-800 mb-4')
                
                openai_key = ui.input('OpenAI API Key', placeholder='sk-...', password=True).classes('w-full mb-2')
                if settings.get("openai_api_key_set"):
                    ui.label('✓ Klucz OpenAI jest ustawiony').classes('text-sm text-emerald-600 mb-4')
                
                mistral_key = ui.input('Mistral API Key', placeholder='...', password=True).classes('w-full mb-4')
                if settings.get("mistral_api_key_set"):
                    ui.label('✓ Klucz Mistral jest ustawiony').classes('text-sm text-emerald-600')
                
                async def save_settings():
                    update_data = {
                        "use_cloud_ai": True,
                        "use_cloud_ocr": True,
                    }
                    
                    if openai_key.value:
                        update_data["openai_api_key"] = openai_key.value
                    
                    if mistral_key.value:
                        update_data["mistral_api_key"] = mistral_key.value
                    
                    try:
                        await api_call("POST", "/api/settings", update_data)
                        ui.notify("✓ Ustawienia zapisane!", type='positive')
                    except Exception as e:
                        ui.notify(f"❌ Błąd: {str(e)}", type='negative')
                
                ui.button('💾 Zapisz ustawienia', on_click=save_settings).classes('bg-emerald-600 text-white w-full mt-4')
        except Exception as e:
            with ui.card().classes(f'{Theme.SURFACE} p-4'):
                ui.label(f'Błąd: {str(e)}').classes('text-red-600')
    
    # Bottom Navigation
    with ui.row().classes('bottom-nav'):
        ui.button(icon='home', on_click=lambda: ui.open('/')).props('flat round color=grey')
        ui.button(icon='inventory', on_click=lambda: ui.open('/magazyn')).props('flat round color=grey')
        ui.button(icon='add', on_click=lambda: ui.open('/')).props('round color=green').classes('-mt-8 shadow-lg border-4 border-slate-50 scale-125')
        ui.button(icon='shopping_cart', on_click=lambda: ui.open('/lista')).props('flat round color=grey')
        ui.button(icon='chat', on_click=lambda: ui.open('/chat')).props('flat round color=grey')


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8082, title="Spiżarnia AI", favicon="🍽️")

