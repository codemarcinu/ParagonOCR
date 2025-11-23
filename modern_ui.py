import os
import sys
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict
import httpx
from nicegui import ui, app

# --- CONFIG ---
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


# --- API HELPERS ---
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
        ui.notify(f"Błąd API: {str(e)}", type="negative")
        return None


# --- LOGIC ---
def calculate_days_left(expiry_date_str: Optional[str]) -> int:
    if not expiry_date_str:
        return 999  # Brak daty = świeże
    try:
        expiry = datetime.fromisoformat(expiry_date_str).date()
        today = date.today()
        return (expiry - today).days
    except ValueError:
        return 999


def get_freshness_color(days):
    if days < 0:
        return Theme.FRESH_BAD
    if days <= 3:
        return Theme.FRESH_WARN
    return Theme.FRESH_GOOD


def get_category_icon(category_name: str) -> str:
    if not category_name:
        return "📦"

    cat = category_name.lower()

    mapping = {
        "nabiał": "🥛",
        "mleko": "🥛",
        "ser": "🧀",
        "jogurt": "🥣",
        "warzywa": "🥦",
        "owoce": "🍎",
        "mięso": "🥩",
        "wędliny": "🥓",
        "ryby": "🐟",
        "pieczywo": "🍞",
        "napoje": "🥤",
        "soki": "🧃",
        "alkohol": "🍷",
        "słodycze": "🍫",
        "przekąski": "🍿",
        "chemia": "🧼",
        "kosmetyki": "🧴",
        "mrożonki": "❄️",
        "przyprawy": "🧂",
        "sosy": "🥫",
        "dania gotowe": "🍱",
        "inne": "📦",
    }

    # Przeszukaj mapowanie (partial match)
    for key, icon in mapping.items():
        if key in cat:
            return icon

    return "📦"


# --- STATE ---
class AppState:
    inventory: List[Dict] = []
    shopping_list: List[Dict] = []
    chat_history: List[Dict] = []  # {role: 'user'/'bot', content: str}
    current_view: str = "home"  # home, list, bielik, account

    @classmethod
    async def refresh_inventory(cls):
        data = await api_call("GET", "/api/inventory")
        if data:
            # API zwraca {"inventory": [...]}, więc pobierz listę
            cls.inventory = data.get("inventory", []) if isinstance(data, dict) else data
            # Przetwórz dane (dodaj days_left i icon)
            for item in cls.inventory:
                item["days_left"] = calculate_days_left(item.get("data_waznosci"))
                item["icon"] = get_category_icon(item.get("kategoria", "Inne"))

    @classmethod
    def generate_smart_list(cls):
        """Generuje listę zakupów na podstawie braków i przeterminowanych produktów."""
        cls.shopping_list = []
        for item in cls.inventory:
            # Logika: mało produktu (< 1) lub przeterminowany (<= 0 dni)
            if item["ilosc"] < 1 or item["days_left"] <= 0:
                cls.shopping_list.append(
                    {
                        "name": item["nazwa"],
                        "reason": "Kończy się" if item["ilosc"] < 1 else "Po terminie",
                        "checked": False,
                    }
                )


