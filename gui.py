import customtkinter as ctk
from tkinter import filedialog, Toplevel
from PIL import Image
import threading
import queue
import os
import sys
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import desc, asc

# Lokalne importy - gui.py jest w folderze głównym projektu, src jest w ReceiptParser/src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ReceiptParser"))

from src.main import run_processing_pipeline
from src.database import (
    init_db,
    engine,
    Produkt,
    StanMagazynowy,
    KategoriaProduktu,
    AliasProduktu,
    Paragon,
)
from src.config import Config
from src.normalization_rules import find_static_match
from src.bielik import BielikAssistant
from src.config_prompts import (
    load_prompts,
    save_prompts,
    reset_prompts_to_default,
    DEFAULT_PROMPTS,
)
from src.purchase_analytics import PurchaseAnalytics
from src.food_waste_tracker import FoodWasteTracker, get_expiring_products_summary
from src.quick_add import QuickAddHelper
from src.meal_planner import MealPlanner
from history_manager import load_history, add_to_history
from src.unified_design_system import AppColors, AppSpacing, AppFont, Icons, adjust_color
from src.notifications import NotificationToast, NotificationDialog

# Imported Dialogs
from gui_modules.dialogs.mapping_dialog import ProductMappingDialog
from gui_modules.dialogs.review_dialog import ReviewDialog
from gui_modules.dialogs.cooking_dialog import CookingDialog
from gui_modules.dialogs.quick_add_dialog import QuickAddDialog
from gui_modules.dialogs.add_product_dialog import AddProductDialog
from gui_modules.dialogs.chat_dialog import BielikChatDialog
from gui_modules.dialogs.settings_dialog import SettingsDialog
from src.gui_optimizations import (
    VirtualScrollableFrame,
    MemoryProfiler,
    DialogManager,
    AnimationHelper,
    cleanup_widget_tree,
    force_garbage_collection,
    dialog_manager,
    memory_profiler,
    ToolTip,
)
import logging

logger = logging.getLogger(__name__)








