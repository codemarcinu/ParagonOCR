import customtkinter as ctk
from tkinter import filedialog, messagebox, Toplevel
import threading
import queue
import os
import sys
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import sessionmaker, joinedload

# Lokalne importy - gui.py jest w folderze głównym projektu, src jest w ReceiptParser/src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ReceiptParser'))

from src.main import run_processing_pipeline
from src.database import init_db, engine, Produkt, StanMagazynowy, KategoriaProduktu, AliasProduktu, Paragon
from src.config import Config
from src.normalization_rules import find_static_match
from src.bielik import BielikAssistant
from src.config_prompts import load_prompts, save_prompts, reset_prompts_to_default, DEFAULT_PROMPTS
from src.purchase_analytics import PurchaseAnalytics
from history_manager import load_history, add_to_history


class ToolTip:
    """Prosta implementacja tooltipa dla CustomTkinter."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self):
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        # Użyj standardowego tkinter Label zamiast CTkLabel dla tooltipa
        from tkinter import Label
        label = Label(tw, text=self.text, justify="left",
                     bg="#1a1a1a", fg="white",
                     font=("Arial", 10), padx=5, pady=5)
        label.pack()

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class ProductMappingDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, text, initial_value=""):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x300")
        self.user_input = None

        self.label = ctk.CTkLabel(self, text=text, wraplength=480, font=("Arial", 14))
        self.label.pack(pady=20, padx=20)

        self.entry = ctk.CTkEntry(self, width=400, font=("Arial", 14))
        self.entry.pack(pady=10)
        self.entry.insert(0, initial_value)
        self.entry.focus_set()

        self.ok_button = ctk.CTkButton(
            self, text="Zatwierdź", command=self.on_ok, width=200
        )
        self.ok_button.pack(pady=20)

        self.bind("<Return>", lambda event: self.on_ok())
        self.bind("<Escape>", lambda event: self.on_close())

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        # Użyj after() aby upewnić się, że okno jest widoczne przed grab_set
        self.after(100, self.grab_set)  # Make modal

    def on_ok(self):
        self.user_input = self.entry.get()
        self.destroy()

    def on_close(self):
        self.destroy()

    def get_input(self):
        self.master.wait_window(self)
        return self.user_input


class ReviewDialog(ctk.CTkToplevel):
    def __init__(self, parent, parsed_data):
        super().__init__(parent)
        self.title("Weryfikacja Paragonu")
        self.geometry("1000x700")
        self.parsed_data = parsed_data
        self.result_data = None

        # --- Header ---
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(self.header_frame, text="Sklep:").grid(
            row=0, column=0, padx=5, pady=5
        )
        self.store_entry = ctk.CTkEntry(self.header_frame, width=200)
        self.store_entry.grid(row=0, column=1, padx=5, pady=5)
        self.store_entry.insert(0, parsed_data["sklep_info"]["nazwa"])

        ctk.CTkLabel(self.header_frame, text="Data:").grid(
            row=0, column=2, padx=5, pady=5
        )
        self.date_entry = ctk.CTkEntry(self.header_frame, width=150)
        self.date_entry.grid(row=0, column=3, padx=5, pady=5)
        # Format daty do stringa
        date_val = parsed_data["paragon_info"]["data_zakupu"]
        if isinstance(date_val, datetime):
            date_val = date_val.strftime("%Y-%m-%d")
        self.date_entry.insert(0, str(date_val))

        ctk.CTkLabel(self.header_frame, text="Suma:").grid(
            row=0, column=4, padx=5, pady=5
        )
        self.total_entry = ctk.CTkEntry(self.header_frame, width=100)
        self.total_entry.grid(row=0, column=5, padx=5, pady=5)
        self.total_entry.insert(0, str(parsed_data["paragon_info"]["suma_calkowita"]))

        # --- Body (Items) ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Headers - dodano kolumnę "Znormalizowana nazwa" i "Data ważności"
        headers = ["Nazwa (raw)", "Znormalizowana nazwa", "Ilość", "Cena jedn.", "Wartość", "Rabat", "Po rabacie", "Data ważności"]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                self.scrollable_frame, text=text, font=("Arial", 12, "bold")
            ).grid(row=0, column=col, padx=5, pady=5)

        # Pobierz sugestie znormalizowanych nazw z bazy danych (jeśli dostępna)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        normalized_suggestions = {}
        try:
            for item in parsed_data["pozycje"]:
                nazwa_raw = item.get("nazwa_raw", "").strip()
                # Sprawdź czy istnieje alias w bazie
                alias = session.query(AliasProduktu).options(
                    joinedload(AliasProduktu.produkt)
                ).filter_by(nazwa_z_paragonu=nazwa_raw).first()
                if alias:
                    normalized_suggestions[nazwa_raw] = alias.produkt.znormalizowana_nazwa
                else:
                    # Użyj reguł statycznych
                    suggestion = find_static_match(nazwa_raw)
                    if suggestion:
                        normalized_suggestions[nazwa_raw] = suggestion
        except Exception as e:
            print(f"Błąd podczas pobierania sugestii normalizacji: {e}")
        finally:
            session.close()

        self.item_entries = []
        self.row_frames = []  # Przechowuj ramki wierszy dla kolorowania
        for i, item in enumerate(parsed_data["pozycje"]):
            row = i + 1
            entries = {}
            
            # Sprawdź czy produkt powinien być oznaczony specjalnie
            nazwa_raw = item.get("nazwa_raw", "").strip()
            is_skip = nazwa_raw.upper() == "POMIŃ" or nazwa_raw.upper() == "SKIP"
            is_unknown = not nazwa_raw or len(nazwa_raw) < 2
            
            # Utwórz ramkę dla wiersza (dla kolorowania tła)
            row_frame = ctk.CTkFrame(self.scrollable_frame)
            row_frame.grid(row=row, column=0, columnspan=8, padx=2, pady=2, sticky="ew")
            self.row_frames.append(row_frame)
            
            # Ustaw kolor tła w zależności od typu produktu
            if is_skip:
                row_frame.configure(fg_color="#3d1a1a")  # Ciemnoczerwony dla POMIŃ
                tooltip_text = "Ta pozycja została oznaczona do pominięcia"
            elif is_unknown:
                row_frame.configure(fg_color="#3d3d1a")  # Ciemnożółty dla nieznanych
                tooltip_text = "Nieznany produkt - wymaga weryfikacji"
            else:
                tooltip_text = f"Produkt: {nazwa_raw}"
            
            # Konfiguruj kolumny w ramce
            for col in range(8):
                row_frame.grid_columnconfigure(col, weight=1)

            # Nazwa raw
            e_name = ctk.CTkEntry(row_frame, width=200)
            e_name.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
            e_name.insert(0, nazwa_raw)
            entries["nazwa_raw"] = e_name
            ToolTip(e_name, tooltip_text)

            # Znormalizowana nazwa (sugestia)
            normalized_name = normalized_suggestions.get(nazwa_raw, "")
            e_normalized = ctk.CTkEntry(row_frame, width=200)
            e_normalized.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
            e_normalized.insert(0, normalized_name)
            entries["nazwa_znormalizowana"] = e_normalized
            if normalized_name:
                ToolTip(e_normalized, f"Sugestia znormalizowanej nazwy: {normalized_name}")

            # Ilość
            e_qty = ctk.CTkEntry(row_frame, width=60)
            e_qty.grid(row=0, column=2, padx=2, pady=2, sticky="ew")
            e_qty.insert(0, str(item["ilosc"]))
            entries["ilosc"] = e_qty

            # Cena jedn
            e_unit = ctk.CTkEntry(row_frame, width=80)
            e_unit.grid(row=0, column=3, padx=2, pady=2, sticky="ew")
            e_unit.insert(0, str(item["cena_jedn"]))
            entries["cena_jedn"] = e_unit

            # Cena całk
            e_total = ctk.CTkEntry(row_frame, width=80)
            e_total.grid(row=0, column=4, padx=2, pady=2, sticky="ew")
            e_total.insert(0, str(item["cena_calk"]))
            entries["cena_calk"] = e_total

            # Rabat
            e_disc = ctk.CTkEntry(row_frame, width=80)
            e_disc.grid(row=0, column=5, padx=2, pady=2, sticky="ew")
            val_disc = item.get("rabat", "0.00")
            if val_disc is None:
                val_disc = "0.00"
            e_disc.insert(0, str(val_disc))
            entries["rabat"] = e_disc

            # Po rabacie
            e_final = ctk.CTkEntry(row_frame, width=80)
            e_final.grid(row=0, column=6, padx=2, pady=2, sticky="ew")
            e_final.insert(0, str(item["cena_po_rab"]))
            entries["cena_po_rab"] = e_final

            # Data ważności
            e_expiry = ctk.CTkEntry(row_frame, width=120, placeholder_text="YYYY-MM-DD")
            e_expiry.grid(row=0, column=7, padx=2, pady=2, sticky="ew")
            # Domyślnie ustawiamy datę za 7 dni (można zmienić)
            default_expiry = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            e_expiry.insert(0, default_expiry)
            entries["data_waznosci"] = e_expiry

            # Hidden fields
            entries["jednostka"] = item.get("jednostka", "")

            self.item_entries.append(entries)

        # --- Footer ---
        self.footer_frame = ctk.CTkFrame(self)
        self.footer_frame.pack(fill="x", padx=10, pady=10)

        self.save_btn = ctk.CTkButton(
            self.footer_frame,
            text="Zatwierdź i Zapisz",
            command=self.on_save,
            fg_color="green",
        )
        self.save_btn.pack(side="right", padx=10)

        self.discard_btn = ctk.CTkButton(
            self.footer_frame, text="Odrzuć", command=self.on_discard, fg_color="red"
        )
        self.discard_btn.pack(side="left", padx=10)

        self.protocol("WM_DELETE_WINDOW", self.on_discard)
        # Użyj after() aby upewnić się, że okno jest widoczne przed grab_set
        self.after(100, self.grab_set)

    def on_save(self):
        try:
            # Update parsed_data with values from entries
            self.parsed_data["sklep_info"]["nazwa"] = self.store_entry.get()

            # Date conversion
            raw_date = self.date_entry.get()
            try:
                self.parsed_data["paragon_info"]["data_zakupu"] = datetime.strptime(
                    raw_date, "%Y-%m-%d"
                )
            except ValueError:
                # Fallback if user entered something weird, keep original or now
                pass

            self.parsed_data["paragon_info"]["suma_calkowita"] = Decimal(
                self.total_entry.get().replace(",", ".")
            )

            new_items = []
            for entries in self.item_entries:
                # Parsowanie daty ważności
                data_waznosci_str = entries["data_waznosci"].get().strip()
                data_waznosci = None
                if data_waznosci_str:
                    try:
                        data_waznosci = datetime.strptime(data_waznosci_str, "%Y-%m-%d").date()
                    except ValueError:
                        messagebox.showerror("Błąd", f"Nieprawidłowy format daty ważności: {data_waznosci_str}\nUżyj formatu YYYY-MM-DD")
                        return
                
                item = {
                    "nazwa_raw": entries["nazwa_raw"].get(),
                    "ilosc": Decimal(entries["ilosc"].get().replace(",", ".")),
                    "jednostka": entries["jednostka"],
                    "cena_jedn": Decimal(entries["cena_jedn"].get().replace(",", ".")),
                    "cena_calk": Decimal(entries["cena_calk"].get().replace(",", ".")),
                    "rabat": Decimal(entries["rabat"].get().replace(",", ".")),
                    "cena_po_rab": Decimal(
                        entries["cena_po_rab"].get().replace(",", ".")
                    ),
                    "data_waznosci": data_waznosci,  # Dodano datę ważności
                }
                new_items.append(item)

            self.parsed_data["pozycje"] = new_items
            self.result_data = self.parsed_data
            self.destroy()
        except Exception as e:
            print(f"Error saving review: {e}")
            # Optionally show error dialog

    def on_discard(self):
        self.result_data = None
        self.destroy()

    def get_result(self):
        self.master.wait_window(self)
        return self.result_data


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
        header_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header_frame, text="Zaznacz produkty do zużycia:", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Scrollable list of products
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Headers
        headers = ["Zaznacz", "Produkt", "Ilość", "Jednostka", "Data ważności"]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                self.scrollable_frame, text=text, font=("Arial", 12, "bold")
            ).grid(row=0, column=col, padx=5, pady=5)
        
        # Load products from database
        self.checkboxes = []
        self.product_data = []
        self.load_products()
        
        # Footer
        footer_frame = ctk.CTkFrame(self)
        footer_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            footer_frame,
            text="Zużyj zaznaczone",
            command=self.consume_products,
            fg_color="green",
            width=200
        ).pack(side="right", padx=10)
        
        ctk.CTkButton(
            footer_frame,
            text="Anuluj",
            command=self.on_cancel,
            width=200
        ).pack(side="left", padx=10)
        
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        # Użyj after() aby upewnić się, że okno jest widoczne przed grab_set
        self.after(100, self.grab_set)
    
    def load_products(self):
        """Wczytuje produkty z magazynu"""
        # Pobierz wszystkie produkty ze stanem magazynowym > 0
        stany = self.session.query(StanMagazynowy).join(Produkt).filter(
            StanMagazynowy.ilosc > 0
        ).order_by(StanMagazynowy.data_waznosci).all()
        
        if not stany:
            ctk.CTkLabel(
                self.scrollable_frame,
                text="Brak produktów w magazynie",
                font=("Arial", 14)
            ).grid(row=1, column=0, columnspan=5, pady=20)
            return
        
        for i, stan in enumerate(stany):
            row = i + 1
            checkbox = ctk.CTkCheckBox(self.scrollable_frame, text="")
            checkbox.grid(row=row, column=0, padx=5, pady=2)
            
            ctk.CTkLabel(
                self.scrollable_frame,
                text=stan.produkt.znormalizowana_nazwa,
                width=300
            ).grid(row=row, column=1, padx=5, pady=2, sticky="w")
            
            ilosc_entry = ctk.CTkEntry(self.scrollable_frame, width=80)
            ilosc_entry.insert(0, str(stan.ilosc))
            ilosc_entry.grid(row=row, column=2, padx=5, pady=2)
            
            ctk.CTkLabel(
                self.scrollable_frame,
                text=stan.jednostka_miary or "szt",
                width=80
            ).grid(row=row, column=3, padx=5, pady=2)
            
            data_waz = stan.data_waznosci.strftime("%Y-%m-%d") if stan.data_waznosci else "Brak"
            color = "red" if stan.data_waznosci and stan.data_waznosci < date.today() else "green"
            ctk.CTkLabel(
                self.scrollable_frame,
                text=data_waz,
                width=120,
                text_color=color
            ).grid(row=row, column=4, padx=5, pady=2)
            
            self.checkboxes.append({
                "checkbox": checkbox,
                "ilosc_entry": ilosc_entry,
                "stan": stan,
                "max_ilosc": stan.ilosc
            })
    
    def consume_products(self):
        """Zużywa zaznaczone produkty"""
        consumed = []
        for item in self.checkboxes:
            if item["checkbox"].get():
                try:
                    ilosc_do_zuzycia = Decimal(item["ilosc_entry"].get().replace(",", "."))
                    if ilosc_do_zuzycia <= 0:
                        continue
                    if ilosc_do_zuzycia > item["max_ilosc"]:
                        messagebox.showerror(
                            "Błąd",
                            f"Nie można zużyć więcej niż dostępne {item['max_ilosc']} dla produktu {item['stan'].produkt.znormalizowana_nazwa}"
                        )
                        return
                    
                    # Zmniejsz ilość w magazynie
                    item["stan"].ilosc -= ilosc_do_zuzycia
                    if item["stan"].ilosc <= 0:
                        self.session.delete(item["stan"])
                    
                    consumed.append({
                        "produkt": item["stan"].produkt.znormalizowana_nazwa,
                        "ilosc": ilosc_do_zuzycia
                    })
                except ValueError:
                    messagebox.showerror("Błąd", f"Nieprawidłowa ilość dla produktu {item['stan'].produkt.znormalizowana_nazwa}")
                    return
        
        if consumed:
            self.session.commit()
            messagebox.showinfo("Sukces", f"Zużyto {len(consumed)} produktów")
            self.result = consumed
            self.destroy()
        else:
            messagebox.showwarning("Uwaga", "Nie zaznaczono żadnych produktów")
    
    def on_cancel(self):
        self.session.close()
        self.destroy()


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
        form_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(form_frame, text="Nazwa produktu:", font=("Arial", 14)).grid(row=0, column=0, sticky="w", pady=10)
        self.name_entry = ctk.CTkEntry(form_frame, width=300)
        self.name_entry.grid(row=0, column=1, pady=10, padx=10)
        
        ctk.CTkLabel(form_frame, text="Ilość:", font=("Arial", 14)).grid(row=1, column=0, sticky="w", pady=10)
        self.quantity_entry = ctk.CTkEntry(form_frame, width=300)
        self.quantity_entry.insert(0, "1.0")
        self.quantity_entry.grid(row=1, column=1, pady=10, padx=10)
        
        ctk.CTkLabel(form_frame, text="Jednostka:", font=("Arial", 14)).grid(row=2, column=0, sticky="w", pady=10)
        self.unit_entry = ctk.CTkEntry(form_frame, width=300)
        self.unit_entry.insert(0, "szt")
        self.unit_entry.grid(row=2, column=1, pady=10, padx=10)
        
        ctk.CTkLabel(form_frame, text="Data ważności (YYYY-MM-DD):", font=("Arial", 14)).grid(row=3, column=0, sticky="w", pady=10)
        self.expiry_entry = ctk.CTkEntry(form_frame, width=300, placeholder_text="YYYY-MM-DD")
        default_expiry = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        self.expiry_entry.insert(0, default_expiry)
        self.expiry_entry.grid(row=3, column=1, pady=10, padx=10)
        
        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="Dodaj",
            command=self.add_product,
            fg_color="green",
            width=200
        ).pack(side="right", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="Anuluj",
            command=self.on_cancel,
            width=200
        ).pack(side="left", padx=10)
        
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        # Użyj after() aby upewnić się, że okno jest widoczne przed grab_set
        self.after(100, self.grab_set)
    
    def add_product(self):
        """Dodaje produkt do bazy"""
        nazwa = self.name_entry.get().strip()
        if not nazwa:
            messagebox.showerror("Błąd", "Nazwa produktu nie może być pusta")
            return
        
        try:
            ilosc = Decimal(self.quantity_entry.get().replace(",", "."))
            if ilosc <= 0:
                messagebox.showerror("Błąd", "Ilość musi być większa od zera")
                return
        except ValueError:
            messagebox.showerror("Błąd", "Nieprawidłowa ilość")
            return
        
        jednostka = self.unit_entry.get().strip() or "szt"
        
        data_waznosci_str = self.expiry_entry.get().strip()
        data_waznosci = None
        if data_waznosci_str:
            try:
                data_waznosci = datetime.strptime(data_waznosci_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowy format daty. Użyj YYYY-MM-DD")
                return
        
        # Znajdź lub utwórz produkt
        produkt = self.session.query(Produkt).filter_by(znormalizowana_nazwa=nazwa).first()
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
            data_waznosci=data_waznosci
        )
        self.session.add(stan)
        self.session.commit()
        
        messagebox.showinfo("Sukces", f"Dodano produkt '{nazwa}' do magazynu")
        self.result = True
        self.destroy()
    
    def on_cancel(self):
        self.session.close()
        self.destroy()


class BielikChatDialog(ctk.CTkToplevel):
    """Okno czatu z asystentem Bielik"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🦅 Bielik - Asystent Kulinarny")
        self.geometry("800x600")
        self.assistant = None
        
        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(
            header_frame, 
            text="🦅 Bielik - Asystent Kulinarny", 
            font=("Arial", 18, "bold")
        ).pack(pady=10)
        
        # Chat area (scrollable)
        self.chat_frame = ctk.CTkScrollableFrame(self)
        self.chat_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Input area
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=10, pady=10)
        
        self.input_entry = ctk.CTkEntry(
            input_frame, 
            placeholder_text="Zadaj pytanie Bielikowi...",
            font=("Arial", 14)
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.input_entry.bind("<Return>", lambda e: self.send_message())
        
        self.send_button = ctk.CTkButton(
            input_frame,
            text="Wyślij",
            command=self.send_message,
            width=100
        )
        self.send_button.pack(side="right", padx=5)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self, 
            text="Gotowy", 
            font=("Arial", 10)
        )
        self.status_label.pack(pady=5)
        
        # Inicjalizuj asystenta
        self.init_assistant()
        
        # Dodaj powitanie
        self.add_message("Bielik", "Cześć! Jestem Bielik, twój asystent kulinarny. Jak mogę Ci pomóc?")
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def init_assistant(self):
        """Inicjalizuje asystenta Bielik"""
        try:
            self.assistant = BielikAssistant()
            self.status_label.configure(text="Gotowy", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"Błąd: {e}", text_color="red")
            messagebox.showerror("Błąd", f"Nie udało się połączyć z bazą danych: {e}")
    
    def add_message(self, sender: str, message: str):
        """Dodaje wiadomość do czatu"""
        # Ramka dla wiadomości
        msg_frame = ctk.CTkFrame(self.chat_frame)
        msg_frame.pack(fill="x", padx=5, pady=5)
        
        # Kolor w zależności od nadawcy
        if sender == "Bielik":
            msg_frame.configure(fg_color="#1f538d")
            sender_text = "🦅 Bielik:"
        else:
            msg_frame.configure(fg_color="#2b2b2b")
            sender_text = "Ty:"
        
        # Label z wiadomością
        msg_label = ctk.CTkLabel(
            msg_frame,
            text=f"{sender_text} {message}",
            font=("Arial", 12),
            wraplength=700,
            justify="left",
            anchor="w"
        )
        msg_label.pack(fill="x", padx=10, pady=5)
        
        # Przewiń do dołu
        self.chat_frame.update()
        self.chat_frame._parent_canvas.yview_moveto(1.0)
    
    def send_message(self):
        """Wysyła wiadomość do Bielika"""
        question = self.input_entry.get().strip()
        if not question:
            return
        
        # Wyczyść pole wejściowe
        self.input_entry.delete(0, "end")
        
        # Dodaj wiadomość użytkownika
        self.add_message("User", question)
        
        # Wyłącz przycisk podczas przetwarzania
        self.send_button.configure(state="disabled")
        self.status_label.configure(text="Bielik myśli...", text_color="orange")
        
        # Uruchom w osobnym wątku, żeby nie blokować GUI
        import threading
        thread = threading.Thread(target=self.process_question, args=(question,))
        thread.daemon = True
        thread.start()
    
    def process_question(self, question: str):
        """Przetwarza pytanie w osobnym wątku"""
        try:
            if not self.assistant:
                self.init_assistant()
            
            answer = self.assistant.answer_question(question)
            
            # Aktualizuj GUI w głównym wątku
            self.after(0, lambda: self.add_message("Bielik", answer))
            self.after(0, lambda: self.status_label.configure(text="Gotowy", text_color="green"))
            self.after(0, lambda: self.send_button.configure(state="normal"))
        except Exception as e:
            error_msg = f"Przepraszam, wystąpił błąd: {str(e)}"
            self.after(0, lambda: self.add_message("Bielik", error_msg))
            self.after(0, lambda: self.status_label.configure(text="Błąd", text_color="red"))
            self.after(0, lambda: self.send_button.configure(state="normal"))
    
    def on_close(self):
        """Zamyka okno i zwalnia zasoby"""
        if self.assistant:
            self.assistant.close()
        self.destroy()


