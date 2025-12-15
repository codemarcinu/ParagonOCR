import os
import customtkinter as ctk
from datetime import datetime, date, timedelta
from decimal import Decimal
from PIL import Image
from sqlalchemy.orm import sessionmaker, joinedload

from src.database import engine, AliasProduktu
from src.normalization_rules import find_static_match
from src.unified_design_system import AppColors, AppSpacing, Icons, adjust_color
from src.unified_design_system import AppColors, AppSpacing, Icons, adjust_color
from src.gui_optimizations import ToolTip
import subprocess
import platform

class ReviewDialog(ctk.CTkToplevel):
    def __init__(self, parent, parsed_data):
        super().__init__(parent)
        self.title("Weryfikacja Paragonu")
        self.geometry("1000x700")
        self.parsed_data = parsed_data
        self.result_data = None

        # --- Header ---
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)

        ctk.CTkLabel(self.header_frame, text="Sklep:").grid(
            row=0, column=0, padx=AppSpacing.XS, pady=AppSpacing.XS
        )
        self.store_entry = ctk.CTkEntry(self.header_frame, width=200)
        self.store_entry.grid(row=0, column=1, padx=AppSpacing.XS, pady=AppSpacing.XS)
        self.store_entry.insert(0, parsed_data["sklep_info"]["nazwa"])

        ctk.CTkLabel(self.header_frame, text="Data:").grid(
            row=0, column=2, padx=AppSpacing.XS, pady=AppSpacing.XS
        )
        self.date_entry = ctk.CTkEntry(self.header_frame, width=150)
        self.date_entry.grid(row=0, column=3, padx=AppSpacing.XS, pady=AppSpacing.XS)
        # Format daty do stringa
        date_val = parsed_data["paragon_info"]["data_zakupu"]
        if isinstance(date_val, (datetime, date)):
            date_val = date_val.strftime("%Y-%m-%d")
        self.date_entry.insert(0, str(date_val))

        ctk.CTkLabel(self.header_frame, text="Suma:").grid(
            row=0, column=4, padx=AppSpacing.XS, pady=AppSpacing.XS
        )
        self.total_entry = ctk.CTkEntry(self.header_frame, width=100)
        self.total_entry.grid(row=0, column=5, padx=AppSpacing.XS, pady=AppSpacing.XS)
        self.total_entry.insert(0, str(parsed_data["paragon_info"]["suma_calkowita"]))

        # --- Body (Items) ---
        # Kontener główny
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=AppSpacing.SM, pady=AppSpacing.XS)

        # Sprawdź czy mamy podgląd obrazu
        file_path = parsed_data.get("file_path")
        if file_path and os.path.exists(file_path):
            # Poszerz okno dla podglądu
            self.geometry("1400x800")
            
            self.main_container.grid_columnconfigure(0, weight=1) # Preview
            self.main_container.grid_columnconfigure(1, weight=2) # Form
            
            # --- Left: Preview ---
            # --- Left: Preview Column ---
            self.preview_col = ctk.CTkFrame(self.main_container, fg_color="transparent")
            self.preview_col.grid(row=0, column=0, sticky="nsew", padx=(0, AppSpacing.SM), pady=0)
            
            # Toolbar
            self.preview_toolbar = ctk.CTkFrame(self.preview_col, fg_color="transparent")
            self.preview_toolbar.pack(fill="x", pady=(0, 5))
            
            ctk.CTkButton(
                self.preview_toolbar, 
                text=f"{Icons.SEARCH} Otwórz oryginał", 
                command=lambda: self.open_image_external(file_path),
                height=28,
                fg_color=AppColors.PRIMARY,
                hover_color=adjust_color(AppColors.PRIMARY, -15)
            ).pack(side="left")

            # Scrollable Image
            self.preview_scroll = ctk.CTkScrollableFrame(self.preview_col, label_text="Podgląd Paragonu")
            self.preview_scroll.pack(fill="both", expand=True)
            
            try:
                img = Image.open(file_path)
                # Resize for display (width ~450px, keep aspect ratio)
                # Zwiększamy nieco domyślną szerokość dla lepszej czytelności
                target_width = 500
                aspect_ratio = img.height / img.width
                target_height = int(target_width * aspect_ratio)
                
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(target_width, target_height))
                
                self.img_label = ctk.CTkLabel(self.preview_scroll, text="", image=ctk_img)
                self.img_label.pack(fill="both", expand=True)
            except Exception as e:
                ctk.CTkLabel(self.preview_scroll, text=f"Błąd ładowania obrazu:\n{e}").pack()

            # --- Right: Form ---
            self.form_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
            self.form_container.grid(row=0, column=1, sticky="nsew")
            
            self.scrollable_frame = ctk.CTkScrollableFrame(self.form_container)
            self.scrollable_frame.pack(fill="both", expand=True)
        else:
            # Brak obrazu - standardowy widok
            self.scrollable_frame = ctk.CTkScrollableFrame(self.main_container)
            self.scrollable_frame.pack(fill="both", expand=True)

        # Headers - dodano kolumnę "Znormalizowana nazwa" i "Data ważności"
        headers = [
            "Nazwa (raw)",
            "Znormalizowana nazwa",
            "Ilość",
            "Cena jedn.",
            "Wartość",
            "Rabat",
            "Po rabacie",
            "Data ważności",
        ]
        for col, text in enumerate(headers):
            ctk.CTkLabel(
                self.scrollable_frame, text=text, font=("Arial", 12, "bold")
            ).grid(row=0, column=col, padx=AppSpacing.XS, pady=AppSpacing.XS)

        # Pobierz sugestie znormalizowanych nazw z bazy danych (jeśli dostępna)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        normalized_suggestions = {}
        try:
            for item in parsed_data["pozycje"]:
                nazwa_raw = item.get("nazwa_raw", "").strip()
                # Sprawdź czy istnieje alias w bazie
                alias = (
                    session.query(AliasProduktu)
                    .options(joinedload(AliasProduktu.produkt))
                    .filter_by(nazwa_z_paragonu=nazwa_raw)
                    .first()
                )
                if alias:
                    normalized_suggestions[nazwa_raw] = (
                        alias.produkt.znormalizowana_nazwa
                    )
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
            # Alternatywne kolory dla lepszej czytelności
            is_even = i % 2 == 0
            mode = ctk.get_appearance_mode()

            if is_skip:
                row_frame.configure(fg_color=AppColors.ERROR)
                tooltip_text = "Ta pozycja została oznaczona do pominięcia"
            elif is_unknown:
                row_frame.configure(fg_color=AppColors.WARNING)
                tooltip_text = "Nieznany produkt - wymaga weryfikacji"
            else:
                # Alternatywne kolory dla parzystych/nieparzystych wierszy
                if mode == "Dark":
                    row_frame.configure(
                        fg_color=AppColors.ROW_EVEN if is_even else AppColors.ROW_ODD
                    )
                else:
                    row_frame.configure(
                        fg_color=(
                            AppColors.ROW_EVEN_LIGHT
                            if is_even
                            else AppColors.ROW_ODD_LIGHT
                        )
                    )
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
                ToolTip(
                    e_normalized, f"Sugestia znormalizowanej nazwy: {normalized_name}"
                )

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
        self.footer_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)

        self.save_btn = ctk.CTkButton(
            self.footer_frame,
            text=f"{Icons.SAVE} Zatwierdź i Zapisz",
            command=self.on_save,
            fg_color=AppColors.SUCCESS,
            hover_color=adjust_color(AppColors.SUCCESS, -15),
        )
        self.save_btn.pack(side="right", padx=AppSpacing.SM)

        self.discard_btn = ctk.CTkButton(
            self.footer_frame,
            text="Odrzuć",
            command=self.on_discard,
            fg_color=AppColors.ERROR,
            hover_color=adjust_color(AppColors.ERROR, -15),
        )
        self.discard_btn.pack(side="left", padx=AppSpacing.SM)

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
                        data_waznosci = datetime.strptime(
                            data_waznosci_str, "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        if hasattr(self.master, "notifications"):
                            self.master.notifications.show_error(
                                f"Nieprawidłowy format daty ważności: {data_waznosci_str}\nUżyj formatu YYYY-MM-DD"
                            )
                        else:
                            # Fallback if notifications not available
                            print(f"Error: Invalid date format {data_waznosci_str}")
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
            if hasattr(self.master, "notifications"):
                self.master.notifications.show_error(f"Błąd podczas zapisu: {e}")

    def on_discard(self):
        self.result_data = None
        self.destroy()

    def get_result(self):
        self.master.wait_window(self)
        return self.result_data

    def open_image_external(self, file_path):
        """Otwiera obraz w domyślnej przeglądarce systemu."""
        try:
            if platform.system() == 'Darwin':       # macOS
                subprocess.call(('open', file_path))
            elif platform.system() == 'Windows':    # Windows
                os.startfile(file_path)
            else:                                   # linux variants
                subprocess.call(('xdg-open', file_path))
        except Exception as e:
            if hasattr(self.master, "notifications"):
                self.master.notifications.show_error(f"Nie udało się otworzyć pliku: {e}")
            else:
                print(f"Error opening file: {e}")
