import customtkinter as ctk
from datetime import datetime
from decimal import Decimal

from src.quick_add import QuickAddHelper
from src.unified_design_system import AppColors, AppSpacing, adjust_color
from src.gui_optimizations import ToolTip

class QuickAddDialog(ctk.CTkToplevel):
    """Okno Quick Add - szybkie dodawanie produktu z autocomplete"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚡ Quick Add - Szybkie Dodawanie")
        self.geometry("500x400")
        self.result = None

        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)
        ctk.CTkLabel(
            header_frame,
            text="⚡ Quick Add - Dodaj produkt w 5 sekund",
            font=("Arial", 16, "bold"),
        ).pack(pady=AppSpacing.SM)

        # Form
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="both", expand=True, padx=AppSpacing.LG, pady=AppSpacing.SM)

        # Nazwa produktu z autocomplete
        ctk.CTkLabel(form_frame, text="Nazwa produktu:", font=("Arial", 14)).grid(
            row=0, column=0, sticky="w", pady=AppSpacing.SM
        )
        self.name_entry = ctk.CTkEntry(form_frame, width=300, font=("Arial", 14))
        self.name_entry.grid(row=0, column=1, pady=AppSpacing.SM, padx=AppSpacing.SM, sticky="ew")
        self.name_entry.focus_set()
        form_frame.grid_columnconfigure(1, weight=1)

        # Bind autocomplete
        self.name_entry.bind("<KeyRelease>", self.on_name_changed)
        self.autocomplete_listbox = None

        # Ilość
        ctk.CTkLabel(form_frame, text="Ilość:", font=("Arial", 14)).grid(
            row=1, column=0, sticky="w", pady=AppSpacing.SM
        )
        self.quantity_entry = ctk.CTkEntry(form_frame, width=300)
        self.quantity_entry.insert(0, "1.0")
        self.quantity_entry.grid(row=1, column=1, pady=AppSpacing.SM, padx=AppSpacing.SM, sticky="ew")

        # Jednostka
        ctk.CTkLabel(form_frame, text="Jednostka:", font=("Arial", 14)).grid(
            row=2, column=0, sticky="w", pady=AppSpacing.SM
        )
        self.unit_entry = ctk.CTkEntry(form_frame, width=300)
        self.unit_entry.insert(0, "szt")
        self.unit_entry.grid(row=2, column=1, pady=AppSpacing.SM, padx=AppSpacing.SM, sticky="ew")

        # Data ważności (opcjonalna)
        ctk.CTkLabel(
            form_frame, text="Data ważności (opcjonalna):", font=("Arial", 14)
        ).grid(row=3, column=0, sticky="w", pady=AppSpacing.SM)
        self.expiry_entry = ctk.CTkEntry(
            form_frame, width=300, placeholder_text="YYYY-MM-DD"
        )
        self.expiry_entry.grid(row=3, column=1, pady=AppSpacing.SM, padx=AppSpacing.SM, sticky="ew")

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=AppSpacing.LG, pady=AppSpacing.SM)

        btn_add = ctk.CTkButton(
            button_frame,
            text="⚡ Dodaj (Enter)",
            command=self.quick_add,
            fg_color=AppColors.SUCCESS,
            hover_color=adjust_color(AppColors.SUCCESS, -15),
            width=200,
        )
        btn_add.pack(side="right", padx=AppSpacing.SM)
        ToolTip(btn_add, "Zatwierdź i dodaj produkt")

        btn_cancel = ctk.CTkButton(
            button_frame, text="Anuluj (Esc)", command=self.on_cancel, width=200
        )
        btn_cancel.pack(side="left", padx=AppSpacing.SM)
        ToolTip(btn_cancel, "Anuluj dodawanie")

        self.bind("<Return>", lambda event: self.quick_add())
        self.bind("<Escape>", lambda event: self.on_cancel())
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.after(100, self.grab_set)

    def on_name_changed(self, event=None):
        """Obsługuje zmiany w polu nazwy - pokazuje autocomplete"""
        query = self.name_entry.get().strip()

        # Usuń poprzednią listę autocomplete
        if self.autocomplete_listbox:
            self.autocomplete_listbox.destroy()
            self.autocomplete_listbox = None

        if len(query) < 2:
            return

        # Pobierz sugestie
        try:
            with QuickAddHelper() as helper:
                suggestions = helper.get_autocomplete_suggestions(query, limit=5)

            if suggestions:
                # Utwórz listbox z sugestiami
                self.autocomplete_listbox = ctk.CTkFrame(self)
                self.autocomplete_listbox.place(
                    x=self.name_entry.winfo_x() + 20,
                    y=self.name_entry.winfo_y() + 30,
                    width=300,
                )

                for i, suggestion in enumerate(suggestions):
                    btn = ctk.CTkButton(
                        self.autocomplete_listbox,
                        text=suggestion["nazwa"],
                        command=lambda s=suggestion: self.select_suggestion(s),
                        anchor="w",
                        fg_color="transparent",
                        hover_color=AppColors.PRIMARY,
                    )
                    btn.pack(fill="x", padx=2, pady=1)

        except Exception:
            pass  # Ignoruj błędy autocomplete

    def select_suggestion(self, suggestion):
        """Wybiera sugestię z autocomplete"""
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, suggestion["nazwa"])
        if self.autocomplete_listbox:
            self.autocomplete_listbox.destroy()
            self.autocomplete_listbox = None
        self.quantity_entry.focus_set()

    def quick_add(self):
        """Szybko dodaje produkt"""
        nazwa = self.name_entry.get().strip()
        if not nazwa:
            if hasattr(self.master, "notifications"):
                self.master.notifications.show_error("Nazwa produktu nie może być pusta")
            return

        try:
            ilosc = Decimal(self.quantity_entry.get().replace(",", "."))
            if ilosc <= 0:
                if hasattr(self.master, "notifications"):
                    self.master.notifications.show_error("Ilość musi być większa od zera")
                return
        except ValueError:
            if hasattr(self.master, "notifications"):
                self.master.notifications.show_error("Nieprawidłowa ilość")
            return

        jednostka = self.unit_entry.get().strip() or "szt"

        data_waznosci = None
        expiry_str = self.expiry_entry.get().strip()
        if expiry_str:
            try:
                data_waznosci = datetime.strptime(expiry_str, "%Y-%m-%d")
            except ValueError:
                if hasattr(self.master, "notifications"):
                    self.master.notifications.show_error("Nieprawidłowy format daty. Użyj YYYY-MM-DD")
                return

        try:
            with QuickAddHelper() as helper:
                result = helper.quick_add_product(nazwa, ilosc, jednostka, data_waznosci)
                if hasattr(self.master, "notifications"):
                    self.master.notifications.show_success(
                        f"⚡ Produkt '{result['nazwa']}' dodany w trybie Quick Add!"
                    )
                self.result = result
                self.destroy()
        except Exception as e:
            if hasattr(self.master, "notifications"):
                self.master.notifications.show_error(f"Nie udało się dodać produktu: {str(e)}")

    def on_cancel(self):
        """Anuluje dodawanie"""
        if self.autocomplete_listbox:
            self.autocomplete_listbox.destroy()
        self.destroy()