class SettingsDialog(ctk.CTkToplevel):
    """Okno ustawień - edycja promptów systemowych"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚙️ Ustawienia - Prompty Systemowe")
        self.geometry("900x700")
        
        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(
            header_frame,
            text="⚙️ Ustawienia Promptów Systemowych Bielika",
            font=("Arial", 18, "bold")
        ).pack(pady=10)
        
        # Scrollable frame dla promptów
        scrollable = ctk.CTkScrollableFrame(self)
        scrollable.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Wczytaj prompty
        self.prompts = load_prompts()
        self.text_boxes = {}
        
        # Opisy promptów
        prompt_descriptions = {
            "answer_question": "Prompt dla odpowiadania na pytania użytkownika",
            "suggest_dishes": "Prompt dla proponowania potraw",
            "shopping_list": "Prompt dla generowania list zakupów"
        }
        
        # Utwórz pola tekstowe dla każdego promptu
        for i, (key, value) in enumerate(self.prompts.items()):
            # Label z opisem
            label = ctk.CTkLabel(
                scrollable,
                text=prompt_descriptions.get(key, key),
                font=("Arial", 14, "bold")
            )
            label.grid(row=i*2, column=0, sticky="w", padx=10, pady=(10, 5))
            
            # Textbox dla promptu
            textbox = ctk.CTkTextbox(
                scrollable,
                height=150,
                font=("Arial", 11)
            )
            textbox.insert("1.0", value)
            textbox.grid(row=i*2+1, column=0, sticky="ew", padx=10, pady=5)
            scrollable.grid_columnconfigure(0, weight=1)
            
            self.text_boxes[key] = textbox
        
        # Footer z przyciskami
        footer_frame = ctk.CTkFrame(self)
        footer_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            footer_frame,
            text="💾 Zapisz",
            command=self.save_prompts,
            fg_color="green",
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            footer_frame,
            text="🔄 Resetuj do domyślnych",
            command=self.reset_prompts,
            fg_color="orange",
            width=200
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            footer_frame,
            text="❌ Anuluj",
            command=self.destroy,
            fg_color="red",
            width=150
        ).pack(side="right", padx=5)
        
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(100, self.grab_set)
    
    def save_prompts(self):
        """Zapisuje prompty do pliku"""
        try:
            new_prompts = {}
            for key, textbox in self.text_boxes.items():
                new_prompts[key] = textbox.get("1.0", "end-1c").strip()
            
            if save_prompts(new_prompts):
                messagebox.showinfo("Sukces", "Prompty zostały zapisane!")
                self.destroy()
            else:
                messagebox.showerror("Błąd", "Nie udało się zapisać promptów.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Wystąpił błąd podczas zapisywania: {e}")
    
    def reset_prompts(self):
        """Resetuje prompty do wartości domyślnych"""
        if messagebox.askyesno(
            "Potwierdzenie",
            "Czy na pewno chcesz zresetować wszystkie prompty do wartości domyślnych?"
        ):
            try:
                reset_prompts_to_default()
                # Odśwież okno
                self.destroy()
                # Otwórz ponownie
                SettingsDialog(self.master)
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się zresetować promptów: {e}")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ReceiptParser - System Zarządzania Paragonami")
        self.geometry("1000x700")
        ctk.set_appearance_mode("System")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- MENU BAR ---
        self.menu_frame = ctk.CTkFrame(self)
        self.menu_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.menu_frame.grid_columnconfigure(0, weight=1)
        
        # Menu buttons
        menu_buttons_frame = ctk.CTkFrame(self.menu_frame)
        menu_buttons_frame.pack(side="left", padx=5, pady=5)
        
        ctk.CTkButton(
            menu_buttons_frame,
            text="📄 Paragony",
            command=self.show_receipts_tab,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            menu_buttons_frame,
            text="🍳 Gotowanie",
            command=self.show_cooking_dialog,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            menu_buttons_frame,
            text="➕ Dodaj produkt",
            command=self.show_add_product_dialog,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            menu_buttons_frame,
            text="📦 Magazyn",
            command=self.show_inventory,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            menu_buttons_frame,
            text="🦅 Bielik",
            command=self.show_bielik_chat,
            width=120
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            menu_buttons_frame,
            text="⚙️ Ustawienia",
            command=self.show_settings,
            width=120
        ).pack(side="left", padx=5)

        # --- MAIN CONTENT AREA ---
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # --- WIDGETY DLA PARAGONÓW (ANALITYKA) ---
        self.receipts_frame = ctk.CTkFrame(self.content_frame)
        self.receipts_frame.grid(row=0, column=0, sticky="nsew")
        self.receipts_frame.grid_columnconfigure(0, weight=1)
        self.receipts_frame.grid_rowconfigure(1, weight=1)
        
        # Header z przyciskami
        header_frame = ctk.CTkFrame(self.receipts_frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            header_frame,
            text="📊 Analityka Zakupów",
            font=("Arial", 20, "bold")
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        buttons_frame = ctk.CTkFrame(header_frame)
        buttons_frame.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        ctk.CTkButton(
            buttons_frame,
            text="📁 Dodaj paragon",
            command=self.show_add_receipt_dialog,
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            buttons_frame,
            text="🔄 Odśwież",
            command=self.refresh_analytics,
            width=100
        ).pack(side="left", padx=5)
        
        # Scrollable area dla analityki
        self.analytics_scrollable = ctk.CTkScrollableFrame(self.receipts_frame)
        self.analytics_scrollable.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.analytics_scrollable.grid_columnconfigure(0, weight=1)
        
        # Stary widok przetwarzania (ukryty, dostępny przez dialog)
        self.processing_frame = ctk.CTkFrame(self.content_frame)
        self.processing_frame.grid(row=0, column=0, sticky="nsew")
        self.processing_frame.grid_columnconfigure(0, weight=1)
        self.processing_frame.grid_rowconfigure(5, weight=1)
        
        # Historia plików
        history_frame = ctk.CTkFrame(self.processing_frame)
        history_frame.grid(row=0, column=0, columnspan=4, padx=10, pady=(10, 5), sticky="ew")
        history_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(history_frame, text="Ostatnie pliki:", font=("Arial", 12)).grid(row=0, column=0, padx=5, pady=5)
        
        self.history_combo = ctk.CTkComboBox(
            history_frame,
            values=[],
            command=self.on_history_selected,
            width=400
        )
        self.history_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.history_combo.set("Wybierz z historii...")
        
        # Wczytaj historię plików (po utworzeniu history_combo)
        self.refresh_history()
        
        self.file_button = ctk.CTkButton(
            history_frame, text="📁 Wybierz plik", command=self.select_file, width=150
        )
        self.file_button.grid(row=0, column=2, padx=5, pady=5)

        self.file_label = ctk.CTkLabel(
            self.processing_frame, text="Nie wybrano pliku", anchor="w"
        )
        self.file_label.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="ew")

        buttons_frame2 = ctk.CTkFrame(self.processing_frame)
        buttons_frame2.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        
        self.process_button = ctk.CTkButton(
            buttons_frame2,
            text="🔄 Przetwórz",
            command=self.start_processing,
            state="disabled",
        )
        self.process_button.pack(side="left", padx=5)

        self.init_db_button = ctk.CTkButton(
            buttons_frame2,
            text="⚙️ Inicjalizuj bazę danych",
            command=self.initialize_database,
        )
        self.init_db_button.pack(side="left", padx=5)

        # Status label i progress bar
        self.status_label = ctk.CTkLabel(
            self.processing_frame, text="Gotowy", anchor="w", font=("Arial", 12)
        )
        self.status_label.grid(row=3, column=0, columnspan=4, padx=10, pady=(10, 5), sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self.processing_frame)
        self.progress_bar.grid(row=4, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.log_textbox = ctk.CTkTextbox(self.processing_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=5, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")
        
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
        
        # Show receipts tab by default
        self.show_receipts_tab()

    def show_receipts_tab(self):
        """Pokazuje zakładkę paragonów z analityką"""
        # Ukryj wszystkie inne widoki
        for widget in self.content_frame.winfo_children():
            widget.grid_remove()
        
        # Pokaż widok analityki
        self.receipts_frame.grid(row=0, column=0, sticky="nsew")
        self.refresh_analytics()
    
    def show_cooking_dialog(self):
        """Otwiera okno gotowania"""
        dialog = CookingDialog(self)
        dialog.wait_window()
    
    def show_add_product_dialog(self):
        """Otwiera okno dodawania produktu"""
        dialog = AddProductDialog(self)
        dialog.wait_window()
        if dialog.result:
            self.log("INFO: Produkt został dodany do magazynu")
    
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
        action_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(
            action_frame,
            text="💾 Zapisz zmiany",
            command=lambda: self.save_inventory_changes(inv_window, session, inventory_items),
            fg_color="green",
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            action_frame,
            text="🔄 Odśwież",
            command=lambda: self.refresh_inventory_window(inv_window, session),
            width=150
        ).pack(side="left", padx=5)
        
        scrollable = ctk.CTkScrollableFrame(inv_window)
        scrollable.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Headers - dodano kolumnę "Zamrożone" i "Akcje"
        headers = ["Produkt", "Ilość", "Jednostka", "Data ważności", "Zamrożone", "Status", "Akcje"]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                scrollable, text=text, font=("Arial", 12, "bold")
            ).grid(row=0, column=col, padx=5, pady=5)
        
        stany = session.query(StanMagazynowy).join(Produkt).filter(
            StanMagazynowy.ilosc > 0
        ).order_by(StanMagazynowy.data_waznosci).all()
        
        inventory_items = []
        
        for i, stan in enumerate(stany):
            row = i + 1
            
            # Produkt (tylko do odczytu)
            ctk.CTkLabel(
                scrollable,
                text=stan.produkt.znormalizowana_nazwa,
                width=250
            ).grid(row=row, column=0, padx=5, pady=2, sticky="w")
            
            # Ilość (edytowalna)
            ilosc_entry = ctk.CTkEntry(scrollable, width=100)
            ilosc_entry.insert(0, str(stan.ilosc))
            ilosc_entry.grid(row=row, column=1, padx=5, pady=2)
            
            # Jednostka (edytowalna)
            jednostka_entry = ctk.CTkEntry(scrollable, width=100)
            jednostka_entry.insert(0, stan.jednostka_miary or "szt")
            jednostka_entry.grid(row=row, column=2, padx=5, pady=2)
            
            # Data ważności (edytowalna)
            data_entry = ctk.CTkEntry(scrollable, width=120, placeholder_text="YYYY-MM-DD")
            if stan.data_waznosci:
                data_entry.insert(0, stan.data_waznosci.strftime("%Y-%m-%d"))
            data_entry.grid(row=row, column=3, padx=5, pady=2)
            
            # Checkbox "Zamrożone"
            zamrozone_checkbox = ctk.CTkCheckBox(scrollable, text="")
            zamrozone_checkbox.grid(row=row, column=4, padx=5, pady=2)
            # Ustaw stan checkboxa na podstawie wartości z bazy (domyślnie False jeśli None)
            zamrozone_checkbox.select() if getattr(stan, 'zamrozone', False) else zamrozone_checkbox.deselect()
            
            # Status (tylko do odczytu)
            if stan.data_waznosci:
                if stan.data_waznosci < date.today():
                    status = "⚠️ Przeterminowany"
                    color = "red"
                elif stan.data_waznosci <= date.today() + timedelta(days=3):
                    status = "🔴 Wkrótce przeterminowany"
                    color = "orange"
                else:
                    status = "✅ OK"
                    color = "green"
            else:
                status = "❓ Brak daty"
                color = "gray"
            
            status_label = ctk.CTkLabel(
                scrollable,
                text=status,
                width=150,
                text_color=color
            )
            status_label.grid(row=row, column=5, padx=5, pady=2)
            
            # Przycisk usuwania
            delete_btn = ctk.CTkButton(
                scrollable,
                text="🗑️ Usuń",
                command=lambda s=stan: self.delete_inventory_item(inv_window, session, s),
                fg_color="red",
                width=80,
                height=25
            )
            delete_btn.grid(row=row, column=6, padx=5, pady=2)
            
            inventory_items.append({
                "stan": stan,
                "ilosc_entry": ilosc_entry,
                "jednostka_entry": jednostka_entry,
                "data_entry": data_entry,
                "zamrozone_checkbox": zamrozone_checkbox,
                "status_label": status_label
            })
        
        if not stany:
            ctk.CTkLabel(
                scrollable,
                text="Brak produktów w magazynie",
                font=("Arial", 14)
            ).grid(row=1, column=0, columnspan=7, pady=20)
        
        # Przechowaj referencje w oknie
        inv_window.inventory_items = inventory_items
        inv_window.session = session
        
        inv_window.protocol("WM_DELETE_WINDOW", lambda: self.close_inventory_window(inv_window, session))
    
    def save_inventory_changes(self, inv_window, session, inventory_items):
        """Zapisuje zmiany w magazynie"""
        try:
            for item in inventory_items:
                stan = item["stan"]
                
                # Aktualizuj ilość
                try:
                    nowa_ilosc = Decimal(item["ilosc_entry"].get().replace(",", "."))
                    if nowa_ilosc < 0:
                        messagebox.showerror("Błąd", f"Ilość nie może być ujemna dla produktu {stan.produkt.znormalizowana_nazwa}")
                        return
                    if nowa_ilosc == 0:
                        # Usuń produkt z magazynu jeśli ilość = 0
                        session.delete(stan)
                        continue
                    stan.ilosc = nowa_ilosc
                except ValueError:
                    messagebox.showerror("Błąd", f"Nieprawidłowa ilość dla produktu {stan.produkt.znormalizowana_nazwa}")
                    return
                
                # Aktualizuj jednostkę
                stan.jednostka_miary = item["jednostka_entry"].get().strip() or None
                
                # Aktualizuj datę ważności
                data_str = item["data_entry"].get().strip()
                if data_str:
                    try:
                        stan.data_waznosci = datetime.strptime(data_str, "%Y-%m-%d").date()
                    except ValueError:
                        messagebox.showerror("Błąd", f"Nieprawidłowy format daty dla produktu {stan.produkt.znormalizowana_nazwa}\nUżyj formatu YYYY-MM-DD")
                        return
                else:
                    stan.data_waznosci = None
                
                # Aktualizuj stan zamrożenia
                stan.zamrozone = item["zamrozone_checkbox"].get()
            
            session.commit()
            messagebox.showinfo("Sukces", "Zmiany zostały zapisane!")
            # Odśwież okno
            self.refresh_inventory_window(inv_window, session)
        except Exception as e:
            session.rollback()
            messagebox.showerror("Błąd", f"Nie udało się zapisać zmian: {e}")
    
    def delete_inventory_item(self, inv_window, session, stan):
        """Usuwa produkt z magazynu"""
        if messagebox.askyesno("Potwierdzenie", f"Czy na pewno chcesz usunąć {stan.produkt.znormalizowana_nazwa} z magazynu?"):
            try:
                session.delete(stan)
                session.commit()
                messagebox.showinfo("Sukces", "Produkt został usunięty z magazynu")
                # Odśwież okno
                self.refresh_inventory_window(inv_window, session)
            except Exception as e:
                session.rollback()
                messagebox.showerror("Błąd", f"Nie udało się usunąć produktu: {e}")
    
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
        dialog = BielikChatDialog(self)
        dialog.wait_window()
    
    def show_settings(self):
        """Otwiera okno ustawień"""
        dialog = SettingsDialog(self)
        dialog.wait_window()
    
    def show_add_receipt_dialog(self):
        """Otwiera widok do dodawania paragonu"""
        # Ukryj analitykę i pokaż widok przetwarzania
        self.receipts_frame.grid_remove()
        self.processing_frame.grid(row=0, column=0, sticky="nsew")
    
    def refresh_analytics(self):
        """Odświeża widok analityki zakupów"""
        # Wyczyść poprzednią zawartość
        for widget in self.analytics_scrollable.winfo_children():
            widget.destroy()
        
        try:
            with PurchaseAnalytics() as analytics:
                # Ogólne statystyki
                stats = analytics.get_total_statistics()
                
                # Sekcja ogólnych statystyk
                stats_frame = ctk.CTkFrame(self.analytics_scrollable)
                stats_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
                stats_frame.grid_columnconfigure(0, weight=1)
                
                ctk.CTkLabel(
                    stats_frame,
                    text="📊 Ogólne Statystyki",
                    font=("Arial", 16, "bold")
                ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
                
                stats_text = f"""
