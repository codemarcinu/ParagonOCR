import customtkinter as ctk
from datetime import datetime, timedelta, date
from decimal import Decimal
from sqlalchemy.orm import sessionmaker

from src.database import engine, Produkt, StanMagazynowy
from src.unified_design_system import AppColors, AppSpacing, adjust_color
from src.gui_optimizations import ToolTip

class AddProductDialog(ctk.CTkToplevel):
    """Okno do ręcznego dodawania produktów"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Dodaj produkt ręcznie")
        self.geometry("500x400")
        self.result = None

        SessionLocal = sessionmaker(bind=engine)
        self.session = SessionLocal()

        # Form fields
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="both", expand=True, padx=AppSpacing.LG, pady=AppSpacing.LG)

        ctk.CTkLabel(form_frame, text="Nazwa produktu:", font=("Arial", 14)).grid(
            row=0, column=0, sticky="w", pady=AppSpacing.SM
        )
        self.name_entry = ctk.CTkEntry(form_frame, width=300)
        self.name_entry.grid(row=0, column=1, pady=AppSpacing.SM, padx=AppSpacing.SM)

        ctk.CTkLabel(form_frame, text="Ilość:", font=("Arial", 14)).grid(
            row=1, column=0, sticky="w", pady=AppSpacing.SM
        )
        self.quantity_entry = ctk.CTkEntry(form_frame, width=300)
        self.quantity_entry.insert(0, "1.0")
        self.quantity_entry.grid(row=1, column=1, pady=AppSpacing.SM, padx=AppSpacing.SM)

        ctk.CTkLabel(form_frame, text="Jednostka:", font=("Arial", 14)).grid(
            row=2, column=0, sticky="w", pady=AppSpacing.SM
        )
        self.unit_entry = ctk.CTkEntry(form_frame, width=300)
        self.unit_entry.insert(0, "szt")
        self.unit_entry.grid(row=2, column=1, pady=AppSpacing.SM, padx=AppSpacing.SM)

        ctk.CTkLabel(
            form_frame, text="Data ważności (YYYY-MM-DD):", font=("Arial", 14)
        ).grid(row=3, column=0, sticky="w", pady=AppSpacing.SM)
        self.expiry_entry = ctk.CTkEntry(
            form_frame, width=300, placeholder_text="YYYY-MM-DD"
        )
        default_expiry = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        self.expiry_entry.insert(0, default_expiry)
        self.expiry_entry.grid(row=3, column=1, pady=AppSpacing.SM, padx=AppSpacing.SM)

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=AppSpacing.LG, pady=AppSpacing.SM)

        btn_add = ctk.CTkButton(
            button_frame,
            text="Dodaj",
            command=self.add_product,
            fg_color=AppColors.SUCCESS,
            hover_color=adjust_color(AppColors.SUCCESS, -15),
            width=200,
        )
        btn_add.pack(side="right", padx=AppSpacing.SM)
        ToolTip(btn_add, "Zapisz produkt w magazynie")

        btn_cancel = ctk.CTkButton(
            button_frame, text="Anuluj", command=self.on_cancel, width=200
        )
        btn_cancel.pack(side="left", padx=AppSpacing.SM)
        ToolTip(btn_cancel, "Anuluj i zamknij")

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        # Użyj after() aby upewnić się, że okno jest widoczne przed grab_set
        self.after(100, self.grab_set)

    def add_product(self):
        """Dodaje produkt do bazy"""
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

        data_waznosci_str = self.expiry_entry.get().strip()
        data_waznosci = None
        if data_waznosci_str:
            try:
                data_waznosci = datetime.strptime(data_waznosci_str, "%Y-%m-%d").date()
            except ValueError:
                if hasattr(self.master, "notifications"):
                    self.master.notifications.show_error("Nieprawidłowy format daty. Użyj YYYY-MM-DD")
                return

        # Znajdź lub utwórz produkt
        produkt = (
            self.session.query(Produkt).filter_by(znormalizowana_nazwa=nazwa).first()
        )
        if not produkt:
            # Utwórz nowy produkt (bez kategorii na razie)
            produkt = Produkt(znormalizowana_nazwa=nazwa)
            self.session.add(produkt)
            self.session.flush()

        # Dodaj do magazynu
        stan = StanMagazynowy(
            produkt_id=produkt.produkt_id,
            ilosc=ilosc,
            jednostka_miary=jednostka,
            data_waznosci=data_waznosci,
        )
        self.session.add(stan)
        self.session.commit()

        if hasattr(self.master, "notifications"):
            self.master.notifications.show_success(f"Dodano produkt '{nazwa}' do magazynu")
        self.result = True
        self.destroy()

    def on_cancel(self):
        self.session.close()
        self.destroy()