class App(ctk.CTk):


    def __init__(self):
        super().__init__()

        self.title("ReceiptParser - System Zarządzania Paragonami")
        self.geometry("1200x700")
        self.minsize(1200, 700)  # Minimalny rozmiar okna
        ctk.set_appearance_mode("System")
        
        # Thread safety for processing
        self.processing_lock = threading.Lock()
        self.is_processing = False
        self.inventory_sort = ("data_waznosci", False) # (column, desc)
        self.history_sort = ("date", True) # (column, desc)
    
        # Notifications
        self.notifications = NotificationToast(self)
        self.notifications_dialog = NotificationDialog(self)
    
        # Register dialogs for lazy loading
        dialog_manager.register_dialog("cooking", CookingDialog)
        dialog_manager.register_dialog("add_product", AddProductDialog)
        dialog_manager.register_dialog("bielik_chat", BielikChatDialog)
        dialog_manager.register_dialog("settings", SettingsDialog)
        
        # Start memory profiling (optional, can be disabled)
        # memory_profiler.start()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)  # Status bar row
        self.grid_rowconfigure(2, weight=0)  # Status bar row
        
        # Automatycznie uruchom migracje bazy danych przy starcie (jeśli baza istnieje)
        self.after(100, self._run_migrations_on_startup)

        # --- MENU BAR ---
        self.menu_frame = ctk.CTkFrame(self)
        self.menu_frame.grid(row=0, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.XS)
        self.menu_frame.grid_columnconfigure(0, weight=1)

        # Menu buttons
        menu_buttons_frame = ctk.CTkFrame(self.menu_frame)
        menu_buttons_frame.pack(side="left", padx=AppSpacing.XS, pady=AppSpacing.XS)

        # Menu buttons z ujednoliconymi kolorami i tooltips
        btn_receipts = ctk.CTkButton(
            menu_buttons_frame,
            text=f"{Icons.RECEIPT} Paragony",
            command=self.show_receipts_tab,
            width=120,
            fg_color=AppColors.PRIMARY,
            hover_color=adjust_color(AppColors.PRIMARY, -15),
        )
        btn_receipts.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_receipts, "Wyświetl analitykę zakupów i paragony")

        btn_cooking = ctk.CTkButton(
            menu_buttons_frame,
            text=f"{Icons.COOKING} Gotowanie",
            command=self.show_cooking_dialog,
            width=120,
            fg_color=AppColors.PRIMARY,
            hover_color=adjust_color(AppColors.PRIMARY, -15),
        )
        btn_cooking.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_cooking, "Zaznacz produkty do zużycia podczas gotowania")

        btn_add = ctk.CTkButton(
            menu_buttons_frame,
            text=f"{Icons.ADD} Dodaj produkt",
            command=self.show_add_product_dialog,
            width=120,
            fg_color=AppColors.PRIMARY,
            hover_color=adjust_color(AppColors.PRIMARY, -15),
        )
        btn_add.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_add, "Dodaj produkt ręcznie do magazynu")

        btn_inventory = ctk.CTkButton(
            menu_buttons_frame,
            text=f"{Icons.INVENTORY} Magazyn",
            command=self.show_inventory,
            width=120,
            fg_color=AppColors.PRIMARY,
            hover_color=adjust_color(AppColors.PRIMARY, -15),
        )
        btn_inventory.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_inventory, "Przeglądaj i edytuj stan magazynu")

        btn_bielik = ctk.CTkButton(
            menu_buttons_frame,
            text=f"{Icons.BEAR} Bielik",
            command=self.show_bielik_chat,
            width=120,
            fg_color=AppColors.PRIMARY,
            hover_color=adjust_color(AppColors.PRIMARY, -15),
        )
        btn_bielik.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_bielik, "Otwórz czat z asystentem kulinarnym Bielik")

        btn_meal_planner = ctk.CTkButton(
            menu_buttons_frame,
            text=f"{Icons.MEAL_PLANNER} Plan Posiłków",
            command=self.show_meal_planner,
            width=120,
            fg_color=AppColors.PRIMARY,
            hover_color=adjust_color(AppColors.PRIMARY, -15),
        )
        btn_meal_planner.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_meal_planner, "Tygodniowy planer posiłków")

        btn_settings = ctk.CTkButton(
            menu_buttons_frame,
            text=f"{Icons.SETTINGS} Ustawienia",
            command=self.show_settings,
            width=120,
            fg_color=AppColors.PRIMARY,
            hover_color=adjust_color(AppColors.PRIMARY, -15),
        )
        btn_settings.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_settings, "Ustawienia i konfiguracja promptów")

        # --- MAIN CONTENT AREA ---
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # --- WIDGETY DLA PARAGONÓW (ANALITYKA) ---
        self.receipts_frame = ctk.CTkFrame(self.content_frame)
        self.receipts_frame.grid(row=0, column=0, sticky="nsew")
        self.receipts_frame.grid_columnconfigure(0, weight=1)
        self.receipts_frame.grid_rowconfigure(2, weight=1)  # Zmieniono z 1 na 2 dla alertów

        # --- MEAL PLANNER FRAME ---
        self.meal_planner_frame = ctk.CTkFrame(self.content_frame)
        self.meal_planner_frame.grid(row=0, column=0, sticky="nsew")
        self.meal_planner_frame.grid_columnconfigure(0, weight=1)
        self.meal_planner_frame.grid_rowconfigure(1, weight=1)
        self.meal_planner_frame.grid_remove()  # Hide by default

        # Header z przyciskami
        header_frame = ctk.CTkFrame(self.receipts_frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header_frame,
            text=f"{Icons.ANALYTICS} Analityka Zakupów",
            font=("Arial", 20, "bold"),
        ).grid(row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w")

        buttons_frame = ctk.CTkFrame(header_frame)
        buttons_frame.grid(
            row=0, column=1, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="e"
        )

        btn_add_receipt = ctk.CTkButton(
            buttons_frame,
            text=f"{Icons.FILE} Dodaj paragon",
            command=self.show_add_receipt_dialog,
            width=150,
            fg_color=AppColors.SUCCESS,
            hover_color=adjust_color(AppColors.SUCCESS, -15),
        )
        btn_add_receipt.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_add_receipt, "Dodaj nowy paragon do przetworzenia")

        btn_refresh = ctk.CTkButton(
            buttons_frame,
            text=f"{Icons.REFRESH} Odśwież",
            command=self.refresh_analytics,
            width=100,
            fg_color=AppColors.INFO,
            hover_color=adjust_color(AppColors.INFO, -15),
        )
        btn_refresh.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_refresh, "Odśwież dane analityki")

        # Frame dla alertów wygasających produktów
        self.expiry_alert_frame = ctk.CTkFrame(self.receipts_frame)
        self.expiry_alert_frame.grid(row=1, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.XS)

        # Scrollable area dla analityki
        self.analytics_scrollable = ctk.CTkScrollableFrame(self.receipts_frame)
        self.analytics_scrollable.grid(row=2, column=0, sticky="nsew", padx=AppSpacing.SM, pady=AppSpacing.SM)
        self.analytics_scrollable.grid_columnconfigure(0, weight=1)

        # Stary widok przetwarzania (ukryty, dostępny przez dialog)
        self.processing_frame = ctk.CTkFrame(self.content_frame)
        self.processing_frame.grid(row=0, column=0, sticky="nsew")
        self.processing_frame.grid_columnconfigure(0, weight=1)
        self.processing_frame.grid_rowconfigure(5, weight=1)

        # Historia plików
        history_frame = ctk.CTkFrame(self.processing_frame)
        history_frame.grid(
            row=0, column=0, columnspan=4, padx=AppSpacing.SM, pady=(10, 5), sticky="ew"
        )
        history_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(history_frame, text="Ostatnie pliki:", font=("Arial", 12)).grid(
            row=0, column=0, padx=AppSpacing.XS, pady=AppSpacing.XS
        )

        self.history_combo = ctk.CTkComboBox(
            history_frame, values=[], command=self.on_history_selected, width=400
        )
        self.history_combo.grid(row=0, column=1, padx=AppSpacing.XS, pady=AppSpacing.XS, sticky="ew")
        self.history_combo.set("Wybierz z historii...")

        # Wczytaj historię plików (po utworzeniu history_combo)
        self.refresh_history()

        self.file_button = ctk.CTkButton(
            history_frame, text="📁 Wybierz plik", command=self.select_file, width=150
        )
        self.file_button.grid(row=0, column=2, padx=AppSpacing.XS, pady=AppSpacing.XS)

        self.file_label = ctk.CTkLabel(
            self.processing_frame, text="Nie wybrano pliku", anchor="w"
        )
        self.file_label.grid(
            row=1, column=0, columnspan=4, padx=AppSpacing.SM, pady=AppSpacing.XS, sticky="ew"
        )

        buttons_frame2 = ctk.CTkFrame(self.processing_frame)
        buttons_frame2.grid(row=2, column=0, columnspan=4, padx=AppSpacing.SM, pady=AppSpacing.XS, sticky="ew")

        self.process_button = ctk.CTkButton(
            buttons_frame2,
            text="🔄 Przetwórz",
            command=self.start_processing,
            state="disabled",
        )
        self.process_button.pack(side="left", padx=AppSpacing.XS)

        self.init_db_button = ctk.CTkButton(
            buttons_frame2,
            text="⚙️ Inicjalizuj bazę danych",
            command=self.initialize_database,
        )
        self.init_db_button.pack(side="left", padx=AppSpacing.XS)

        # Status label i progress bar
        self.status_label = ctk.CTkLabel(
            self.processing_frame, text="Gotowy", anchor="w", font=("Arial", 12)
        )
        self.status_label.grid(
            row=3, column=0, columnspan=4, padx=AppSpacing.SM, pady=(10, 5), sticky="ew"
        )

        self.progress_bar = ctk.CTkProgressBar(self.processing_frame)
        self.progress_bar.grid(
            row=4, column=0, columnspan=4, padx=AppSpacing.SM, pady=AppSpacing.XS, sticky="ew"
        )
        self.progress_bar.set(0)

        self.log_textbox = ctk.CTkTextbox(
            self.processing_frame, state="disabled", wrap="word"
        )
        self.log_textbox.grid(
            row=5, column=0, columnspan=4, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="nsew"
        )

        # Ukryj processing_frame domyślnie
        self.processing_frame.grid_remove()

        # --- Zmienne stanu ---
        self.selected_file_path = None
        self.log_queue = queue.Queue()
        self.prompt_queue = queue.Queue()
        self.prompt_result_queue = queue.Queue()
        self.review_queue = queue.Queue()
        self.review_result_queue = queue.Queue()

        self.after(100, self.process_log_queue)

        # --- STATUS BAR ---
        self.status_bar = ctk.CTkFrame(self)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.XS)
        self.status_bar.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Gotowy",
            anchor="w",
            font=(AppFont.FAMILY, AppFont.SIZE_SM)
        )
        self.status_label.grid(row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.XS, sticky="w")
        
        # --- FAB BUTTON (Floating Action Button) ---
        self.fab_button = ctk.CTkButton(
            self,
            text="⚡",
            width=60,
            height=60,
            font=("Arial", 24, "bold"),
            fg_color=AppColors.SUCCESS,
            hover_color=adjust_color(AppColors.SUCCESS, -20),
            corner_radius=30,
            command=self.show_quick_add_dialog,
        )
        # FAB będzie pozycjonowany absolutnie (overlay)
        self.fab_button.place(relx=0.95, rely=0.95, anchor="se")
        ToolTip(self.fab_button, "⚡ Quick Add - Dodaj produkt w 5 sekund")

        # Show receipts tab by default
        self.show_receipts_tab()
        
        # --- HOTKEYS ---
        self.bind("<Control-n>", lambda event: self.show_quick_add_dialog())

    def show_receipts_tab(self):
        """Pokazuje zakładkę paragonów z analityką"""
        # Ukryj wszystkie inne widoki
        for widget in self.content_frame.winfo_children():
            widget.grid_remove()

        # Pokaż widok analityki
        self.receipts_frame.grid(row=0, column=0, sticky="nsew")
        self.refresh_analytics()

    def show_meal_planner(self):
        """Pokazuje zakładkę planera posiłków"""
        # Ukryj wszystkie inne widoki
        for widget in self.content_frame.winfo_children():
            widget.grid_remove()

        # Pokaż widok meal planera
        self.meal_planner_frame.grid(row=0, column=0, sticky="nsew")
        self.refresh_meal_planner()

    def show_cooking_dialog(self):
        """Otwiera okno gotowania"""
        # Lazy load dialog
        dialog = dialog_manager.get_dialog("cooking", self)
        dialog.wait_window()
        dialog_manager.cleanup()
        force_garbage_collection()

    def show_quick_add_dialog(self):
        """Otwiera okno Quick Add"""
        dialog = QuickAddDialog(self)
        dialog.wait_window()
        if dialog.result:
            self.log("INFO: Produkt został dodany w trybie Quick Add")
            # Odśwież widoki jeśli są otwarte
            if hasattr(self, "receipts_frame") and self.receipts_frame.winfo_viewable():
                self.refresh_analytics()

    def show_add_product_dialog(self):
        """Otwiera okno dodawania produktu"""
        # Lazy load dialog
        dialog = dialog_manager.get_dialog("add_product", self)
        dialog.wait_window()
        if hasattr(dialog, 'result') and dialog.result:
            self.log("INFO: Produkt został dodany do magazynu")
        dialog_manager.cleanup()
        force_garbage_collection()

    def toggle_history_sort(self, column):
        """Przełącza sortowanie historii paragonów"""
        current_col, current_desc = self.history_sort
        if current_col == column:
            # Toggle desc
            self.history_sort = (column, not current_desc)
        else:
            # New col, default asc
            self.history_sort = (column, False)
        self.refresh_analytics()

    def toggle_inventory_sort(self, inv_window, session, column):
        current_col, current_desc = self.inventory_sort
        if current_col == column:
            # Toggle desc
            self.inventory_sort = (column, not current_desc)
        else:
            # New col, default asc
            self.inventory_sort = (column, False)
        
        self.refresh_inventory_window(inv_window, session)

    def show_inventory(self):
        """Pokazuje stan magazynu z możliwością edycji"""
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # Create inventory window
        inv_window = ctk.CTkToplevel(self)
        inv_window.title("Stan Magazynu - Edycja")
        inv_window.geometry("1200x700")

        # Frame dla przycisków akcji
        action_frame = ctk.CTkFrame(inv_window)
        action_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.XS)

        # Get data first
        query = (
            session.query(StanMagazynowy)
            .join(Produkt)
            .filter(StanMagazynowy.ilosc > 0)
        )
        
        # Sortowanie
        sort_col, sort_desc = self.inventory_sort
        order_func = desc if sort_desc else asc
        
        if sort_col == "produkt":
            query = query.order_by(order_func(Produkt.znormalizowana_nazwa))
        elif sort_col == "ilosc":
            query = query.order_by(order_func(StanMagazynowy.ilosc))
        else: # data_waznosci default
            query = query.order_by(order_func(StanMagazynowy.data_waznosci))
            
        stany = query.all()

        inventory_items = []
        
        save_btn = ctk.CTkButton(
            action_frame,
            text=f"{Icons.SAVE} Zapisz zmiany",
            command=lambda: self.save_inventory_changes(
                inv_window, session, inventory_items
            ),
            fg_color=AppColors.SUCCESS,
            hover_color=adjust_color(AppColors.SUCCESS, -15),
            width=150,
        )
        save_btn.pack(side="left", padx=AppSpacing.XS)

        ctk.CTkButton(
            action_frame,
            text=f"{Icons.REFRESH} Odśwież",
            command=lambda: self.refresh_inventory_window(inv_window, session),
            fg_color=AppColors.INFO,
            hover_color=adjust_color(AppColors.INFO, -15),
            width=150,
        ).pack(side="left", padx=AppSpacing.XS)

        # Use virtual scrolling for large datasets (>1000 rows)
        use_virtual_scrolling = len(stany) > 1000
        
        if use_virtual_scrolling:
            # Headers frame (fixed)
            headers_frame = ctk.CTkFrame(inv_window)
            headers_frame.pack(fill="x", padx=AppSpacing.SM, pady=(AppSpacing.SM, 0))
            
            headers = [
                "Produkt",
                "Ilość",
                "Jednostka",
                "Data ważności",
                "Zamrożone",
                "Status",
                "Akcje",
            ]
            for col, text in enumerate(headers):
                key = None
                if text == "Produkt": key = "produkt"
                elif text == "Ilość": key = "ilosc"
                elif text == "Data ważności": key = "data_waznosci"
                elif text == "Status": key = "data_waznosci"
                
                if key:
                    marker = ""
                    if self.inventory_sort[0] == key:
                        marker = " ▼" if self.inventory_sort[1] else " ▲"
                    
                    ctk.CTkButton(
                        headers_frame, 
                        text=f"{text}{marker}", 
                        font=("Arial", 12, "bold"),
                        command=lambda k=key: self.toggle_inventory_sort(inv_window, session, k),
                        fg_color="transparent",
                        hover_color=AppColors.BG_DARK,
                        anchor="w",
                        width=100
                    ).grid(row=0, column=col, padx=AppSpacing.XS, pady=AppSpacing.XS)
                else:
                    ctk.CTkLabel(headers_frame, text=text, font=("Arial", 12, "bold")).grid(
                        row=0, column=col, padx=AppSpacing.XS, pady=AppSpacing.XS
                    )
            
            # Virtual scrollable frame
            def render_row(index, stan_data, row_frame):
                """Render a single row in virtual scrolling."""
                stan = stan_data["stan"]
                i = index
                
                row_frame.grid_columnconfigure(0, weight=1)
                
                # Produkt (tylko do odczytu)
                ctk.CTkLabel(
                    row_frame, text=stan.produkt.znormalizowana_nazwa, width=250
                ).grid(row=0, column=0, padx=AppSpacing.XS, pady=2, sticky="w")

                # Ilość (edytowalna)
                ilosc_entry = ctk.CTkEntry(row_frame, width=100)
                ilosc_entry.insert(0, str(stan.ilosc))
                ilosc_entry.grid(row=0, column=1, padx=AppSpacing.XS, pady=2)

                # Jednostka (edytowalna)
                jednostka_entry = ctk.CTkEntry(row_frame, width=100)
                jednostka_entry.insert(0, stan.jednostka_miary or "szt")
                jednostka_entry.grid(row=0, column=2, padx=AppSpacing.XS, pady=2)

                # Data ważności (edytowalna)
                data_entry = ctk.CTkEntry(
                    row_frame, width=120, placeholder_text="YYYY-MM-DD"
                )
                if stan.data_waznosci:
                    data_entry.insert(0, stan.data_waznosci.strftime("%Y-%m-%d"))
                data_entry.grid(row=0, column=3, padx=AppSpacing.XS, pady=2)

                # Checkbox "Zamrożone"
                zamrozone_checkbox = ctk.CTkCheckBox(row_frame, text="")
                zamrozone_checkbox.grid(row=0, column=4, padx=AppSpacing.XS, pady=2)
                if getattr(stan, "zamrozone", False):
                    zamrozone_checkbox.select()
                else:
                    zamrozone_checkbox.deselect()

                # Status
                if stan.data_waznosci:
                    if stan.data_waznosci < date.today():
                        status = "⚠️ Przeterminowany"
                        color = AppColors.EXPIRED
                    elif stan.data_waznosci <= date.today() + timedelta(days=3):
                        status = "🔴 Wkrótce przeterminowany"
                        color = AppColors.EXPIRING_SOON
                    else:
                        status = "✅ OK"
                        color = AppColors.OK
                else:
                    status = "❓ Brak daty"
                    color = AppColors.UNKNOWN

                status_label = ctk.CTkLabel(
                    row_frame, text=status, width=150, text_color=color
                )
                status_label.grid(row=0, column=5, padx=AppSpacing.XS, pady=2)

                # Frame dla przycisków akcji
                actions_frame = ctk.CTkFrame(row_frame)
                actions_frame.grid(row=0, column=6, padx=AppSpacing.XS, pady=2)

                waste_btn = ctk.CTkButton(
                    actions_frame,
                    text="🗑️",
                    command=lambda s=stan: self.mark_as_waste(inv_window, session, s),
                    fg_color="#8b4513",
                    hover_color="#654321",
                    width=40,
                    height=25,
                )
                waste_btn.pack(side="left", padx=2)

                delete_btn = ctk.CTkButton(
                    actions_frame,
                    text=f"{Icons.DELETE} Usuń",
                    command=lambda s=stan: self.delete_inventory_item(
                        inv_window, session, s
                    ),
                    fg_color=AppColors.ERROR,
                    hover_color=adjust_color(AppColors.ERROR, -15),
                    width=80,
                    height=25,
                )
                delete_btn.pack(side="left", padx=2)
                
                # Store in inventory_items
                inventory_items.append({
                    "stan": stan,
                    "ilosc_entry": ilosc_entry,
                    "jednostka_entry": jednostka_entry,
                    "data_entry": data_entry,
                    "zamrozone_checkbox": zamrozone_checkbox,
                    "status_label": status_label,
                })
            
            # Prepare data for virtual scrolling
            data_list = [{"stan": stan} for stan in stany]
            
            scrollable = VirtualScrollableFrame(
                inv_window,
                item_height=50,
                page_size=100,
                render_callback=render_row
            )
            scrollable.pack(fill="both", expand=True, padx=AppSpacing.SM, pady=AppSpacing.SM)
            scrollable.set_data(data_list, use_pagination_threshold=1000)
            
        else:
            # Standard scrolling for smaller datasets
            scrollable = ctk.CTkScrollableFrame(inv_window)
            scrollable.pack(fill="both", expand=True, padx=AppSpacing.SM, pady=AppSpacing.SM)

            # Headers
            headers = [
                "Produkt",
                "Ilość",
                "Jednostka",
                "Data ważności",
                "Zamrożone",
                "Status",
                "Akcje",
            ]
            for col, text in enumerate(headers):
                key = None
                if text == "Produkt": key = "produkt"
                elif text == "Ilość": key = "ilosc"
                elif text == "Data ważności": key = "data_waznosci"
                elif text == "Status": key = "data_waznosci"
                
                if key:
                    marker = ""
                    if self.inventory_sort[0] == key:
                        marker = " ▼" if self.inventory_sort[1] else " ▲"
                        
                    ctk.CTkButton(
                        scrollable, 
                        text=f"{text}{marker}", 
                        font=("Arial", 12, "bold"),
                        command=lambda k=key: self.toggle_inventory_sort(inv_window, session, k),
                        fg_color="transparent",
                        hover_color=AppColors.BG_DARK,
                        anchor="w",
                        width=100
                    ).grid(row=0, column=col, padx=AppSpacing.XS, pady=AppSpacing.XS)
                else:
                    ctk.CTkLabel(scrollable, text=text, font=("Arial", 12, "bold")).grid(
                        row=0, column=col, padx=AppSpacing.XS, pady=AppSpacing.XS
                    )

            for i, stan in enumerate(stany):
                row = i + 1
                
                # Create row frame with alternating colors
                row_frame = ctk.CTkFrame(
                    scrollable,
                    fg_color=AppColors.SURFACE_DARK if i % 2 == 0 else AppColors.BG_DARK
                )
                row_frame.grid(row=row, column=0, columnspan=len(headers), sticky="ew", padx=AppSpacing.SM, pady=1)
                row_frame.grid_columnconfigure(0, weight=1)

                # Produkt (tylko do odczytu)
                ctk.CTkLabel(
                    row_frame, text=stan.produkt.znormalizowana_nazwa, width=250
                ).grid(row=0, column=0, padx=AppSpacing.XS, pady=2, sticky="w")

                # Ilość (edytowalna)
                ilosc_entry = ctk.CTkEntry(row_frame, width=100)
                ilosc_entry.insert(0, str(stan.ilosc))
                ilosc_entry.grid(row=0, column=1, padx=AppSpacing.XS, pady=2)

                # Jednostka (edytowalna)
                jednostka_entry = ctk.CTkEntry(row_frame, width=100)
                jednostka_entry.insert(0, stan.jednostka_miary or "szt")
                jednostka_entry.grid(row=0, column=2, padx=AppSpacing.XS, pady=2)

                # Data ważności (edytowalna)
                data_entry = ctk.CTkEntry(
                    row_frame, width=120, placeholder_text="YYYY-MM-DD"
                )
                if stan.data_waznosci:
                    data_entry.insert(0, stan.data_waznosci.strftime("%Y-%m-%d"))
                data_entry.grid(row=0, column=3, padx=AppSpacing.XS, pady=2)

                # Checkbox "Zamrożone"
                zamrozone_checkbox = ctk.CTkCheckBox(row_frame, text="")
                zamrozone_checkbox.grid(row=0, column=4, padx=AppSpacing.XS, pady=2)
                if getattr(stan, "zamrozone", False):
                    zamrozone_checkbox.select()
                else:
                    zamrozone_checkbox.deselect()

                # Status (tylko do odczytu)
                if stan.data_waznosci:
                    if stan.data_waznosci < date.today():
                        status = f"{Icons.STATUS_DOT} Przeterminowany"
                        color = AppColors.EXPIRED
                    elif stan.data_waznosci <= date.today() + timedelta(days=3):
                        status = f"{Icons.STATUS_DOT} Wkrótce"
                        color = AppColors.EXPIRING_SOON
                    else:
                        status = f"{Icons.STATUS_DOT} OK"
                        color = AppColors.OK
                else:
                    status = f"{Icons.STATUS_DOT} Brak daty"
                    color = AppColors.UNKNOWN

                status_label = ctk.CTkLabel(
                    row_frame, text=status, width=150, text_color=color
                )
                status_label.grid(row=0, column=5, padx=AppSpacing.XS, pady=2)

                # Frame dla przycisków akcji
                actions_frame = ctk.CTkFrame(row_frame)
                actions_frame.grid(row=0, column=6, padx=AppSpacing.XS, pady=2)

                # Przycisk zmarnowany
                waste_btn = ctk.CTkButton(
                    actions_frame,
                    text="🗑️",
                    command=lambda s=stan: self.mark_as_waste(inv_window, session, s),
                    fg_color=AppColors.WASTE,
                    hover_color=adjust_color(AppColors.WASTE, -15),
                    width=40,
                    height=25,
                )
                waste_btn.pack(side="left", padx=AppSpacing.XS)
                ToolTip(waste_btn, "Oznacz jako zmarnowany")

                # Przycisk usuwania
                delete_btn = ctk.CTkButton(
                    actions_frame,
                    text=f"{Icons.DELETE} Usuń",
                    command=lambda s=stan: self.delete_inventory_item(
                        inv_window, session, s
                    ),
                    fg_color=AppColors.ERROR,
                    hover_color=adjust_color(AppColors.ERROR, -15),
                    width=80,
                    height=25,
                )
                delete_btn.pack(side="left", padx=AppSpacing.XS)
                ToolTip(delete_btn, "Usuń z magazynu")

                inventory_items.append(
                    {
                        "stan": stan,
                        "ilosc_entry": ilosc_entry,
                        "jednostka_entry": jednostka_entry,
                        "data_entry": data_entry,
                        "zamrozone_checkbox": zamrozone_checkbox,
                        "status_label": status_label,
                    }
                )

        if not stany:
            empty_label = ctk.CTkLabel(
                inv_window, text="Brak produktów w magazynie", font=("Arial", 14)
            )
            empty_label.pack(pady=AppSpacing.LG)

        # Przechowaj referencje w oknie
        inv_window.inventory_items = inventory_items
        inv_window.session = session
        inv_window.scrollable = scrollable if not use_virtual_scrolling else None

        def on_close():
            """Cleanup on window close."""
            try:
                cleanup_widget_tree(inv_window)
                session.close()
                dialog_manager.cleanup()
                force_garbage_collection()
            except Exception as e:
                import logging
                logging.warning(f"Error during inventory window cleanup: {e}")
            inv_window.destroy()

        inv_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Smooth animation
        AnimationHelper.fade_in(inv_window)

    def save_inventory_changes(self, inv_window, session, inventory_items):
        """Zapisuje zmiany w magazynie"""
        try:
            for item in inventory_items:
                stan = item["stan"]

                # Aktualizuj ilość
                ilosc_str = item["ilosc_entry"].get().strip()
                if not ilosc_str:
                    session.rollback()
                    self.notifications.show_error(f"Ilość nie może być pusta dla produktu {stan.produkt.znormalizowana_nazwa}")
                    return
                try:
                    nowa_ilosc = Decimal(ilosc_str.replace(",", "."))
                    if nowa_ilosc < 0:
                        session.rollback()
                        self.notifications.show_error(f"Ilość nie może być ujemna dla produktu {stan.produkt.znormalizowana_nazwa}")
                        return
                    if nowa_ilosc == 0:
                        # Usuń produkt z magazynu jeśli ilość = 0
                        session.delete(stan)
                        continue
                    stan.ilosc = nowa_ilosc
                except (ValueError, InvalidOperation) as e:
                    session.rollback()
                    self.notifications.show_error(f"Nieprawidłowa ilość '{ilosc_str}' dla produktu {stan.produkt.znormalizowana_nazwa}")
                    return

                # Aktualizuj jednostkę
                stan.jednostka_miary = item["jednostka_entry"].get().strip() or None

                # Aktualizuj datę ważności
                data_str = item["data_entry"].get().strip()
                if data_str:
                    try:
                        stan.data_waznosci = datetime.strptime(
                            data_str, "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        session.rollback()
                        self.notifications.show_error(f"Nieprawidłowy format daty dla produktu {stan.produkt.znormalizowana_nazwa}\nUżyj formatu YYYY-MM-DD")
                        return
                else:
                    stan.data_waznosci = None

                # Aktualizuj stan zamrożenia
                stan.zamrozone = item["zamrozone_checkbox"].get()

            session.commit()
            self.notifications.show_success("Zmiany zostały zapisane!")
            # Odśwież okno
            self.refresh_inventory_window(inv_window, session)
        except Exception as e:
            session.rollback()
            self.notifications.show_error(f"Nie udało się zapisać zmian: {e}")

    def mark_as_waste(self, inv_window, session, stan):
        """Oznacza produkt jako zmarnowany"""
        import sqlite3
        from datetime import date

        if self.notifications_dialog.confirm(
            "Potwierdzenie",
            f"Czy na pewno chcesz oznaczyć {stan.produkt.znormalizowana_nazwa} jako zmarnowany?",
        ):
            try:
                # Zapisz do tabeli zmarnowane_produkty
                project_root = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                db_path = os.path.join(project_root, "ReceiptParser", "data", "receipts.db")

                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Przybliżona wartość (można rozszerzyć o rzeczywiste ceny)
                wartosc = float(stan.ilosc) * 5.0  # Przybliżenie

                cursor.execute(
                    """
                    INSERT INTO zmarnowane_produkty (produkt_id, data_zmarnowania, powod, wartosc)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        stan.produkt_id,
                        date.today().isoformat(),
                        "Oznaczony przez użytkownika",
                        wartosc,
                    ),
                )

                conn.commit()
                conn.close()

                # Usuń z magazynu
                session.delete(stan)
                session.commit()

                self.notifications.show_success(f"Produkt '{stan.produkt.znormalizowana_nazwa}' został oznaczony jako zmarnowany")
                # Odśwież okno
                self.refresh_inventory_window(inv_window, session)
            except Exception as e:
                session.rollback()
                self.notifications.show_error(f"Nie udało się oznaczyć produktu jako zmarnowany: {e}")

    def delete_inventory_item(self, inv_window, session, stan):
        """Usuwa produkt z magazynu"""
        if self.notifications_dialog.confirm(
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć {stan.produkt.znormalizowana_nazwa} z magazynu?",
        ):
            try:
                session.delete(stan)
                session.commit()
                self.notifications.show_success("Produkt został usunięty z magazynu")
                # Odśwież okno
                self.refresh_inventory_window(inv_window, session)
            except Exception as e:
                session.rollback()
                self.notifications.show_error(f"Nie udało się usunąć produktu: {e}")

    def refresh_inventory_window(self, inv_window, session):
        """Odświeża okno magazynu"""
        session.close()
        inv_window.destroy()
        self.show_inventory()

    def close_inventory_window(self, inv_window, session):
        """Zamyka okno magazynu i zamyka sesję"""
        session.close()
        inv_window.destroy()

    def show_bielik_chat(self):
        """Otwiera okno czatu z Bielikiem"""
        # Lazy load dialog
        dialog = dialog_manager.get_dialog("bielik_chat", self)
        dialog.wait_window()
        dialog_manager.cleanup()
        force_garbage_collection()

    def show_settings(self):
        """Otwiera okno ustawień"""
        # Lazy load dialog
        dialog = dialog_manager.get_dialog("settings", self)
        dialog.wait_window()
        dialog_manager.cleanup()
        force_garbage_collection()

    def show_add_receipt_dialog(self):
        """Otwiera widok do dodawania paragonu"""
        # Ukryj analitykę i pokaż widok przetwarzania
        self.receipts_frame.grid_remove()
        self.processing_frame.grid(row=0, column=0, sticky="nsew")

    def refresh_expiry_alerts(self):
        """Odświeża alerty wygasających produktów"""
        # Wyczyść poprzednią zawartość
        for widget in self.expiry_alert_frame.winfo_children():
            widget.destroy()

        try:
            with FoodWasteTracker() as tracker:
                tracker.update_priorities()
                alerts = tracker.get_expiry_alerts()

                # Kolory zgodnie z specyfikacją
                colors = {
                    "expired": AppColors.EXPIRED,  # critical
                    "critical": AppColors.EXPIRED,  # critical
                    "warning": AppColors.EXPIRING_SOON,  # warning
                    "normal": AppColors.OK,  # success
                }

                # Liczniki
                expired_count = len(alerts["expired"])
                critical_count = len(alerts["critical"])
                warning_count = len(alerts["warning"])

                if expired_count == 0 and critical_count == 0 and warning_count == 0:
                    # Brak alertów - pokaż zielony status
                    status_label = ctk.CTkLabel(
                        self.expiry_alert_frame,
                        text="✅ Wszystkie produkty są w porządku",
                        font=("Arial", 14),
                        text_color=colors["normal"],
                    )
                    status_label.pack(pady=AppSpacing.SM, padx=AppSpacing.SM)
                    return

                # Frame dla alertów
                alerts_container = ctk.CTkFrame(self.expiry_alert_frame)
                alerts_container.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)

                # Nagłówek
                header_label = ctk.CTkLabel(
                    alerts_container,
                    text="🚨 Alerty Wygasających Produktów",
                    font=("Arial", 16, "bold"),
                )
                header_label.pack(pady=AppSpacing.XS)

                # Przeterminowane
                if expired_count > 0:
                    expired_frame = ctk.CTkFrame(alerts_container)
                    expired_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.XS)
                    expired_frame.configure(fg_color=colors["expired"])

                    expired_label = ctk.CTkLabel(
                        expired_frame,
                        text=f"❌ PRZETERMINOWANE: {expired_count} produktów",
                        font=("Arial", 14, "bold"),
                        text_color="white",
                    )
                    expired_label.pack(pady=AppSpacing.XS)

                    # Lista produktów
                    for product in alerts["expired"][:5]:  # Maksymalnie 5
                        product_text = f"  • {product['nazwa']} ({product['ilosc']} {product['jednostka']})"
                        if product["data_waznosci"]:
                            product_text += f" - wygasł {abs(product['days_until_expiry'])} dni temu"
                        product_label = ctk.CTkLabel(
                            expired_frame,
                            text=product_text,
                            font=("Arial", 12),
                            text_color="white",
                            anchor="w",
                        )
                        product_label.pack(padx=AppSpacing.SM, pady=2, anchor="w")

                # Krytyczne (dziś)
                if critical_count > 0:
                    critical_frame = ctk.CTkFrame(alerts_container)
                    critical_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.XS)
                    critical_frame.configure(fg_color=colors["critical"])

                    critical_label = ctk.CTkLabel(
                        critical_frame,
                        text=f"🔴 KRYTYCZNE (dziś): {critical_count} produktów",
                        font=("Arial", 14, "bold"),
                        text_color="white",
                    )
                    critical_label.pack(pady=AppSpacing.XS)

                    for product in alerts["critical"][:5]:
                        product_text = f"  • {product['nazwa']} ({product['ilosc']} {product['jednostka']})"
                        product_label = ctk.CTkLabel(
                            critical_frame,
                            text=product_text,
                            font=("Arial", 12),
                            text_color="white",
                            anchor="w",
                        )
                        product_label.pack(padx=AppSpacing.SM, pady=2, anchor="w")

                # Ostrzeżenia (3 dni)
                if warning_count > 0:
                    warning_frame = ctk.CTkFrame(alerts_container)
                    warning_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.XS)
                    warning_frame.configure(fg_color=colors["warning"])

                    warning_label = ctk.CTkLabel(
                        warning_frame,
                        text=f"⚠️ OSTRZEŻENIE (≤3 dni): {warning_count} produktów",
                        font=("Arial", 14, "bold"),
                        text_color="white",
                    )
                    warning_label.pack(pady=AppSpacing.XS)

                    for product in alerts["warning"][:5]:
                        product_text = f"  • {product['nazwa']} ({product['ilosc']} {product['jednostka']})"
                        if product["days_until_expiry"] is not None:
                            product_text += f" - {product['days_until_expiry']} dni do wygaśnięcia"
                        product_label = ctk.CTkLabel(
                            warning_frame,
                            text=product_text,
                            font=("Arial", 12),
                            text_color="white",
                            anchor="w",
                        )
                        product_label.pack(padx=AppSpacing.SM, pady=2, anchor="w")

                # Przycisk do otwarcia szczegółów
                if expired_count + critical_count + warning_count > 0:
                    buttons_frame = ctk.CTkFrame(alerts_container)
                    buttons_frame.pack(pady=AppSpacing.SM)

                    btn_details = ctk.CTkButton(
                        buttons_frame,
                        text="📋 Zobacz wszystkie wygasające produkty",
                        command=self.show_expiring_products_details,
                        fg_color=AppColors.INFO,
                        hover_color=adjust_color(AppColors.INFO, -15),
                    )
                    btn_details.pack(side="left", padx=AppSpacing.XS)

                    btn_bielik_suggest = ctk.CTkButton(
                        buttons_frame,
                        text="🦅 Zapytaj Bielika: Co zrobić z wygasającymi?",
                        command=self.ask_bielik_about_expiring,
                        fg_color=AppColors.PRIMARY,
                        hover_color=adjust_color(AppColors.PRIMARY, -15),
                    )
                    btn_bielik_suggest.pack(side="left", padx=AppSpacing.XS)

        except Exception as e:
            error_label = ctk.CTkLabel(
                self.expiry_alert_frame,
                text=f"Błąd podczas ładowania alertów: {str(e)}",
                font=("Arial", 12),
                text_color=AppColors.ERROR,
            )
            error_label.pack(pady=AppSpacing.SM, padx=AppSpacing.SM)

    def ask_bielik_about_expiring(self):
        """Zadaje Bielikowi pytanie o wygasające produkty"""
        try:
            with BielikAssistant() as assistant:
                suggestion = assistant.suggest_use_expiring_products()

                # Pokaż odpowiedź w oknie dialogowym
                dialog = ctk.CTkToplevel(self)
                dialog.title("🦅 Bielik - Sugestie dla wygasających produktów")
                dialog.geometry("800x500")

                header = ctk.CTkLabel(
                    dialog,
                    text="🦅 Bielik - Sugestie",
                    font=("Arial", 18, "bold"),
                )
                header.pack(pady=AppSpacing.SM)

                scrollable = ctk.CTkScrollableFrame(dialog)
                scrollable.pack(fill="both", expand=True, padx=AppSpacing.LG, pady=AppSpacing.SM)

                suggestion_label = ctk.CTkLabel(
                    scrollable,
                    text=suggestion,
                    font=("Arial", 12),
                    wraplength=700,
                    justify="left",
                    anchor="w",
                )
                suggestion_label.pack(pady=AppSpacing.SM, padx=AppSpacing.SM, anchor="w")

                ctk.CTkButton(
                    dialog,
                    text="Zamknij",
                    command=dialog.destroy,
                    width=150,
                ).pack(pady=AppSpacing.SM)

        except Exception as e:
            self.notifications.show_error(f"Nie udało się uzyskać sugestii od Bielika: {str(e)}")

    def show_expiring_products_details(self):
        """Pokazuje szczegółowy widok wygasających produktów"""
        details_window = ctk.CTkToplevel(self)
        details_window.title("Wygasające Produkty - Szczegóły")
        details_window.geometry("1000x600")

        # Scrollable frame
        scrollable = ctk.CTkScrollableFrame(details_window)
        scrollable.pack(fill="both", expand=True, padx=AppSpacing.SM, pady=AppSpacing.SM)

        try:
            with FoodWasteTracker() as tracker:
                tracker.update_priorities()
                alerts = tracker.get_expiry_alerts()

                # Nagłówek
                ctk.CTkLabel(
                    scrollable,
                    text="🚨 Wygasające Produkty",
                    font=("Arial", 18, "bold"),
                ).pack(pady=AppSpacing.SM)

                # Przeterminowane
                if alerts["expired"]:
                    ctk.CTkLabel(
                        scrollable,
                        text="❌ PRZETERMINOWANE",
                        font=("Arial", 16, "bold"),
                        text_color=AppColors.EXPIRED,
                    ).pack(pady=AppSpacing.SM, anchor="w")

                    for product in alerts["expired"]:
                        product_text = f"• {product['nazwa']} - {product['ilosc']} {product['jednostka']}"
                        if product["data_waznosci"]:
                            product_text += f" (wygasł {abs(product['days_until_expiry'])} dni temu)"
                        ctk.CTkLabel(
                            scrollable, text=product_text, font=("Arial", 12)
                        ).pack(padx=AppSpacing.LG, pady=2, anchor="w")

                # Krytyczne
                if alerts["critical"]:
                    ctk.CTkLabel(
                        scrollable,
                        text="🔴 KRYTYCZNE (dziś wygasa)",
                        font=("Arial", 16, "bold"),
                        text_color=AppColors.EXPIRED,
                    ).pack(pady=AppSpacing.SM, anchor="w")

                    for product in alerts["critical"]:
                        product_text = f"• {product['nazwa']} - {product['ilosc']} {product['jednostka']}"
                        ctk.CTkLabel(
                            scrollable, text=product_text, font=("Arial", 12)
                        ).pack(padx=AppSpacing.LG, pady=2, anchor="w")

                # Ostrzeżenia
                if alerts["warning"]:
                    ctk.CTkLabel(
                        scrollable,
                        text="⚠️ OSTRZEŻENIE (≤3 dni)",
                        font=("Arial", 16, "bold"),
                        text_color=AppColors.EXPIRING_SOON,
                    ).pack(pady=AppSpacing.SM, anchor="w")

                    for product in alerts["warning"]:
                        product_text = f"• {product['nazwa']} - {product['ilosc']} {product['jednostka']}"
                        if product["days_until_expiry"] is not None:
                            product_text += f" ({product['days_until_expiry']} dni do wygaśnięcia)"
                        ctk.CTkLabel(
                            scrollable, text=product_text, font=("Arial", 12)
                        ).pack(padx=AppSpacing.LG, pady=2, anchor="w")

                if not alerts["expired"] and not alerts["critical"] and not alerts["warning"]:
                    ctk.CTkLabel(
                        scrollable,
                        text="✅ Brak wygasających produktów",
                        font=("Arial", 14),
                        text_color=AppColors.OK,
                    ).pack(pady=AppSpacing.LG)

        except Exception as e:
            ctk.CTkLabel(
                scrollable,
                text=f"Błąd: {str(e)}",
                font=("Arial", 12),
                text_color=AppColors.ERROR,
            ).pack(pady=AppSpacing.LG)

    def refresh_analytics(self):
        """Odświeża widok analityki zakupów"""
        # Odśwież alerty wygasających produktów
        self.refresh_expiry_alerts()

        # Wyczyść poprzednią zawartość
        for widget in self.analytics_scrollable.winfo_children():
            widget.destroy()

        try:
            with PurchaseAnalytics() as analytics:
                # Ogólne statystyki
                stats = analytics.get_total_statistics()

                # Sekcja ogólnych statystyk (card-based)
                stats_frame = ctk.CTkFrame(
                    self.analytics_scrollable,
                    border_width=1,
                    border_color=AppColors.BORDER_DARK
                )
                stats_frame.grid(row=0, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
                stats_frame.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(
                    stats_frame,
                    text=f"{Icons.ANALYTICS} Ogólne Statystyki",
                    font=("Arial", 16, "bold"),
                ).grid(
                    row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w"
                )

                stats_text = f"""
Łączna liczba paragonów: {stats['total_receipts']}
Łączne wydatki: {stats['total_spent']:.2f} PLN
Łączna liczba pozycji: {stats['total_items']}
Średnia wartość paragonu: {stats['avg_receipt']:.2f} PLN
"""
                if stats["oldest_date"]:
                    stats_text += f"Pierwszy paragon: {stats['oldest_date']}\n"
                if stats["newest_date"]:
                    stats_text += f"Ostatni paragon: {stats['newest_date']}\n"

                ctk.CTkLabel(
                    stats_frame,
                    text=stats_text.strip(),
                    font=("Arial", 12),
                    justify="left",
                    anchor="w",
                ).grid(row=1, column=0, padx=AppSpacing.LG, pady=AppSpacing.SM, sticky="w")

                if stats["total_receipts"] == 0:
                    ctk.CTkLabel(
                        self.analytics_scrollable,
                        text="Brak danych do wyświetlenia. Dodaj paragony, aby zobaczyć analitykę.",
                        font=("Arial", 14),
                        text_color="gray",
                    ).grid(row=1, column=0, padx=AppSpacing.LG, pady=AppSpacing.LG)
                    return

                # Separator
                separator1 = ctk.CTkFrame(
                    self.analytics_scrollable,
                    height=1,
                    fg_color=AppColors.BORDER_DARK
                )
                separator1.grid(row=1, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.XS)
                
                # Wydatki według sklepów (card-based)
                stores_frame = ctk.CTkFrame(
                    self.analytics_scrollable,
                    border_width=1,
                    border_color=AppColors.BORDER_DARK
                )
                stores_frame.grid(row=2, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
                stores_frame.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(
                    stores_frame,
                    text=f"{Icons.SHOP} Wydatki według Sklepów",
                    font=("Arial", 16, "bold"),
                ).grid(
                    row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w"
                )

                stores = analytics.get_spending_by_store(limit=5)
                if stores:
                    max_val = max(s[1] for s in stores)
                    for i, store in enumerate(stores):
                        row = ctk.CTkFrame(stores_frame, fg_color="transparent")
                        row.grid(row=i+1, column=0, sticky="ew", padx=AppSpacing.LG, pady=2)
                        row.grid_columnconfigure(0, weight=1)
                        
                        ctk.CTkLabel(row, text=f"{i+1}. {store[0]} ({store[1]:.2f} PLN)", font=("Arial", 12)).pack(anchor="w")
                        
                        progress = ctk.CTkProgressBar(row, height=8, progress_color=AppColors.PRIMARY)
                        progress.pack(fill="x", pady=(0, 5))
                        progress.set(store[1] / max_val if max_val > 0 else 0)
                else:
                    ctk.CTkLabel(stores_frame, text="Brak danych", font=("Arial", 12)).grid(row=1, column=0, padx=AppSpacing.LG, pady=AppSpacing.SM, sticky="w")

                # Separator
                separator2 = ctk.CTkFrame(
                    self.analytics_scrollable,
                    height=1,
                    fg_color=AppColors.BORDER_DARK
                )
                separator2.grid(row=3, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.XS)
                
                # Wydatki według kategorii (card-based)
                categories_frame = ctk.CTkFrame(
                    self.analytics_scrollable,
                    border_width=1,
                    border_color=AppColors.BORDER_DARK
                )
                categories_frame.grid(row=4, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
                categories_frame.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(
                    categories_frame,
                    text=f"{Icons.CATEGORY} Wydatki według Kategorii",
                    font=("Arial", 16, "bold"),
                ).grid(
                    row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w"
                )

                categories = analytics.get_spending_by_category(limit=5)
                if categories:
                    max_val = max(c[1] for c in categories)
                    for i, cat in enumerate(categories):
                        row = ctk.CTkFrame(categories_frame, fg_color="transparent")
                        row.grid(row=i+1, column=0, sticky="ew", padx=AppSpacing.LG, pady=2)
                        row.grid_columnconfigure(0, weight=1)
                        
                        ctk.CTkLabel(row, text=f"{i+1}. {cat[0]} ({cat[1]:.2f} PLN)", font=("Arial", 12)).pack(anchor="w")
                        
                        progress = ctk.CTkProgressBar(row, height=8, progress_color=AppColors.INFO)
                        progress.pack(fill="x", pady=(0, 5))
                        progress.set(cat[1] / max_val if max_val > 0 else 0)
                else:
                    ctk.CTkLabel(categories_frame, text="Brak danych", font=("Arial", 12)).grid(row=1, column=0, padx=AppSpacing.LG, pady=AppSpacing.SM, sticky="w")

                # Separator
                separator3 = ctk.CTkFrame(
                    self.analytics_scrollable,
                    height=1,
                    fg_color=AppColors.BORDER_DARK
                )
                separator3.grid(row=5, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.XS)
                
                # Najczęściej kupowane produkty (card-based)
                products_frame = ctk.CTkFrame(
                    self.analytics_scrollable,
                    border_width=1,
                    border_color=AppColors.BORDER_DARK
                )
                products_frame.grid(row=6, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
                products_frame.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(
                    products_frame,
                    text=f"{Icons.PRODUCT} Najczęściej Kupowane Produkty",
                    font=("Arial", 16, "bold"),
                ).grid(
                    row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w"
                )

                products = analytics.get_top_products(limit=10)
                products_text = "\n".join(
                    [
                        f"{i+1}. {prod[0]} - {prod[1]}x zakupów, {prod[2]:.2f} PLN"
                        for i, prod in enumerate(products)
                    ]
                )

                ctk.CTkLabel(
                    products_frame,
                    text=products_text if products_text else "Brak danych",
                    font=("Arial", 12),
                    justify="left",
                    anchor="w",
                ).grid(row=1, column=0, padx=AppSpacing.LG, pady=AppSpacing.SM, sticky="w")

                # Separator
                separator4 = ctk.CTkFrame(
                    self.analytics_scrollable,
                    height=1,
                    fg_color=AppColors.BORDER_DARK
                )
                separator4.grid(row=7, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.XS)
                
                # Statystyki miesięczne (card-based)
                monthly_frame = ctk.CTkFrame(
                    self.analytics_scrollable,
                    border_width=1,
                    border_color=AppColors.BORDER_DARK
                )
                monthly_frame.grid(row=8, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
                monthly_frame.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(
                    monthly_frame,
                    text=f"{Icons.CALENDAR} Statystyki Miesięczne",
                    font=("Arial", 16, "bold"),
                ).grid(
                    row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w"
                )

                monthly_stats = analytics.get_monthly_statistics()
                if monthly_stats:
                    monthly_text = "\n".join(
                        [
                            f"{stat['month_name']}: {stat['receipts_count']} paragonów, {stat['total_spent']:.2f} PLN"
                            for stat in monthly_stats[:12]  # Ostatnie 12 miesięcy
                        ]
                    )
                else:
                    monthly_text = "Brak danych"

                ctk.CTkLabel(
                    monthly_frame,
                    text=monthly_text,
                    font=("Arial", 12),
                    justify="left",
                    anchor="w",
                ).grid(row=1, column=0, padx=AppSpacing.LG, pady=AppSpacing.SM, sticky="w")

                # Separator
                separator5 = ctk.CTkFrame(
                    self.analytics_scrollable,
                    height=1,
                    fg_color=AppColors.BORDER_DARK
                )
                separator5.grid(row=9, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.XS)
                
                # Ostatnie paragony (card-based)
                # --- Historia Paragonów (Tabela z sortowaniem) ---
                history_frame = ctk.CTkFrame(
                    self.analytics_scrollable,
                    border_width=1,
                    border_color=AppColors.BORDER_DARK
                )
                history_frame.grid(row=10, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
                history_frame.grid_columnconfigure(0, weight=1)

                ctk.CTkLabel(
                    history_frame,
                    text=f"{Icons.RECEIPT} Historia Paragonów",
                    font=("Arial", 16, "bold"),
                ).pack(padx=AppSpacing.SM, pady=AppSpacing.SM, anchor="w")

                # Headers
                h_cols = [
                    ("Data", "date", 120),
                    ("Sklep", "store", 200),
                    ("Suma", "total", 100),
                    ("Pozycje", "items", 80),
                ]
                
                header_row = ctk.CTkFrame(history_frame, fg_color="transparent")
                header_row.pack(fill="x", padx=AppSpacing.SM, pady=(0, 5))
                
                current_sort, is_desc = self.history_sort
                
                for title, key, width in h_cols:
                    marker = ""
                    if current_sort == key:
                        marker = " ▼" if is_desc else " ▲"
                    
                    btn = ctk.CTkButton(
                        header_row,
                        text=f"{title}{marker}",
                        font=("Arial", 12, "bold"),
                        command=lambda k=key: self.toggle_history_sort(k),
                        fg_color="transparent",
                        hover_color=AppColors.BG_DARK,
                        width=width,
                        anchor="w"
                    )
                    btn.pack(side="left", padx=2)

                # Content - używamy get_receipts z sortowaniem
                receipts = analytics.get_receipts(
                    limit=50, 
                    sort_by=current_sort, 
                    sort_desc=is_desc
                )
                
                if not receipts:
                    ctk.CTkLabel(history_frame, text="Brak paragonów", font=("Arial", 12)).pack(pady=10)
                
                for i, r in enumerate(receipts):
                    row = ctk.CTkFrame(
                        history_frame, 
                        fg_color=AppColors.SURFACE_DARK if i % 2 == 0 else "transparent"
                    )
                    row.pack(fill="x", padx=AppSpacing.SM, pady=1)
                    
                    # Data
                    ctk.CTkLabel(row, text=r["date"], width=120, anchor="w").pack(side="left", padx=2)
                    # Sklep
                    ctk.CTkLabel(row, text=r["store"], width=200, anchor="w").pack(side="left", padx=2)
                    # Suma
                    ctk.CTkLabel(row, text=f"{r['total']:.2f} PLN", width=100, anchor="w").pack(side="left", padx=2)
                    # Pozycje
                    ctk.CTkLabel(row, text=f"{r['items_count']} poz.", width=80, anchor="w").pack(side="left", padx=2)

        except Exception as e:
            ctk.CTkLabel(
                self.analytics_scrollable,
                text=f"Błąd podczas ładowania analityki: {str(e)}",
                font=("Arial", 12),
                text_color=AppColors.ERROR,
            ).grid(row=0, column=0, padx=AppSpacing.LG, pady=AppSpacing.LG)

    def refresh_meal_planner(self):
        """Odświeża widok planera posiłków"""
        # Wyczyść poprzednią zawartość
        for widget in self.meal_planner_frame.winfo_children():
            widget.destroy()

        # Header
        header_frame = ctk.CTkFrame(self.meal_planner_frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header_frame,
            text=f"{Icons.MEAL_PLANNER} Tygodniowy Planer Posiłków",
            font=("Arial", 20, "bold"),
        ).grid(row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w")

        buttons_frame = ctk.CTkFrame(header_frame)
        buttons_frame.grid(
            row=0, column=1, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="e"
        )

        btn_generate = ctk.CTkButton(
            buttons_frame,
            text=f"{Icons.REFRESH} Wygeneruj Plan",
            command=self.generate_meal_plan,
            width=150,
            fg_color=AppColors.SUCCESS,
            hover_color=adjust_color(AppColors.SUCCESS, -15),
        )
        btn_generate.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_generate, "Wygeneruj nowy plan posiłków na 7 dni")

        # Scrollable area
        scrollable = ctk.CTkScrollableFrame(self.meal_planner_frame)
        scrollable.grid(row=1, column=0, sticky="nsew", padx=AppSpacing.SM, pady=AppSpacing.SM)
        scrollable.grid_columnconfigure(0, weight=1)

        # Placeholder
        ctk.CTkLabel(
            scrollable,
            text="Kliknij 'Wygeneruj Plan' aby utworzyć plan posiłków na 7 dni",
            font=("Arial", 14),
            text_color="gray",
        ).pack(pady=AppSpacing.XS0)

        self.meal_planner_scrollable = scrollable

    def generate_meal_plan(self):
        """Generuje plan posiłków"""
        # Pokaż progress
        for widget in self.meal_planner_scrollable.winfo_children():
            widget.destroy()

        progress_label = ctk.CTkLabel(
            self.meal_planner_scrollable,
            text="🦅 Bielik generuje plan posiłków...",
            font=("Arial", 14),
        )
        progress_label.pack(pady=AppSpacing.XS0)

        # Generuj w osobnym wątku
        import threading

        thread = threading.Thread(target=self._generate_meal_plan_thread)
        thread.daemon = True
        thread.start()

    def _generate_meal_plan_thread(self):
        """Generuje plan posiłków w osobnym wątku"""
        try:
            with MealPlanner() as planner:
                plan = planner.generate_weekly_plan()

            # Aktualizuj GUI w głównym wątku
            self.after(0, lambda: self._display_meal_plan(plan))

        except Exception as e:
            error_msg = f"Błąd podczas generowania planu: {str(e)}"
            self.after(0, lambda: self._display_meal_plan_error(error_msg))

    def _display_meal_plan(self, plan: Dict):
        """Wyświetla wygenerowany plan posiłków"""
        # Wyczyść
        for widget in self.meal_planner_scrollable.winfo_children():
            widget.destroy()

        plan_data = plan.get("plan", [])

        if not plan_data:
            ctk.CTkLabel(
                self.meal_planner_scrollable,
                text="Nie udało się wygenerować planu",
                font=("Arial", 14),
                text_color=AppColors.ERROR,
            ).pack(pady=AppSpacing.LG)
            return

        # Wyświetl plan dla każdego dnia
        for i, day_plan in enumerate(plan_data):
            day_frame = ctk.CTkFrame(self.meal_planner_scrollable)
            day_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)
            day_frame.grid_columnconfigure(1, weight=1)

            # Nagłówek dnia
            day_name = day_plan.get("dzien_tygodnia", "")
            day_date = day_plan.get("dzien", "")
            header_text = f"{day_name} - {day_date}"

            ctk.CTkLabel(
                day_frame,
                text=header_text,
                font=("Arial", 16, "bold"),
            ).grid(row=0, column=0, columnspan=3, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w")

            # Śniadanie
            self._display_meal(
                day_frame, 1, "🌅 Śniadanie", day_plan.get("sniadanie", {})
            )
            # Obiad
            self._display_meal(day_frame, 2, "🍽️ Obiad", day_plan.get("obiad", {}))
            # Kolacja
            self._display_meal(
                day_frame, 3, "🌙 Kolacja", day_plan.get("kolacja", {})
            )

    def _display_meal(self, parent, row: int, meal_name: str, meal_data: Dict):
        """Wyświetla pojedynczy posiłek"""
        meal_frame = ctk.CTkFrame(parent)
        meal_frame.grid(row=row, column=0, columnspan=3, padx=AppSpacing.SM, pady=AppSpacing.XS, sticky="ew")
        meal_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            meal_frame, text=meal_name, font=("Arial", 14, "bold"), width=120
        ).grid(row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.XS, sticky="w")

        nazwa = meal_data.get("nazwa", "Brak")
        opis = meal_data.get("opis", "")
        czas = meal_data.get("czas", "")
        skladniki = meal_data.get("skladniki", [])

        meal_text = f"{nazwa}"
        if czas:
            meal_text += f" ⏱️ {czas}"
        if opis:
            meal_text += f"\n{opis}"
        if skladniki:
            meal_text += f"\nSkładniki: {', '.join(skladniki)}"

        ctk.CTkLabel(
            meal_frame, text=meal_text, font=("Arial", 12), anchor="w", justify="left"
        ).grid(row=0, column=1, padx=AppSpacing.SM, pady=AppSpacing.XS, sticky="w")

    def _display_meal_plan_error(self, error_msg: str):
        """Wyświetla błąd podczas generowania planu"""
        for widget in self.meal_planner_scrollable.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.meal_planner_scrollable,
            text=error_msg,
            font=("Arial", 14),
            text_color=AppColors.ERROR,
        ).pack(pady=AppSpacing.LG)

    def refresh_history(self):
        """Odświeża listę historii plików w combobox."""
        history = load_history()
        # Konwertuj na krótkie nazwy dla wyświetlenia
        display_values = [os.path.basename(path) for path in history]
        self.history_combo.configure(values=display_values)
        if history:
            self.history_combo.set("Wybierz z historii...")
        else:
            self.history_combo.set("Brak historii")

    def on_history_selected(self, choice):
        """Obsługuje wybór pliku z historii."""
        if choice and choice != "Wybierz z historii..." and choice != "Brak historii":
            history = load_history()
            # Znajdź pełną ścieżkę na podstawie nazwy pliku
            for path in history:
                if os.path.basename(path) == choice:
                    if os.path.exists(path):
                        self.selected_file_path = path
                        self.file_label.configure(text=os.path.basename(path))
                        self.process_button.configure(state="normal")
                        return
            # Jeśli nie znaleziono, odśwież historię
            self.refresh_history()

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Wybierz plik paragonu",
            filetypes=[
                ("Pliki obrazów", "*.png *.jpg *.jpeg"),
                ("Pliki PDF", "*.pdf"),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        if file_path:
            self.selected_file_path = file_path
            self.file_label.configure(text=os.path.basename(file_path))
            self.process_button.configure(state="normal")
            # Dodaj do historii
            add_to_history(file_path)
            self.refresh_history()

    def log(self, message, progress=None, status=None):
        """
        Loguje wiadomość z opcjonalnym postępem i statusem.

        Args:
            message: Wiadomość do wyświetlenia
            progress: Postęp 0-100 (float) lub -1 dla indeterminate, None dla braku zmiany
            status: Tekst statusu do wyświetlenia, None dla braku zmiany
        """
        print(message)  # Print to terminal for debugging
        self.log_queue.put((message, progress, status))

    def prompt_user(self, prompt_text, default_value, raw_name):
        self.prompt_queue.put((prompt_text, default_value, raw_name))
        # Czekaj na wynik z głównego wątku GUI z timeoutem (5 minut)
        try:
            result = self.prompt_result_queue.get(timeout=300)
        except queue.Empty:
            # Timeout - używamy wartości domyślnej
            print(
                f"TIMEOUT: Brak odpowiedzi użytkownika dla '{raw_name}', używam wartości domyślnej: '{default_value}'"
            )
            return default_value
        return result

    def review_user(self, parsed_data):
        self.review_queue.put(parsed_data)
        # Czekaj na wynik z głównego wątku GUI z timeoutem (10 minut)
        try:
            result = self.review_result_queue.get(timeout=600)
        except queue.Empty:
            # Timeout - użytkownik nie odpowiedział, zwracamy None (odrzucamy)
            print(
                "TIMEOUT: Brak odpowiedzi użytkownika na weryfikację paragonu, odrzucam zmiany."
            )
            return None
        return result

    def update_status(self, message, progress=None):
        """
        Aktualizuje status label i pasek postępu.

        Args:
            message: Tekst statusu
            progress: Postęp 0-100 (float) lub -1 dla indeterminate, None dla braku zmiany
        """
        if message:
            self.status_label.configure(text=message)

        if progress is not None:
            if progress == -1:
                # Tryb indeterminate
                self.progress_bar.start()
            else:
                # Tryb determinate
                self.progress_bar.stop()
                self.progress_bar.set(progress / 100.0)

    def process_log_queue(self):
        try:
            # Limit iteracji aby uniknąć memory leak przy szybkim zapełnianiu queue
            max_messages = 50
            processed = 0
            while not self.log_queue.empty() and processed < max_messages:
                item = self.log_queue.get_nowait()
                # Obsługa starego formatu (tylko string) i nowego (tuple)
                if isinstance(item, tuple):
                    message, progress, status = item
                else:
                    message = item
                    progress = None
                    status = None

                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", message + "\n")
                self.log_textbox.configure(state="disabled")
                self.log_textbox.see("end")

                # Aktualizuj status i postęp
                if status is not None or progress is not None:
                    status_text = (
                        status if status is not None else self.status_label.cget("text")
                    )
                    self.update_status(status_text, progress)

                processed += 1

            if not self.prompt_queue.empty():
                prompt_text, default_value, raw_name = self.prompt_queue.get_nowait()
                self.show_prompt_dialog(prompt_text, default_value, raw_name)

            if not self.review_queue.empty():
                parsed_data = self.review_queue.get_nowait()
                self.show_review_dialog(parsed_data)

        finally:
            self.after(100, self.process_log_queue)

    def show_prompt_dialog(self, prompt_text, default_value, raw_name):
        # Sanitize user input to prevent XSS/injection
        from src.security import sanitize_log_message
        sanitized_raw_name = sanitize_log_message(raw_name)
        dialog = ProductMappingDialog(
            self,
            title="Nieznany produkt",
            text=f"Produkt z paragonu: '{sanitized_raw_name}'\n\n{prompt_text}",
            initial_value=default_value,
        )
        user_input = dialog.get_input()
        self.prompt_result_queue.put(user_input if user_input is not None else "")

    def show_review_dialog(self, parsed_data):
        dialog = ReviewDialog(self, parsed_data)
        result_data = dialog.get_result()
        self.review_result_queue.put(result_data)

    def set_ui_state(self, state: str):
        self.process_button.configure(state=state)
        self.file_button.configure(state=state)
        self.init_db_button.configure(state=state)

    def _run_migrations_on_startup(self):
        """Uruchamia migracje bazy danych przy starcie aplikacji (cicho, bez logowania)."""
        try:
            from src.migrate_db import migrate_all
            import os
            
            # Sprawdź czy baza danych istnieje
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, "ReceiptParser", "data", "receipts.db")
            
            if os.path.exists(db_path):
                # Uruchom migracje cicho (bez printów)
                migrate_all()
        except Exception as e:
            # Loguj błąd, ale nie przerywaj startu aplikacji
            logger.error(f"Error running migrations on startup: {e}")

    def initialize_database(self):
        self.log("INFO: Rozpoczynam inicjalizację bazy danych...")
        try:
            init_db()
            # Uruchom migracje po inicjalizacji
            from src.migrate_db import migrate_all

            self.log("INFO: Sprawdzam i aktualizuję schemat bazy danych...")
            migrate_all()
            self.log("INFO: Baza danych została pomyślnie zainicjalizowana!")
        except Exception as e:
            self.log(f"BŁĄD: Nie udało się zainicjalizować bazy danych: {e}")

    def start_processing(self):
        if not self.selected_file_path:
            return

        # Acquire lock to prevent concurrent processing
        if not self.processing_lock.acquire(blocking=False):
            self.notifications.show_warning("Przetwarzanie już trwa. Proszę poczekać na zakończenie.")
            return
        
        try:
            self.is_processing = True
            
            # Dodaj do historii przed przetwarzaniem
            add_to_history(self.selected_file_path)
            self.refresh_history()

            self.set_ui_state("disabled")
            self.process_button.configure(text="⏳ Przetwarzanie...")
            self.update_status("🔄 Inicjalizacja przetwarzania...", -1)  # Indeterminate progress
            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", "end")
            self.log_textbox.configure(state="disabled")

            # Uruchom pasek postępu w trybie indeterminate
            self.update_status("Rozpoczynam przetwarzanie...", progress=-1)

            llm_model = Config.VISION_MODEL

            thread = threading.Thread(
                target=self._run_processing_with_cleanup,
                args=(
                    self.selected_file_path,
                    llm_model,
                ),
            )
            thread.daemon = True
            thread.start()

            self.monitor_thread(thread)
        except Exception as e:
            self.is_processing = False
            self.processing_lock.release()
            logger.error(f"Error starting processing: {e}")
            self.notifications.show_error(f"Nie udało się rozpocząć przetwarzania: {e}")
    
    def _run_processing_with_cleanup(self, file_path, llm_model):
        """Wrapper for processing pipeline that ensures lock is released."""
        try:
            run_processing_pipeline(
                file_path,
                llm_model,
                self.log,
                self.prompt_user,
                self.review_user,
            )
        finally:
            self.is_processing = False
            self.processing_lock.release()
            # Update UI on main thread
            self.after(0, lambda: self.set_ui_state("normal"))

    def monitor_thread(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.monitor_thread(thread))
        else:
            # Lock is released in _run_processing_with_cleanup, but ensure UI is updated
            self.set_ui_state("normal")
            self.process_button.configure(text="🔄 Przetwórz")
            # Zatrzymaj pasek postępu i ustaw na 100%
            self.progress_bar.stop()
            self.progress_bar.set(1.0)
            self.update_status("Gotowy", progress=100)
            self.log("INFO: Przetwarzanie zakończone.")


if __name__ == "__main__":
    app = App()
    
    # Cleanup on exit
    def on_closing():
        """Cleanup on application exit."""
        try:
            cleanup_widget_tree(app)
            dialog_manager.cleanup()
            force_garbage_collection()
            memory_profiler.stop()
        except Exception as e:
            import logging
            logging.warning(f"Error during application cleanup: {e}")
        app.destroy()
    
    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()