Łączna liczba paragonów: {stats['total_receipts']}
Łączne wydatki: {stats['total_spent']:.2f} PLN
Łączna liczba pozycji: {stats['total_items']}
Średnia wartość paragonu: {stats['avg_receipt']:.2f} PLN
"""
                if stats['oldest_date']:
                    stats_text += f"Pierwszy paragon: {stats['oldest_date']}\n"
                if stats['newest_date']:
                    stats_text += f"Ostatni paragon: {stats['newest_date']}\n"
                
                ctk.CTkLabel(
                    stats_frame,
                    text=stats_text.strip(),
                    font=("Arial", 12),
                    justify="left",
                    anchor="w"
                ).grid(row=1, column=0, padx=20, pady=10, sticky="w")
                
                if stats['total_receipts'] == 0:
                    ctk.CTkLabel(
                        self.analytics_scrollable,
                        text="Brak danych do wyświetlenia. Dodaj paragony, aby zobaczyć analitykę.",
                        font=("Arial", 14),
                        text_color="gray"
                    ).grid(row=1, column=0, padx=20, pady=20)
                    return
                
                # Wydatki według sklepów
                stores_frame = ctk.CTkFrame(self.analytics_scrollable)
                stores_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
                stores_frame.grid_columnconfigure(0, weight=1)
                
                ctk.CTkLabel(
                    stores_frame,
                    text="🏪 Wydatki według Sklepów",
                    font=("Arial", 16, "bold")
                ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
                
                stores = analytics.get_spending_by_store(limit=10)
                stores_text = "\n".join([
                    f"{i+1}. {store[0]}: {store[1]:.2f} PLN"
                    for i, store in enumerate(stores)
                ])
                
                ctk.CTkLabel(
                    stores_frame,
                    text=stores_text if stores_text else "Brak danych",
                    font=("Arial", 12),
                    justify="left",
                    anchor="w"
                ).grid(row=1, column=0, padx=20, pady=10, sticky="w")
                
                # Wydatki według kategorii
                categories_frame = ctk.CTkFrame(self.analytics_scrollable)
                categories_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
                categories_frame.grid_columnconfigure(0, weight=1)
                
                ctk.CTkLabel(
                    categories_frame,
                    text="📦 Wydatki według Kategorii",
                    font=("Arial", 16, "bold")
                ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
                
                categories = analytics.get_spending_by_category(limit=10)
                categories_text = "\n".join([
                    f"{i+1}. {cat[0]}: {cat[1]:.2f} PLN"
                    for i, cat in enumerate(categories)
                ])
                
                ctk.CTkLabel(
                    categories_frame,
                    text=categories_text if categories_text else "Brak danych",
                    font=("Arial", 12),
                    justify="left",
                    anchor="w"
                ).grid(row=1, column=0, padx=20, pady=10, sticky="w")
                
                # Najczęściej kupowane produkty
                products_frame = ctk.CTkFrame(self.analytics_scrollable)
                products_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
                products_frame.grid_columnconfigure(0, weight=1)
                
                ctk.CTkLabel(
                    products_frame,
                    text="🛒 Najczęściej Kupowane Produkty",
                    font=("Arial", 16, "bold")
                ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
                
                products = analytics.get_top_products(limit=10)
                products_text = "\n".join([
                    f"{i+1}. {prod[0]} - {prod[1]}x zakupów, {prod[2]:.2f} PLN"
                    for i, prod in enumerate(products)
                ])
                
                ctk.CTkLabel(
                    products_frame,
                    text=products_text if products_text else "Brak danych",
                    font=("Arial", 12),
                    justify="left",
                    anchor="w"
                ).grid(row=1, column=0, padx=20, pady=10, sticky="w")
                
                # Statystyki miesięczne
                monthly_frame = ctk.CTkFrame(self.analytics_scrollable)
                monthly_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
                monthly_frame.grid_columnconfigure(0, weight=1)
                
                ctk.CTkLabel(
                    monthly_frame,
                    text="📅 Statystyki Miesięczne",
                    font=("Arial", 16, "bold")
                ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
                
                monthly_stats = analytics.get_monthly_statistics()
                if monthly_stats:
                    monthly_text = "\n".join([
                        f"{stat['month_name']}: {stat['receipts_count']} paragonów, {stat['total_spent']:.2f} PLN"
                        for stat in monthly_stats[:12]  # Ostatnie 12 miesięcy
                    ])
                else:
                    monthly_text = "Brak danych"
                
                ctk.CTkLabel(
                    monthly_frame,
                    text=monthly_text,
                    font=("Arial", 12),
                    justify="left",
                    anchor="w"
                ).grid(row=1, column=0, padx=20, pady=10, sticky="w")
                
                # Ostatnie paragony
                recent_frame = ctk.CTkFrame(self.analytics_scrollable)
                recent_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=10)
                recent_frame.grid_columnconfigure(0, weight=1)
                
                ctk.CTkLabel(
                    recent_frame,
                    text="📄 Ostatnie Paragony",
                    font=("Arial", 16, "bold")
                ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
                
                recent = analytics.get_recent_receipts(limit=10)
                if recent:
                    recent_text = "\n".join([
                        f"{i+1}. {rec['date']} - {rec['store']}: {rec['total']:.2f} PLN ({rec['items_count']} pozycji)"
                        for i, rec in enumerate(recent)
                    ])
                else:
                    recent_text = "Brak danych"
                
                ctk.CTkLabel(
                    recent_frame,
                    text=recent_text,
                    font=("Arial", 12),
                    justify="left",
                    anchor="w"
                ).grid(row=1, column=0, padx=20, pady=10, sticky="w")
                
        except Exception as e:
            ctk.CTkLabel(
                self.analytics_scrollable,
                text=f"Błąd podczas ładowania analityki: {str(e)}",
                font=("Arial", 12),
                text_color="red"
            ).grid(row=0, column=0, padx=20, pady=20)

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
            print(f"TIMEOUT: Brak odpowiedzi użytkownika dla '{raw_name}', używam wartości domyślnej: '{default_value}'")
            return default_value
        return result

    def review_user(self, parsed_data):
        self.review_queue.put(parsed_data)
        # Czekaj na wynik z głównego wątku GUI z timeoutem (10 minut)
        try:
            result = self.review_result_queue.get(timeout=600)
        except queue.Empty:
            # Timeout - użytkownik nie odpowiedział, zwracamy None (odrzucamy)
            print("TIMEOUT: Brak odpowiedzi użytkownika na weryfikację paragonu, odrzucam zmiany.")
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
                    status_text = status if status is not None else self.status_label.cget("text")
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
        dialog = ProductMappingDialog(
            self,
            title="Nieznany produkt",
            text=f"Produkt z paragonu: '{raw_name}'\n\n{prompt_text}",
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

        # Dodaj do historii przed przetwarzaniem
        add_to_history(self.selected_file_path)
        self.refresh_history()

        self.set_ui_state("disabled")
        self.process_button.configure(text="⏳ Przetwarzanie...")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        # Uruchom pasek postępu w trybie indeterminate
        self.update_status("Rozpoczynam przetwarzanie...", progress=-1)

        llm_model = Config.VISION_MODEL

        thread = threading.Thread(
            target=run_processing_pipeline,
            args=(
                self.selected_file_path,
                llm_model,
                self.log,
                self.prompt_user,
                self.review_user,
            ),
        )
        thread.daemon = True
        thread.start()

        self.monitor_thread(thread)

    def monitor_thread(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.monitor_thread(thread))
        else:
            self.set_ui_state("normal")
            self.process_button.configure(text="🔄 Przetwórz")
            # Zatrzymaj pasek postępu i ustaw na 100%
            self.progress_bar.stop()
            self.progress_bar.set(1.0)
            self.update_status("Gotowy", progress=100)
            self.log("INFO: Przetwarzanie zakończone.")


if __name__ == "__main__":
    app = App()
    app.mainloop()
