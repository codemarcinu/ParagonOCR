import customtkinter as ctk
from datetime import date
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import sessionmaker

from src.database import engine, StanMagazynowy, Produkt
from src.unified_design_system import AppColors, AppSpacing, adjust_color

class CookingDialog(ctk.CTkToplevel):
    """Okno do zaznaczania produktów do zużycia podczas gotowania"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Gotowanie - Zużycie produktów")
        self.geometry("900x600")
        self.result = None

        SessionLocal = sessionmaker(bind=engine)
        self.session = SessionLocal()

        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)
        ctk.CTkLabel(
            header_frame,
            text="Zaznacz produkty do zużycia:",
            font=("Arial", 16, "bold"),
        ).pack(pady=AppSpacing.SM)

        # Scrollable list of products
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True, padx=AppSpacing.SM, pady=AppSpacing.XS)

        # Headers
        headers = ["Zaznacz", "Produkt", "Ilość", "Jednostka", "Data ważności"]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                self.scrollable_frame, text=text, font=("Arial", 12, "bold")
            ).grid(row=0, column=col, padx=AppSpacing.XS, pady=AppSpacing.XS)

        # Load products from database
        self.checkboxes = []
        self.product_data = []
        self.load_products()

        # Footer
        footer_frame = ctk.CTkFrame(self)
        footer_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)

        ctk.CTkButton(
            footer_frame,
            text="Zużyj zaznaczone",
            command=self.consume_products,
            fg_color=AppColors.SUCCESS,
            hover_color=adjust_color(AppColors.SUCCESS, -15),
            width=200,
        ).pack(side="right", padx=AppSpacing.SM)

        ctk.CTkButton(
            footer_frame, text="Anuluj", command=self.on_cancel, width=200
        ).pack(side="left", padx=AppSpacing.SM)

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        # Użyj after() aby upewnić się, że okno jest widoczne przed grab_set
        self.after(100, self.grab_set)

    def load_products(self):
        """Wczytuje produkty z magazynu"""
        # Pobierz wszystkie produkty ze stanem magazynowym > 0
        stany = (
            self.session.query(StanMagazynowy)
            .join(Produkt)
            .filter(StanMagazynowy.ilosc > 0)
            .order_by(StanMagazynowy.data_waznosci)
            .all()
        )

        if not stany:
            ctk.CTkLabel(
                self.scrollable_frame,
                text="Brak produktów w magazynie",
                font=("Arial", 14),
            ).grid(row=1, column=0, columnspan=5, pady=AppSpacing.LG)
            return

        for i, stan in enumerate(stany):
            row = i + 1
            checkbox = ctk.CTkCheckBox(self.scrollable_frame, text="")
            checkbox.grid(row=row, column=0, padx=AppSpacing.XS, pady=2)

            ctk.CTkLabel(
                self.scrollable_frame, text=stan.produkt.znormalizowana_nazwa, width=300
            ).grid(row=row, column=1, padx=AppSpacing.XS, pady=2, sticky="w")

            ilosc_entry = ctk.CTkEntry(self.scrollable_frame, width=80)
            ilosc_entry.insert(0, str(stan.ilosc))
            ilosc_entry.grid(row=row, column=2, padx=AppSpacing.XS, pady=2)

            ctk.CTkLabel(
                self.scrollable_frame, text=stan.jednostka_miary or "szt", width=80
            ).grid(row=row, column=3, padx=AppSpacing.XS, pady=2)

            data_waz = (
                stan.data_waznosci.strftime("%Y-%m-%d")
                if stan.data_waznosci
                else "Brak"
            )
            color = (
                "red"
                if stan.data_waznosci and stan.data_waznosci < date.today()
                else "green"
            )
            ctk.CTkLabel(
                self.scrollable_frame, text=data_waz, width=120, text_color=color
            ).grid(row=row, column=4, padx=AppSpacing.XS, pady=2)

            self.checkboxes.append(
                {
                    "checkbox": checkbox,
                    "ilosc_entry": ilosc_entry,
                    "stan": stan,
                    "max_ilosc": stan.ilosc,
                }
            )

    def consume_products(self):
        """Zużywa zaznaczone produkty"""
        consumed = []
        try:
            for item in self.checkboxes:
                if item["checkbox"].get():
                    try:
                        ilosc_do_zuzycia = Decimal(
                            item["ilosc_entry"].get().replace(",", ".")
                        )
                        if ilosc_do_zuzycia <= 0:
                            continue
                        if ilosc_do_zuzycia > item["max_ilosc"]:
                            self.session.rollback()
                            if hasattr(self.master, "notifications"):
                                self.master.notifications.show_error(
                                    f"Nie można zużyć więcej niż dostępne {item['max_ilosc']} dla produktu {item['stan'].produkt.znormalizowana_nazwa}"
                                )
                            return

                        # Zmniejsz ilość w magazynie
                        item["stan"].ilosc -= ilosc_do_zuzycia
                        if item["stan"].ilosc <= 0:
                            self.session.delete(item["stan"])

                        consumed.append(
                            {
                                "produkt": item["stan"].produkt.znormalizowana_nazwa,
                                "ilosc": ilosc_do_zuzycia,
                            }
                        )
                    except (ValueError, InvalidOperation):
                        self.session.rollback()
                        if hasattr(self.master, "notifications"):
                            self.master.notifications.show_error(
                                f"Nieprawidłowa ilość dla produktu {item['stan'].produkt.znormalizowana_nazwa}"
                            )
                        return

            if consumed:
                self.session.commit()
                if hasattr(self.master, "notifications"):
                    self.master.notifications.show_success(f"Zużyto {len(consumed)} produktów")
                self.result = consumed
                self.destroy()
            else:
                if hasattr(self.master, "notifications"):
                    self.master.notifications.show_warning("Nie zaznaczono żadnych produktów")
        except Exception as e:
            self.session.rollback()
            if hasattr(self.master, "notifications"):
                self.master.notifications.show_error(f"Nie udało się zużyć produktów: {e}")

    def on_cancel(self):
        self.session.close()
        self.destroy()
