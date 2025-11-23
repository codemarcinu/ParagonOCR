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


# --- Stylowanie ---

def setup_styles():
    """Konfiguruje style CSS dla aplikacji."""
    ui.add_head_html("""
    <style>
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .btn-primary {
            background: #1f538d;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .btn-primary:hover {
            background: #1a4470;
        }
        .stat-card {
            text-align: center;
            padding: 20px;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #1f538d;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
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


# --- Strony ---

@ui.page('/')
async def dashboard():
    """Strona główna - Dashboard."""
    setup_styles()
    
    with ui.column().classes('container'):
        ui.label('📄 ParagonWeb').style('font-size: 2em; font-weight: bold; margin-bottom: 20px;')
        
        # Przycisk dodawania paragonu
        with ui.card():
            ui.label('Dodaj nowy paragon').style('font-size: 1.2em; margin-bottom: 10px;')
            
            status_label = ui.label('Gotowy').style('margin-top: 10px;')
            progress_bar = ui.linear_progress(value=0).style('margin-top: 10px;')
            
            async def handle_upload_wrapper(e):
                """Wrapper dla handle_upload."""
                status_label.text = f"Przesyłanie {e.name}..."
                progress_bar.value = 0.3
                await handle_upload(e)
                progress_bar.value = 1.0
                status_label.text = "Gotowy"
            
            file_upload = ui.upload(
                label='Wybierz plik paragonu',
                auto_upload=True,
                on_upload=handle_upload_wrapper,
            ).props('accept=".png,.jpg,.jpeg,.pdf"')
        
        # Statystyki
        with ui.row().classes('w-full'):
            try:
                stats = await api_call("GET", "/api/stats")
                total_stats = stats.get("total_statistics", {})
                
                with ui.card().classes('stat-card'):
                    ui.label(f'{total_stats.get("total_receipts", 0)}').classes('stat-value')
                    ui.label('Paragonów').classes('stat-label')
                
                with ui.card().classes('stat-card'):
                    ui.label(f'{total_stats.get("total_spent", 0):.2f} PLN').classes('stat-value')
                    ui.label('Wydatki').classes('stat-label')
                
                with ui.card().classes('stat-card'):
                    ui.label(f'{total_stats.get("total_items", 0)}').classes('stat-value')
                    ui.label('Pozycji').classes('stat-label')
            except Exception as e:
                ui.label(f'Błąd podczas ładowania statystyk: {str(e)}').style('color: red;')
        
        # Ostatnie paragony
        with ui.card():
            ui.label('Ostatnie paragony').style('font-size: 1.2em; margin-bottom: 10px;')
            
            try:
                receipts = await api_call("GET", "/api/receipts?limit=10")
                receipt_list = receipts.get("receipts", [])
                
                if receipt_list:
                    with ui.table(
                        columns=[
                            {'name': 'data', 'label': 'Data', 'field': 'data'},
                            {'name': 'sklep', 'label': 'Sklep', 'field': 'sklep'},
                            {'name': 'suma', 'label': 'Suma', 'field': 'suma'},
                            {'name': 'pozycje', 'label': 'Pozycje', 'field': 'pozycje'},
                        ],
                        rows=[
                            {
                                'data': r['data_zakupu'],
                                'sklep': r['sklep'],
                                'suma': f"{r['suma_paragonu']:.2f} PLN",
                                'pozycje': r['liczba_pozycji'],
                            }
                            for r in receipt_list
                        ],
                    ).classes('w-full'):
                        pass
                else:
                    ui.label('Brak paragonów. Dodaj pierwszy paragon!').style('color: #666;')
            except Exception as e:
                ui.label(f'Błąd podczas ładowania paragonów: {str(e)}').style('color: red;')


@ui.page('/magazyn')
async def inventory_page():
    """Strona magazynu."""
    setup_styles()
    
    with ui.column().classes('container'):
        ui.label('📦 Magazyn').style('font-size: 2em; font-weight: bold; margin-bottom: 20px;')
        
        try:
            inventory_data = await api_call("GET", "/api/inventory")
            items = inventory_data.get("inventory", [])
            
            if items:
                with ui.table(
                    columns=[
                        {'name': 'nazwa', 'label': 'Produkt', 'field': 'nazwa'},
                        {'name': 'ilosc', 'label': 'Ilość', 'field': 'ilosc'},
                        {'name': 'jednostka', 'label': 'Jednostka', 'field': 'jednostka'},
                        {'name': 'data_waznosci', 'label': 'Data ważności', 'field': 'data_waznosci'},
                        {'name': 'kategoria', 'label': 'Kategoria', 'field': 'kategoria'},
                    ],
                    rows=items,
                ).classes('w-full'):
                    pass
            else:
                ui.label('Magazyn jest pusty. Dodaj paragony, aby wypełnić magazyn!').style('color: #666;')
        except Exception as e:
            ui.label(f'Błąd podczas ładowania magazynu: {str(e)}').style('color: red;')


@ui.page('/bielik')
async def bielik_page():
    """Strona czatu z Bielikiem."""
    setup_styles()
    
    with ui.column().classes('container'):
        ui.label('🦅 Bielik - Asystent Kulinarny').style('font-size: 2em; font-weight: bold; margin-bottom: 20px;')
        
        chat_messages = []
        chat_container = ui.column().classes('w-full')
        
        async def send_message():
            question = input_field.value
            if not question.strip():
                return
            
            # Dodaj wiadomość użytkownika
            with chat_container:
                ui.label(f'Ty: {question}').style('background: #e0e0e0; padding: 10px; border-radius: 4px; margin: 5px 0;')
            
            input_field.value = ""
            
            # Wyślij do API
            try:
                response = await api_call("POST", "/api/chat", {"question": question})
                answer = response.get("answer", "Przepraszam, nie mogę odpowiedzieć.")
                
                # Dodaj odpowiedź Bielika
                with chat_container:
                    ui.label(f'Bielik: {answer}').style('background: #1f538d; color: white; padding: 10px; border-radius: 4px; margin: 5px 0;')
            except Exception as e:
                with chat_container:
                    ui.label(f'Błąd: {str(e)}').style('color: red;')
        
        input_field = ui.input('Zadaj pytanie Bielikowi...').classes('w-full').style('margin-top: 20px;')
        input_field.on('keydown.enter', send_message)
        
        ui.button('Wyślij', on_click=send_message).classes('btn-primary').style('margin-top: 10px;')


@ui.page('/ustawienia')
async def settings_page():
    """Strona ustawień."""
    setup_styles()
    
    with ui.column().classes('container'):
        ui.label('⚙️ Ustawienia').style('font-size: 2em; font-weight: bold; margin-bottom: 20px;')
        
        try:
            settings = await api_call("GET", "/api/settings")
            
            with ui.card():
                ui.label('Tryb działania').style('font-size: 1.2em; margin-bottom: 10px;')
                
                use_cloud_ai = ui.switch(
                    'Użyj Cloud AI (OpenAI)',
                    value=settings.get("use_cloud_ai", True)
                )
                
                use_cloud_ocr = ui.switch(
                    'Użyj Cloud OCR (Mistral)',
                    value=settings.get("use_cloud_ocr", True)
                )
                
                ui.label('Klucze API').style('font-size: 1.2em; margin-top: 20px; margin-bottom: 10px;')
                
                openai_key = ui.input(
                    'OpenAI API Key',
                    placeholder='sk-...',
                    password=True
                ).classes('w-full')
                
                mistral_key = ui.input(
                    'Mistral API Key',
                    placeholder='...',
                    password=True
                ).classes('w-full')
                
                async def save_settings():
                    update_data = {
                        "use_cloud_ai": use_cloud_ai.value,
                        "use_cloud_ocr": use_cloud_ocr.value,
                    }
                    
                    if openai_key.value:
                        update_data["openai_api_key"] = openai_key.value
                    
                    if mistral_key.value:
                        update_data["mistral_api_key"] = mistral_key.value
                    
                    try:
                        await api_call("POST", "/api/settings", update_data)
                        ui.notify("Ustawienia zapisane!", type='positive')
                    except Exception as e:
                        ui.notify(f"Błąd: {str(e)}", type='negative')
                
                ui.button('Zapisz ustawienia', on_click=save_settings).classes('btn-primary').style('margin-top: 20px;')
        except Exception as e:
            ui.label(f'Błąd podczas ładowania ustawień: {str(e)}').style('color: red;')


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


# --- Menu nawigacyjne ---

@ui.page('/menu')
def menu():
    """Menu nawigacyjne."""
    with ui.column().classes('container'):
        ui.label('Menu').style('font-size: 2em; font-weight: bold; margin-bottom: 20px;')
        
        ui.link('Dashboard', '/').classes('btn-primary').style('display: block; margin: 10px 0; padding: 10px; text-align: center; text-decoration: none;')
        ui.link('Magazyn', '/magazyn').classes('btn-primary').style('display: block; margin: 10px 0; padding: 10px; text-align: center; text-decoration: none;')
        ui.link('Bielik', '/bielik').classes('btn-primary').style('display: block; margin: 10px 0; padding: 10px; text-align: center; text-decoration: none;')
        ui.link('Ustawienia', '/ustawienia').classes('btn-primary').style('display: block; margin: 10px 0; padding: 10px; text-align: center; text-decoration: none;')


if __name__ in {"__main__", "__mp_main__"}:
    # Port 8081, bo 8080 jest zajęty przez open-webui
    ui.run(port=8081, title="ParagonWeb")