@ui.page("/")
async def main_page():
    # Ustawienia globalne
    ui.query("body").classes("bg-slate-50 font-sans")

    # Załaduj dane
    await AppState.refresh_inventory()

    # --- HEADER ---
    with ui.header().classes(
        "bg-white text-slate-800 h-16 shadow-sm flex items-center justify-between px-4 fixed top-0 w-full z-50"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.label("🦅").classes("text-2xl")
            ui.label("Spiżarnia AI").classes(
                "text-xl font-bold tracking-tight text-emerald-800"
            )
        ui.button(icon="settings", on_click=lambda: switch_view("account")).props(
            "flat round color=grey"
        )

    # --- MAIN CONTENT ---
    # Kontener główny z odświeżaniem
    content_container = ui.column().classes(
        "w-full max-w-md mx-auto pt-20 pb-24 px-4 gap-6"
    )

    async def show_consume_dialog(
        item_name: str, item_id: int, current_qty: float, unit: str
    ):
        """Pokazuje dialog do zużycia produktu."""
        with ui.dialog() as dialog, ui.card().classes("p-6 w-full max-w-xs"):
            ui.label(f"Zużyj: {item_name}").classes("text-lg font-bold mb-4")

            qty_input = ui.number(
                "Ile zużyłeś?", value=current_qty, min=0, max=current_qty, step=0.1
            ).classes("w-full mb-4")

            async def consume():
                if qty_input.value > 0:
                    res = await api_call(
                        "POST",
                        "/api/inventory/consume",
                        {"produkt_id": item_id, "ilosc": qty_input.value},
                    )
                    if res:
                        ui.notify(f"Zużyto {qty_input.value} {unit}!", type="positive")
                        dialog.close()
                        await AppState.refresh_inventory()  # Odśwież stan
                        # Odśwież widok (brutalne ale skuteczne, w SPA można lepiej)
                        ui.open("/")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Anuluj", on_click=dialog.close).props("flat color=grey")
                ui.button("Zużyj", on_click=consume).classes(
                    "bg-emerald-600 text-white"
                )
        dialog.open()

    async def render_home():
        content_container.clear()
        with content_container:
            # 1. SEKCJA: "ZJEDZ MNIE" (Priority Dashboard)
            ui.label("⚠️ Do zużycia wkrótce").classes(
                "text-sm font-bold uppercase text-slate-400 tracking-wider ml-1"
            )

            urgent_items = sorted(
                [i for i in AppState.inventory if i["days_left"] <= 3],
                key=lambda x: x["days_left"],
            )

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
                                    ui.label(item["nazwa"]).classes(
                                        "font-bold text-slate-800 truncate w-full"
                                    )

                                    days = item["days_left"]
                                    days_text = (
                                        "Dziś!"
                                        if days == 0
                                        else (
                                            "Po terminie!"
                                            if days < 0
                                            else f"{days} dni"
                                        )
                                    )
                                    ui.label(days_text).classes(
                                        "text-red-600 font-bold text-sm"
                                    )

                                ui.button(
                                    "Zużyj",
                                    on_click=lambda i=item: show_consume_dialog(
                                        i["nazwa"],
                                        i["produkt_id"],
                                        i["ilosc"],
                                        i["jednostka"],
                                    ),
                                ).classes(
                                    "w-full bg-white text-red-600 border border-red-200 hover:bg-red-100 text-sm rounded-lg shadow-sm"
                                )
            else:
                with ui.card().classes(
                    f"{Theme.CARD} w-full bg-emerald-50 border-emerald-100 flex items-center justify-center p-6"
                ):
                    ui.label("🎉 Wszystko świeże!").classes(
                        "text-emerald-700 font-bold"
                    )

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
                for item in AppState.inventory:
                    with ui.card().classes(
                        f"{Theme.CARD} flex flex-col gap-2 relative overflow-hidden group"
                    ):
                        # Ikona i Nazwa
                        with ui.row().classes("items-center gap-2"):
                            ui.label(item["icon"]).classes("text-2xl")
                            with ui.column().classes("gap-0 overflow-hidden"):
                                ui.label(item["nazwa"]).classes(
                                    "font-semibold text-sm truncate w-full leading-tight"
                                )
                                ui.label(
                                    f"{item['ilosc']} {item['jednostka']}"
                                ).classes("text-xs text-slate-400")

                        # Pasek świeżości
                        days = item["days_left"]
                        color = get_freshness_color(days)
                        width = max(10, min(100, days * 10)) if days > 0 else 100

                        with ui.element("div").classes(
                            "w-full h-1.5 bg-slate-100 rounded-full mt-auto overflow-hidden"
                        ):
                            ui.element("div").classes(f"h-full {color}").style(
                                f"width: {width}%"
                            )

    async def render_shopping_list():
        content_container.clear()
        with content_container:
            ui.label("🛒 Lista Zakupów").classes(
                "text-xl font-bold text-slate-800 mb-4"
            )

            # --- Toolbar ---
            with ui.row().classes("w-full gap-2 mb-4"):

                async def generate_list():
                    spinner = ui.spinner("dots").classes("ml-2")
                    ui.notify("Bielik analizuje braki...", type="info")

                    # Strzał do API (Bielik generuje listę)
                    data = await api_call("POST", "/api/shopping-list/generate", {})
                    spinner.delete()

                    if data and "produkty" in data:
                        # Konwersja na format UI
                        AppState.shopping_list = [
                            {
                                "name": p["nazwa"],
                                "reason": "Sugerowane",
                                "checked": False,
                            }
                            for p in data["produkty"]
                        ]
                        await render_shopping_list()  # Przeładuj widok
                    else:
                        ui.notify("Nie udało się wygenerować listy", type="negative")

                ui.button(
                    "Generuj z braków", on_click=generate_list, icon="auto_awesome"
                ).classes(f"flex-1 {Theme.PRIMARY_BTN}")

                # Przycisk dodawania ręcznego do listy (opcjonalnie)
                ui.button(
                    icon="add", on_click=lambda: ui.notify("Dodawanie do listy wkrótce")
                ).classes("bg-slate-200 text-slate-700")

            # --- Lista ---
            if not AppState.shopping_list:
                with ui.column().classes(
                    "w-full items-center justify-center py-12 text-slate-400 gap-4"
                ):
                    ui.icon("shopping_cart", size="48px")
                    ui.label("Lista jest pusta.").classes("text-sm")
                    ui.label('Kliknij "Generuj", aby Bielik sprawdził zapasy.').classes(
                        "text-xs"
                    )
            else:
                with ui.column().classes("w-full gap-2"):
                    for i, item in enumerate(AppState.shopping_list):
                        # Karta produktu na liście
                        card_color = (
                            "bg-slate-100 opacity-75" if item["checked"] else "bg-white"
                        )
                        text_style = (
                            "line-through text-slate-400"
                            if item["checked"]
                            else "text-slate-800 font-medium"
                        )

                        with ui.card().classes(
                            f"w-full p-3 flex-row items-center justify-between shadow-sm rounded-xl border border-slate-100 {card_color} transition-all"
                        ):
                            with ui.row().classes("items-center gap-3"):
                                # Checkbox (Customowy dla wyglądu)
                                state_icon = (
                                    "check_circle"
                                    if item["checked"]
                                    else "radio_button_unchecked"
                                )
                                state_color = (
                                    "text-emerald-500"
                                    if item["checked"]
                                    else "text-slate-400"
                                )

                                ui.icon(state_icon).classes(
                                    f"cursor-pointer text-2xl {state_color}"
                                ).on("click", lambda idx=i: toggle_item(idx))

                                with ui.column().classes("gap-0"):
                                    ui.label(item["name"]).classes(text_style)
                                    if item.get("reason"):
                                        ui.label(item["reason"]).classes(
                                            "text-xs text-orange-400"
                                        )

                            # Przycisk usuwania
                            ui.button(
                                icon="close", on_click=lambda idx=i: remove_item(idx)
                            ).props("flat round color=grey size=sm")

            async def toggle_item(index):
                AppState.shopping_list[index]["checked"] = not AppState.shopping_list[
                    index
                ]["checked"]
                await render_shopping_list()

            async def remove_item(index):
                AppState.shopping_list.pop(index)
                await render_shopping_list()

    async def render_bielik():
        content_container.clear()
        with content_container:
            ui.label("🦅 Bielik AI").classes("text-xl font-bold text-slate-800 mb-4")

            # Obszar czatu
            chat_area = ui.column().classes("w-full gap-4 mb-20")

            def render_messages():
                chat_area.clear()
                with chat_area:
                    if not AppState.chat_history:
                        with ui.column().classes(
                            "w-full items-center justify-center py-12 text-slate-400 gap-2"
                        ):
                            ui.label("🦅").classes("text-4xl")
                            ui.label("W czym mogę pomóc?").classes("text-sm")

                    for msg in AppState.chat_history:
                        is_user = msg["role"] == "user"
                        align = "items-end" if is_user else "items-start"
                        bg = (
                            "bg-emerald-100 text-emerald-900"
                            if is_user
                            else "bg-white border border-slate-200 text-slate-800"
                        )

                        with ui.column().classes(f"w-full {align}"):
                            ui.label(msg["content"]).classes(
                                f"px-4 py-2 rounded-2xl max-w-[80%] text-sm {bg}"
                            )

            render_messages()

            # Input (fixed bottom)
            with ui.footer().classes(
                "bg-white border-t border-slate-200 p-3 fixed bottom-20 w-full z-40"
            ):
                with ui.row().classes("w-full max-w-md mx-auto gap-2 items-center"):
                    input_field = (
                        ui.input(placeholder="Zapytaj o przepis...")
                        .classes("w-full")
                        .props("rounded outlined dense")
                    )

                    async def send():
                        text = input_field.value
                        if not text:
                            return

                        # User msg
                        AppState.chat_history.append({"role": "user", "content": text})
                        input_field.value = ""
                        render_messages()

                        # API call
                        with chat_area:
                            spinner = ui.spinner("dots", size="lg").classes(
                                "text-emerald-500 ml-4"
                            )

                        response = await api_call(
                            "POST", "/api/chat", {"question": text}
                        )
                        spinner.delete()

                        if response:
                            AppState.chat_history.append(
                                {
                                    "role": "bot",
                                    "content": response.get(
                                        "answer", "Brak odpowiedzi"
                                    ),
                                }
                            )
                        else:
                            AppState.chat_history.append(
                                {
                                    "role": "bot",
                                    "content": "Przepraszam, wystąpił błąd połączenia.",
                                }
                            )

                        render_messages()

                    ui.button(icon="send", on_click=send).props(
                        "round flat color=emerald"
                    )
                    input_field.on("keydown.enter", send)

    async def render_account():
        content_container.clear()
        with content_container:
            ui.label("👤 Moje Konto").classes("text-xl font-bold text-slate-800 mb-4")

            with ui.card().classes(f"{Theme.CARD} w-full mb-4"):
                with ui.row().classes("items-center gap-4"):
                    ui.avatar(
                        "person", color="emerald-600", text_color="white"
                    ).classes("text-2xl")
                    with ui.column().classes("gap-0"):
                        ui.label("Marcin").classes("font-bold text-lg")
                        ui.label("Szef Kuchni").classes("text-sm text-slate-500")

            ui.label("Ustawienia").classes(
                "text-sm font-bold uppercase text-slate-400 tracking-wider ml-1 mb-2"
            )

            with ui.card().classes(f"{Theme.CARD} w-full flex flex-col gap-4"):
                with ui.row().classes("justify-between items-center w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("dark_mode", size="24px").classes("text-slate-600")
                        ui.label("Tryb Ciemny").classes("font-medium")
                    ui.switch(on_change=lambda e: ui.notify("Wkrótce..."))

                ui.separator()

                with ui.row().classes("justify-between items-center w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("notifications", size="24px").classes("text-slate-600")
                        ui.label("Powiadomienia").classes("font-medium")
                    ui.switch(value=True, on_change=lambda e: ui.notify("Zapisano"))

            ui.button(
                "Wyloguj", icon="logout", on_click=lambda: ui.notify("Wylogowano")
            ).classes("w-full bg-red-50 text-red-600 hover:bg-red-100 shadow-none mt-4")

    async def switch_view(view_name):
        AppState.current_view = view_name
        if view_name == "home":
            await render_home()
        elif view_name == "list":
            await render_shopping_list()
        elif view_name == "bielik":
            await render_bielik()
        elif view_name == "account":
            await render_account()

    # Inicjalny render
    await switch_view("home")

    # --- BOTTOM NAVIGATION (Mobile) ---
    with ui.footer().classes(
        "bg-white border-t border-slate-200 h-20 fixed bottom-0 w-full z-50"
    ):
        with ui.row().classes("w-full justify-around items-center h-full pb-2"):
            # Home
            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: switch_view("home")
            ):
                ui.icon("home", size="28px").classes("text-emerald-600")
                ui.label("Dom").classes("text-[10px] text-emerald-600 font-medium")

            # Lista Zakupów
            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: switch_view("list")
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
                "click", lambda: switch_view("bielik")
            ):
                ui.icon("restaurant_menu", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Bielik").classes("text-[10px] text-slate-400 font-medium")

            # Konto
            with ui.column().classes("items-center gap-0 cursor-pointer").on(
                "click", lambda: switch_view("account")
            ):
                ui.icon("person", size="28px").classes(
                    "text-slate-400 hover:text-emerald-600 transition-colors"
                )
                ui.label("Ja").classes("text-[10px] text-slate-400 font-medium")

    # --- DIALOG UPLOADU (Wizard) ---
    with ui.dialog() as upload_dialog, ui.card().classes(
        "w-full max-w-sm p-6 rounded-3xl"
    ):
        # Stan wizarda
        wizard_state = {
            "step": "upload",  # upload, processing, success, error
            "logs": [],
            "progress": 0,
        }

        # Kontener zawartości dialogu
        dialog_content = ui.column().classes("w-full items-center")

        def render_wizard():
            dialog_content.clear()
            with dialog_content:
                if wizard_state["step"] == "upload":
                    ui.label("Dodaj Paragon").classes(
                        "text-xl font-bold text-center mb-6"
                    )

                    # Dropzone
                    with ui.element("div").classes(
                        "w-full h-40 border-2 border-dashed border-emerald-200 bg-emerald-50 rounded-2xl flex flex-col items-center justify-center gap-2 cursor-pointer hover:bg-emerald-100 transition-colors relative"
                    ):
                        ui.icon("cloud_upload", size="48px").classes("text-emerald-400")
                        ui.label("Dotknij, aby zeskanować").classes(
                            "text-emerald-700 font-medium"
                        )

                        async def handle_upload(e):
                            wizard_state["step"] = "processing"
                            render_wizard()

                            # Upload pliku
                            try:
                                # NiceGUI upload event content is a file-like object
                                files = {"file": (e.name, e.content, e.type)}
                                response = await api_call(
                                    "POST", "/api/upload", files=files
                                )

                                if response and "task_id" in response:
                                    await track_progress(response["task_id"])
                                else:
                                    raise Exception("Błąd przesyłania pliku")
                            except Exception as ex:
                                wizard_state["step"] = "error"
                                wizard_state["error"] = str(ex)
                                render_wizard()

                        ui.upload(auto_upload=True, on_upload=handle_upload).classes(
                            "absolute opacity-0 w-full h-full"
                        )

                    ui.label("lub").classes("text-center text-slate-400 my-2 text-sm")

                    async def open_manual_add():
                        upload_dialog.close()

                        with ui.dialog() as manual_dialog, ui.card().classes(
                            "w-full max-w-sm p-6"
                        ):
                            ui.label("Dodaj produkt").classes("text-xl font-bold mb-4")
                            name = ui.input("Nazwa produktu").classes("w-full")
                            qty = ui.number("Ilość", value=1.0, min=0.1).classes(
                                "w-full"
                            )
                            unit = ui.select(
                                ["szt", "kg", "l", "op"], value="szt", label="Jednostka"
                            ).classes("w-full")
                            date_inp = (
                                ui.input("Data ważności (opcjonalnie)")
                                .props("type=date")
                                .classes("w-full")
                            )

                            async def save_manual():
                                if not name.value:
                                    ui.notify("Podaj nazwę!", type="warning")
                                    return

                                await api_call(
                                    "POST",
                                    "/api/products/add_manual",
                                    {
                                        "nazwa": name.value,
                                        "ilosc": qty.value,
                                        "jednostka": unit.value,
                                        "data_waznosci": (
                                            date_inp.value if date_inp.value else None
                                        ),
                                    },
                                )
                                manual_dialog.close()
                                ui.notify(f"Dodano: {name.value}", type="positive")
                                await AppState.refresh_inventory()
                                await render_home()

                            ui.button("Zapisz", on_click=save_manual).classes(
                                f"w-full mt-4 {Theme.PRIMARY_BTN}"
                            )

                        manual_dialog.open()

                    ui.button(
                        "Wpisz ręcznie", icon="edit", on_click=open_manual_add
                    ).classes(
                        "w-full bg-slate-100 text-slate-700 hover:bg-slate-200 shadow-none"
                    )
                    ui.button("Anuluj", on_click=upload_dialog.close).props(
                        "flat color=grey"
                    ).classes("w-full mt-2")

                elif wizard_state["step"] == "processing":
                    ui.label("Magia się dzieje... ✨").classes(
                        "text-xl font-bold text-center mb-6 text-emerald-800"
                    )

                    # Animacja / Ikony postępu
                    with ui.row().classes("justify-center gap-4 mb-6"):
                        # Ikona zmienia się w zależności od postępu
                        prog = wizard_state["progress"]
                        icon = (
                            "visibility"
                            if prog < 30
                            else ("psychology" if prog < 70 else "inventory_2")
                        )
                        color = "text-emerald-600"
                        ui.icon(icon, size="64px").classes(f"{color} animate-bounce")

                    # Pasek postępu
                    ui.linear_progress(value=wizard_state["progress"] / 100).classes(
                        "w-full text-emerald-600 mb-4"
                    )

                    # Logi "Magiczne"
                    last_log = (
                        wizard_state["logs"][-1]
                        if wizard_state["logs"]
                        else "Rozpoczynam..."
                    )
                    ui.label(last_log).classes(
                        "text-center text-slate-500 text-sm animate-pulse"
                    )

                elif wizard_state["step"] == "success":
                    ui.icon("check_circle", size="64px").classes(
                        "text-emerald-500 mb-4"
                    )
                    ui.label("Gotowe!").classes(
                        "text-2xl font-bold text-emerald-800 mb-2"
                    )
                    ui.label("Produkty zostały dodane do spiżarni.").classes(
                        "text-center text-slate-500 mb-6"
                    )

                    ui.button(
                        "Super!",
                        on_click=lambda: [
                            upload_dialog.close(),
                            AppState.refresh_inventory(),
                            render_home(),
                        ],
                    ).classes(f"w-full {Theme.PRIMARY_BTN}")

                elif wizard_state["step"] == "error":
                    ui.icon("error", size="64px").classes("text-red-500 mb-4")
                    ui.label("Ups, coś poszło nie tak").classes(
                        "text-xl font-bold text-red-800 mb-2"
                    )
                    ui.label(wizard_state.get("error", "Nieznany błąd")).classes(
                        "text-center text-slate-500 mb-6"
                    )

                    ui.button(
                        "Spróbuj ponownie",
                        on_click=lambda: [
                            wizard_state.update(step="upload"),
                            render_wizard(),
                        ],
                    ).classes("w-full bg-slate-100 text-slate-800")

        async def track_progress(task_id):
            import asyncio

            while True:
                data = await api_call("GET", f"/api/task/{task_id}")
                if not data:
                    break

                status = data.get("status")
                wizard_state["progress"] = data.get("progress", 0)

                # Mapowanie technicznych logów na "magiczne"
                msg = data.get("message", "")
                if "OCR" in msg:
                    magic_msg = "Bielik czyta paragon... 👁️"
                elif "LLM" in msg or "analiza" in msg.lower():
                    magic_msg = "Rozpoznaję produkty... 🧠"
                elif "zapis" in msg.lower():
                    magic_msg = "Układam na półkach... 📦"
                else:
                    magic_msg = msg

                if not wizard_state["logs"] or wizard_state["logs"][-1] != magic_msg:
                    wizard_state["logs"].append(magic_msg)

                render_wizard()

                if status == "completed":
                    wizard_state["step"] = "success"
                    render_wizard()
                    # Odśwież dane w tle
                    await AppState.refresh_inventory()
                    break
                elif status in ["error", "timeout"]:
                    wizard_state["step"] = "error"
                    wizard_state["error"] = data.get("message")
                    render_wizard()
                    break

                await asyncio.sleep(1)

        render_wizard()


# Uruchomienie
ui.run(title="Spiżarnia AI", port=8082, favicon="🦅")
