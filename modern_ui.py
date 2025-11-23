import os
import sys
from datetime import datetime, date, timedelta
from typing import Optional
from nicegui import ui, app
import httpx

# Dodaj ReceiptParser do ścieżki
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ReceiptParser"))

# URL API
API_URL = os.getenv("API_URL", "http://localhost:8000")


# --- DESIGN SYSTEM (Tailwind Config Wrapper) ---
class Theme:
    # Kolory
    BG_APP = "bg-slate-50"
    SURFACE = "bg-white"
    PRIMARY = "bg-emerald-600"
    PRIMARY_BTN = "bg-emerald-600 hover:bg-emerald-700 text-white"
    TEXT_MAIN = "text-slate-800"
    TEXT_SEC = "text-slate-500"

    # Style Kart
    CARD = "rounded-2xl shadow-sm border border-slate-100 p-4 transition-all hover:shadow-md"

    # Pasek świeżości (kolory)
    FRESH_GOOD = "bg-emerald-400"
    FRESH_WARN = "bg-yellow-400"
    FRESH_BAD = "bg-red-500"


# --- Funkcje pomocnicze API ---
async def api_call(
    method: str,
    endpoint: str,
    data: Optional[dict] = None,
    files: Optional[dict] = None,
):
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
    except Exception as e:
        print(f"API Error: {e}")
        return {}


def calculate_freshness_percentage(
    data_waznosci: Optional[str], typical_shelf_life_days: int = 14
) -> tuple[int, int]:
    """
    Oblicza procent świeżości produktu.
    Returns: (percentage 0-100, days_left)
    """
    if not data_waznosci:
        return (100, 999)  # Brak daty = zawsze świeże

    try:
        expiry_date = (
            datetime.fromisoformat(data_waznosci).date()
            if isinstance(data_waznosci, str)
            else data_waznosci
        )
        today = date.today()
        days_left = (expiry_date - today).days

        if days_left < 0:
            return (0, days_left)  # Przeterminowane

        if days_left >= typical_shelf_life_days:
            return (100, days_left)

        percentage = max(0, min(100, int((days_left / typical_shelf_life_days) * 100)))
        return (percentage, days_left)
    except:
        return (100, 999)


def get_category_emoji(kategoria: Optional[str]) -> str:
    """Zwraca emoji dla kategorii produktu."""
    if not kategoria:
        return "📦"

    emoji_map = {
        "Nabiał": "🥛",
        "Warzywa": "🥦",
        "Owoce": "🍎",
        "Mięso": "🥩",
        "Pieczywo": "🍞",
        "Słodycze": "🍫",
        "Napoje": "🥤",
        "Chemia": "🧴",
    }
    return emoji_map.get(kategoria, "📦")


# Mock danych (później podepniesz tu API)
inventory_mock = [
    {
        "name": "Mleko 3.2%",
        "qty": 1.5,
        "unit": "l",
        "days_left": 2,
        "cat": "Nabiał",
        "icon": "🥛",
    },
    {
        "name": "Jajka L",
        "qty": 8,
        "unit": "szt",
        "days_left": 10,
        "cat": "Nabiał",
        "icon": "🥚",
    },
    {
        "name": "Pomidory",
        "qty": 0.5,
        "unit": "kg",
        "days_left": -1,
        "cat": "Warzywa",
        "icon": "🍅",
    },
    {
        "name": "Kurczak",
        "qty": 1,
        "unit": "kg",
        "days_left": 1,
        "cat": "Mięso",
        "icon": "🥩",
    },
]


def get_freshness_color(days):
    if days < 0:
        return Theme.FRESH_BAD
    if days <= 3:
        return Theme.FRESH_WARN
    return Theme.FRESH_GOOD


