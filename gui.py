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
from src.database import init_db, engine, Produkt, StanMagazynowy, KategoriaProduktu, AliasProduktu
from src.config import Config
from src.normalization_rules import find_static_match
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
        label = ctk.CTkLabel(tw, text=self.text, justify="left",
                             bg="#1a1a1a", fg_color="#1a1a1a", text_color="white",
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
        self.grab_set()  # Make modal

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
        self.grab_set()

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
        self.grab_set()
    
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
        self.grab_set()
    
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

        # --- MAIN CONTENT AREA ---
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # --- WIDGETY DLA PARAGONÓW ---
        self.receipts_frame = ctk.CTkFrame(self.content_frame)
        self.receipts_frame.grid(row=0, column=0, sticky="nsew")
        self.receipts_frame.grid_columnconfigure(0, weight=1)
        self.receipts_frame.grid_rowconfigure(5, weight=1)
        
        # Historia plików
        history_frame = ctk.CTkFrame(self.receipts_frame)
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
            self.receipts_frame, text="Nie wybrano pliku", anchor="w"
        )
        self.file_label.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="ew")

        buttons_frame = ctk.CTkFrame(self.receipts_frame)
        buttons_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        
        self.process_button = ctk.CTkButton(
            buttons_frame,
            text="🔄 Przetwórz",
            command=self.start_processing,
            state="disabled",
        )
        self.process_button.pack(side="left", padx=5)

        self.init_db_button = ctk.CTkButton(
            buttons_frame,
            text="⚙️ Inicjalizuj bazę danych",
            command=self.initialize_database,
        )
        self.init_db_button.pack(side="left", padx=5)

        # Status label i progress bar
        self.status_label = ctk.CTkLabel(
            self.receipts_frame, text="Gotowy", anchor="w", font=("Arial", 12)
        )
        self.status_label.grid(row=3, column=0, columnspan=4, padx=10, pady=(10, 5), sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self.receipts_frame)
        self.progress_bar.grid(row=4, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.log_textbox = ctk.CTkTextbox(self.receipts_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=5, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

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
        """Pokazuje zakładkę paragonów"""
        self.receipts_frame.grid(row=0, column=0, sticky="nsew")
    
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
        """Pokazuje stan magazynu"""
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Create inventory window
        inv_window = ctk.CTkToplevel(self)
        inv_window.title("Stan Magazynu")
        inv_window.geometry("1000x600")
        
        scrollable = ctk.CTkScrollableFrame(inv_window)
        scrollable.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Headers
        headers = ["Produkt", "Ilość", "Jednostka", "Data ważności", "Status"]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                scrollable, text=text, font=("Arial", 12, "bold")
            ).grid(row=0, column=col, padx=5, pady=5)
        
        stany = session.query(StanMagazynowy).join(Produkt).filter(
            StanMagazynowy.ilosc > 0
        ).order_by(StanMagazynowy.data_waznosci).all()
        
        for i, stan in enumerate(stany):
            row = i + 1
            ctk.CTkLabel(
                scrollable,
                text=stan.produkt.znormalizowana_nazwa,
                width=300
            ).grid(row=row, column=0, padx=5, pady=2, sticky="w")
            
            ctk.CTkLabel(
                scrollable,
                text=str(stan.ilosc),
                width=100
            ).grid(row=row, column=1, padx=5, pady=2)
            
            ctk.CTkLabel(
                scrollable,
                text=stan.jednostka_miary or "szt",
                width=100
            ).grid(row=row, column=2, padx=5, pady=2)
            
            data_waz = stan.data_waznosci.strftime("%Y-%m-%d") if stan.data_waznosci else "Brak"
            ctk.CTkLabel(
                scrollable,
                text=data_waz,
                width=120
            ).grid(row=row, column=3, padx=5, pady=2)
            
            # Status
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
            
            ctk.CTkLabel(
                scrollable,
                text=status,
                width=150,
                text_color=color
            ).grid(row=row, column=4, padx=5, pady=2)
        
        session.close()

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