@ui.page("/")
async def main_page():
    # Ustawienia globalne
    ui.query("body").classes("bg-slate-50 font-sans")

    # --- HEADER ---
    with ui.header().classes(
        "bg-white text-slate-800 h-16 shadow-sm flex items-center justify-between px-4 fixed top-0 w-full z-50"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.label("🦅").classes("text-2xl")
            ui.label("Spiżarnia AI").classes(
                "text-xl font-bold tracking-tight text-emerald-800"
            )
        ui.button(icon="settings", on_click=lambda: ui.notify("Ustawienia")).props(
            "flat round color=grey"
        )

    # --- MAIN CONTENT (z paddingiem na header i footer) ---
    with ui.column().classes("w-full max-w-md mx-auto pt-20 pb-24 px-4 gap-6"):

        # Pobierz dane z API
        try:
            inventory_data = await api_call("GET", "/api/inventory")
            items = inventory_data.get("inventory", [])
        except Exception:
            items = []
            ui.notify("Nie udało się pobrać danych z magazynu", type="negative")

        # 1. SEKCJA: "ZJEDZ MNIE" (Priority Dashboard)
        ui.label("⚠️ Do zużycia wkrótce").classes(
            "text-sm font-bold uppercase text-slate-400 tracking-wider ml-1"
        )

        # Filtrujemy produkty "pilne"
        urgent_items = []
        today = date.today()

        for item in items:
            # Oblicz dni do końca
            pct, days = calculate_freshness_percentage(item.get("data_waznosci"))
            if days <= 3:
                item["days_left"] = days
                item["freshness_pct"] = pct
                item["icon"] = get_category_emoji(item.get("kategoria"))
                urgent_items.append(item)

        if urgent_items:
            with ui.scroll_area().classes("w-full h-48 whitespace-nowrap"):
                with ui.row().classes("flex-nowrap gap-4"):
                    for item in urgent_items:
                        # Karta Pilnego Produktu
                        with ui.card().classes(
                            f"{Theme.CARD} w-40 h-44 flex flex-col justify-between shrink-0 bg-red-50 border-red-100"
                        ):
                            with ui.column().classes("gap-0"):
                                ui.label(item["icon"]).classes("text-4xl mb-2")
                                ui.label(item.get("nazwa", "Unknown")).classes(
                                    "font-bold text-slate-800 truncate w-full"
                                )

                                # Logika tekstu dni
                                days_left = item["days_left"]
                                days_text = (
                                    "Dziś!"
                                    if days_left == 0
                                    else (
                                        "Po terminie!"
                                        if days_left < 0
                                        else f"{days_left} dni"
                                    )
                                )
                                ui.label(days_text).classes(
                                    "text-red-600 font-bold text-sm"
                                )

                            ui.button(
                                "Zużyj",
                                on_click=lambda n=item.get("nazwa"): ui.notify(
                                    f"Zużyto: {n}"
                                ),
                            ).classes(
                                "w-full bg-white text-red-600 border border-red-200 hover:bg-red-100 text-sm rounded-lg shadow-sm"
                            )
        else:
            with ui.card().classes(
                f"{Theme.CARD} w-full bg-emerald-50 border-emerald-100 flex items-center justify-center p-6"
            ):
                ui.label("🎉 Wszystko świeże!").classes("text-emerald-700 font-bold")

        # 2. SEKCJA: "WIRTUALNA LODÓWKA" (Grid)
        ui.label("📦 Wszystkie produkty").classes(
            "text-sm font-bold uppercase text-slate-400 tracking-wider ml-1 mt-2"
        )

        # Filtry (Chipsy)
        with ui.row().classes("gap-2 overflow-x-auto pb-2 no-scrollbar"):
            for cat in ["Wszystkie", "Nabiał", "Warzywa", "Mięso", "Inne"]:
                active = (
                    "bg-slate-800 text-white"
                    if cat == "Wszystkie"
                    else "bg-white text-slate-600 border border-slate-200"
                )
                ui.button(cat).classes(
                    f"rounded-full px-4 py-1 text-xs shadow-sm {active}"
                ).props("unelevated")

        # Grid produktów
        with ui.grid(columns=2).classes("w-full gap-3"):
            for item in items:
                # Oblicz świeżość dla każdego produktu
                pct, days = calculate_freshness_percentage(item.get("data_waznosci"))
                color = get_freshness_color(days)
                emoji = get_category_emoji(item.get("kategoria"))

                with ui.card().classes(
                    f"{Theme.CARD} flex flex-col gap-2 relative overflow-hidden group"
                ):
                    # Ikona i Nazwa
                    with ui.row().classes("items-center gap-2"):
                        ui.label(emoji).classes("text-2xl")
                        with ui.column().classes("gap-0 overflow-hidden"):
                            ui.label(item.get("nazwa", "Unknown")).classes(
                                "font-semibold text-sm truncate w-full leading-tight"
                            )
                            ui.label(
                                f"{item.get('ilosc', 0)} {item.get('jednostka', 'szt')}"
                            ).classes("text-xs text-slate-400")

                    # Pasek świeżości (wizualizacja)
                    with ui.element("div").classes(
                        "w-full h-1.5 bg-slate-100 rounded-full mt-auto overflow-hidden"
                    ):
                        ui.element("div").classes(f"h-full {color}").style(
                            f"width: {pct}%"
                        )

    # --- BOTTOM NAVIGATION (Mobile) ---
    with ui.footer().classes(
        "bg-white border-t border-slate-200 h-20 fixed bottom-0 w-full z-50"
    ):
        with ui.row().classes("w-full justify-around items-center h-full pb-2"):
            # Home
            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.open("/")
            ):
                ui.icon("home", size="28px").classes("text-emerald-600")
                ui.label("Dom").classes("text-[10px] text-emerald-600 font-medium")

            # Lista Zakupów
            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.open("/lista")
            ):
                ui.icon("checklist", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Lista").classes("text-[10px] text-slate-400 font-medium")

            # FAB (Floating Action Button) - SCAN
            with ui.column().classes("items-center relative -top-6"):
                with ui.button(on_click=lambda: upload_dialog.open()).classes(
                    "rounded-full w-16 h-16 shadow-lg shadow-emerald-200 bg-emerald-600 hover:bg-emerald-700 flex items-center justify-center border-4 border-slate-50"
                ):
                    ui.icon("document_scanner", size="32px").classes("text-white")

            # Przepisy (Bielik)
            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.open("/bielik")
            ):
                ui.icon("restaurant_menu", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Bielik").classes("text-[10px] text-slate-400 font-medium")

            # Konto
            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.notify("Konto")
            ):
                ui.icon("person", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Ja").classes("text-[10px] text-slate-400 font-medium")


@ui.page("/lista")
async def shopping_list_page():
    """Strona listy zakupów."""
    ui.query("body").classes("bg-slate-50 font-sans")

    # --- HEADER ---
    with ui.header().classes(
        "bg-white text-slate-800 h-16 shadow-sm flex items-center justify-between px-4 fixed top-0 w-full z-50"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.button(icon="arrow_back", on_click=lambda: ui.open("/")).props(
                "flat round color=black"
            )
            ui.label("Lista Zakupów").classes(
                "text-xl font-bold tracking-tight text-slate-800"
            )
        ui.button(icon="share", on_click=lambda: ui.notify("Udostępnij")).props(
            "flat round color=grey"
        )

    # --- MAIN CONTENT ---
    with ui.column().classes("w-full max-w-md mx-auto pt-20 pb-24 px-4 gap-4"):

        # Sugestie (Smart)
        with ui.card().classes(f"{Theme.SURFACE} p-4 bg-emerald-50 border-emerald-100"):
            with ui.row().classes("items-center gap-2 mb-2"):
                ui.label("🧠").classes("text-xl")
                ui.label("Sugerowane przez AI").classes(
                    "font-bold text-emerald-800 text-sm"
                )

            suggestions = [
                "Mleko (kończy się)",
                "Masło (często kupujesz)",
                "Cytryny (do herbaty)",
            ]
            for sug in suggestions:
                with ui.row().classes("w-full items-center justify-between py-1"):
                    ui.label(sug).classes("text-sm text-emerald-700")
                    ui.button(
                        icon="add", on_click=lambda s=sug: ui.notify(f"Dodano: {s}")
                    ).props("flat round dense color=green")

        # Lista właściwa
        ui.label("Twoja lista").classes(
            "text-sm font-bold uppercase text-slate-400 tracking-wider ml-1"
        )

        shopping_items = [
            {"name": "Chleb", "checked": False},
            {"name": "Woda mineralna", "checked": True},
            {"name": "Ręczniki papierowe", "checked": False},
        ]

        with ui.column().classes("w-full gap-2"):
            for item in shopping_items:
                with ui.card().classes(
                    f"{Theme.CARD} flex flex-row items-center justify-between p-3"
                ):
                    with ui.row().classes("items-center gap-3"):
                        cb = ui.checkbox(value=item["checked"])
                        ui.label(item["name"]).classes(
                            "font-medium text-slate-700"
                            + (
                                " line-through text-slate-400"
                                if item["checked"]
                                else ""
                            )
                        )
                        cb.on(
                            "change",
                            lambda e, i=item: ui.notify(f'Zmieniono: {i["name"]}'),
                        )

                    ui.button(icon="delete", on_click=lambda: None).props(
                        "flat round dense color=grey"
                    )

            # Input na nowy produkt
            with ui.row().classes("w-full gap-2 mt-2"):
                ui.input(placeholder="Dodaj produkt...").classes(
                    "flex-1 bg-white rounded-lg px-2"
                ).props("outlined dense")
                ui.button(icon="add").classes(
                    "bg-emerald-600 text-white rounded-lg shadow-sm"
                )

    # --- BOTTOM NAVIGATION ---
    with ui.footer().classes(
        "bg-white border-t border-slate-200 h-20 fixed bottom-0 w-full z-50"
    ):
        with ui.row().classes("w-full justify-around items-center h-full pb-2"):
            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.open("/")
            ):
                ui.icon("home", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Dom").classes("text-[10px] text-slate-400 font-medium")

            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.open("/lista")
            ):
                ui.icon("checklist", size="28px").classes("text-emerald-600")
                ui.label("Lista").classes("text-[10px] text-emerald-600 font-medium")

            with ui.column().classes("items-center relative -top-6"):
                with ui.button(on_click=lambda: ui.notify("Skanuj")).classes(
                    "rounded-full w-16 h-16 shadow-lg shadow-emerald-200 bg-emerald-600 hover:bg-emerald-700 flex items-center justify-center border-4 border-slate-50"
                ):
                    ui.icon("document_scanner", size="32px").classes("text-white")

            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.open("/bielik")
            ):
                ui.icon("restaurant_menu", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Bielik").classes("text-[10px] text-slate-400 font-medium")

            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.notify("Konto")
            ):
                ui.icon("person", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Ja").classes("text-[10px] text-slate-400 font-medium")


@ui.page("/bielik")
async def bielik_chat_page():
    """Strona asystenta AI (Bielik)."""
    ui.query("body").classes("bg-slate-50 font-sans")

    # --- HEADER ---
    with ui.header().classes(
        "bg-white text-slate-800 h-16 shadow-sm flex items-center justify-between px-4 fixed top-0 w-full z-50"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.button(icon="arrow_back", on_click=lambda: ui.open("/")).props(
                "flat round color=black"
            )
            ui.label("Szef Bielik 🦅").classes(
                "text-xl font-bold tracking-tight text-slate-800"
            )
        ui.button(icon="more_vert").props("flat round color=grey")

    # --- MAIN CONTENT ---
    with ui.column().classes(
        "w-full max-w-md mx-auto pt-20 pb-24 px-4 h-screen flex flex-col"
    ):

        # Obszar czatu
        chat_area = ui.column().classes("flex-1 w-full gap-4 overflow-y-auto pb-4")

        with chat_area:
            # Powitanie
            with ui.row().classes("w-full justify-start"):
                with ui.card().classes(
                    "bg-white rounded-2xl rounded-tl-none p-3 shadow-sm max-w-[80%]"
                ):
                    ui.label(
                        "Cześć Marcin! 👋 Widzę, że masz sporo jajek i pomidorów. Może szakszuka na śniadanie?"
                    ).classes("text-slate-700 text-sm")
                    ui.label("10:30").classes(
                        "text-[10px] text-slate-400 mt-1 text-right"
                    )

        # Input
        with ui.row().classes(
            "w-full gap-2 items-center bg-white p-2 rounded-2xl shadow-sm border border-slate-100 mt-auto"
        ):
            ui.button(icon="add").props("flat round dense color=grey")
            input_field = (
                ui.input(placeholder="Napisz do Bielika...")
                .classes("flex-1 border-none")
                .props("borderless dense")
            )

            async def send_message():
                text = input_field.value
                if not text:
                    return

                input_field.value = ""

                # User msg
                with chat_area:
                    with ui.row().classes("w-full justify-end"):
                        with ui.card().classes(
                            "bg-emerald-600 text-white rounded-2xl rounded-tr-none p-3 shadow-sm max-w-[80%]"
                        ):
                            ui.label(text).classes("text-sm")

                # Bot typing...
                with chat_area:
                    typing = ui.label("Bielik pisze...").classes(
                        "text-xs text-slate-400 ml-4"
                    )

                await asyncio.sleep(1.5)
                typing.delete()

                # Bot response (mock)
                with chat_area:
                    with ui.row().classes("w-full justify-start"):
                        with ui.card().classes(
                            "bg-white rounded-2xl rounded-tl-none p-3 shadow-sm max-w-[80%]"
                        ):
                            ui.label("Brzmi świetnie! Przygotuję przepis.").classes(
                                "text-slate-700 text-sm"
                            )

            ui.button(icon="send", on_click=send_message).props(
                "flat round dense color=green"
            )

    # --- BOTTOM NAVIGATION ---
    with ui.footer().classes(
        "bg-white border-t border-slate-200 h-20 fixed bottom-0 w-full z-50"
    ):
        with ui.row().classes("w-full justify-around items-center h-full pb-2"):
            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.open("/")
            ):
                ui.icon("home", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Dom").classes("text-[10px] text-slate-400 font-medium")

            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.open("/lista")
            ):
                ui.icon("checklist", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Lista").classes("text-[10px] text-slate-400 font-medium")

            with ui.column().classes("items-center relative -top-6"):
                with ui.button(on_click=lambda: ui.notify("Skanuj")).classes(
                    "rounded-full w-16 h-16 shadow-lg shadow-emerald-200 bg-emerald-600 hover:bg-emerald-700 flex items-center justify-center border-4 border-slate-50"
                ):
                    ui.icon("document_scanner", size="32px").classes("text-white")

            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.open("/bielik")
            ):
                ui.icon("restaurant_menu", size="28px").classes("text-emerald-600")
                ui.label("Bielik").classes("text-[10px] text-emerald-600 font-medium")

            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: ui.notify("Konto")
            ):
                ui.icon("person", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Ja").classes("text-[10px] text-slate-400 font-medium")

    # --- DIALOG UPLOADU (Wizard) ---
    with ui.dialog() as upload_dialog, ui.card().classes(
        "w-full max-w-sm p-6 rounded-3xl"
    ):
        ui.label("Dodaj Paragon").classes("text-xl font-bold text-center mb-6")

        # Dropzone
        with ui.element("div").classes(
            "w-full h-40 border-2 border-dashed border-emerald-200 bg-emerald-50 rounded-2xl flex flex-col items-center justify-center gap-2 cursor-pointer hover:bg-emerald-100 transition-colors"
        ):
            ui.icon("cloud_upload", size="48px").classes("text-emerald-400")
            ui.label("Dotknij, aby zeskanować").classes("text-emerald-700 font-medium")
            # Tutaj ukryty ui.upload()
            ui.upload(auto_upload=True, label="").classes(
                "absolute opacity-0 w-full h-full"
            )

        ui.label("lub").classes("text-center text-slate-400 my-2 text-sm")

        ui.button("Wpisz ręcznie", icon="edit").classes(
            "w-full bg-slate-100 text-slate-700 hover:bg-slate-200 shadow-none"
        )

        ui.button("Anuluj", on_click=upload_dialog.close).props(
            "flat color=grey"
        ).classes("w-full mt-2")


async def handle_receipt_upload(e, container):
    """Obsługuje upload paragonu z wizardem i animacjami."""
    try:
        file_name = getattr(e, "name", "paragon")

        # Pobierz zawartość pliku
        if hasattr(e, "content"):
            file_obj = e.content
        elif hasattr(e, "file"):
            file_obj = e.file
        else:
            raise Exception("Nie znaleziono zawartości pliku")

        file_content = await file_obj.read()

        # Wyślij do API
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            files = {
                "file": (file_name, file_content, getattr(e, "type", "application/pdf"))
            }
            response = await client.post(f"{API_URL}/api/upload", files=files)
            response.raise_for_status()
            result = response.json()

        task_id = result.get("task_id")
        if task_id:
            # Pokaż wizard z animacjami
            await show_upload_wizard(task_id, file_name)
    except Exception as ex:
        ui.notify(f"Błąd: {str(ex)}", type="negative")


async def show_upload_wizard(task_id: str, file_name: str):
    """Pokazuje wizard uploadu z animacjami postępu."""
    dialog = ui.dialog()
    dialog.classes("w-full max-w-2xl")

    with dialog:
        with ui.card().classes("w-full p-6"):
            ui.label("🔍 Przetwarzanie paragonu").classes(
                "text-2xl font-bold text-slate-800 mb-4"
            )

            # Status message
            status_label = ui.label("📤 Przesyłanie pliku...").classes(
                "text-lg text-slate-600 mb-4"
            )

            # Progress bar
            progress_bar = ui.linear_progress(value=0.05).classes("w-full mb-4")

            # Steps container
            steps_container = ui.column().classes("w-full gap-3 mb-4")

            # Human-readable steps
            steps = [
                {"icon": "📤", "text": "Przesyłanie pliku...", "done": False},
                {"icon": "🔍", "text": "Analizuję obraz...", "done": False},
                {"icon": "🤖", "text": "Asystent czyta produkty...", "done": False},
                {"icon": "📦", "text": "Układam na półkach...", "done": False},
            ]

            step_elements = []
            for step in steps:
                with steps_container:
                    step_row = ui.row().classes(
                        "w-full items-center gap-3 p-3 bg-slate-50 rounded-lg"
                    )
                    with step_row:
                        step_icon = ui.label(step["icon"]).classes("text-2xl")
                        step_text = ui.label(step["text"]).classes("text-slate-600")
                        step_check = ui.icon("check_circle", size="1.5em").classes(
                            "text-emerald-600 ml-auto"
                        )
                        step_check.visible = False
                    step_elements.append(
                        {
                            "row": step_row,
                            "icon": step_icon,
                            "text": step_text,
                            "check": step_check,
                        }
                    )

            # Logs area (optional, collapsible)
            logs_expanded = {"value": False}
            logs_container = ui.column().classes("w-full mt-4")
            logs_area = ui.column().classes(
                "w-full max-h-48 overflow-y-auto bg-slate-50 p-3 rounded-lg text-xs font-mono"
            )
            logs_area.visible = False

            def toggle_logs():
                logs_expanded["value"] = not logs_expanded["value"]
                logs_area.visible = logs_expanded["value"]

            with logs_container:
                ui.button("📋 Pokaż szczegóły", on_click=toggle_logs).props(
                    "flat"
                ).classes("text-sm text-slate-500")
                with logs_area:
                    pass

            # Track progress
            await track_upload_progress(
                task_id, status_label, progress_bar, step_elements, logs_area, dialog
            )

    dialog.open()


async def track_upload_progress(
    task_id: str, status_label, progress_bar, step_elements, logs_area, dialog
):
    """Śledzi postęp przetwarzania z animacjami."""
    max_attempts = 600  # 10 minut
    attempt = 0
    last_log_count = 0
    current_step = 0

    # Mapowanie statusów na kroki
    status_to_step = {
        "uploading": 0,
        "ocr": 1,
        "llm": 2,
        "database": 3,
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
                elif (
                    "LLM" in log_msg
                    or "ASYSTENT" in log_msg
                    or "PRZETWARZANIE" in log_msg
                ):
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
                        ui.label(log_msg).classes(f"{color} mb-1")

                last_log_count = len(recent_logs)

                # Przewiń do dołu
                ui.run_javascript(
                    """
                    const area = arguments[0];
                    if (area) {
                        area.scrollTop = area.scrollHeight;
                    }
                """,
                    logs_area,
                )

            # Sprawdź czy wymagana edycja magazynu
            if status == "awaiting_inventory_review":
                inventory_items = task_data.get("inventory_items", [])
                if inventory_items:
                    mark_step_done(step_elements, 3)
                    status_label.text = "📝 Oczekiwanie na edycję produktów..."
                    progress_bar.value = 0.95

                    # Pokaż dialog edycji (TODO: Implementacja dialogu edycji)
                    dialog.close()
                    # await show_inventory_edit_dialog_modern(task_id, inventory_items)
                    ui.notify("Edycja produktów w przygotowaniu", type="warning")
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
                    ui.notify("Paragon został pomyślnie przetworzony!", type="positive")
                    ui.open("/")
                else:
                    status_label.text = f"❌ {message}"
                    progress_bar.value = 0
                    ui.notify(f"Błąd: {message}", type="negative")

                break

            await asyncio.sleep(1)
            attempt += 1
        except Exception as e:
            status_label.text = f"❌ Błąd śledzenia: {str(e)}"
            break

    if attempt >= max_attempts:
        status_label.text = "⏱️ Przekroczono limit czasu"
        ui.notify("Przetwarzanie trwa zbyt długo", type="warning")


def mark_step_done(step_elements, index):
    """Oznacza krok jako zakończony."""
    if index < len(step_elements):
        step = step_elements[index]
        step["row"].classes("bg-emerald-50 border border-emerald-200")
        step["text"].classes("text-emerald-700 font-semibold")
        step["check"].visible = True


def mark_step_active(step_elements, index):
    """Oznacza krok jako aktywny."""
    if index < len(step_elements):
        step = step_elements[index]
        step["row"].classes("bg-blue-50 border border-blue-200")
        step["text"].classes("text-blue-700 font-semibold")


# Uruchomienie
ui.run(title="Spiżarnia AI", port=8082, favicon="🦅")
