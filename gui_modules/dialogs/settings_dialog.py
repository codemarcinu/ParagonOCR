import os
import customtkinter as ctk

from src.config import Config
from src.config_prompts import (
    load_prompts,
    save_prompts,
    reset_prompts_to_default,
    DEFAULT_PROMPTS,
)
from src.unified_design_system import AppColors, AppSpacing, Icons, adjust_color
from src.gui_optimizations import ToolTip

class SettingsDialog(ctk.CTkToplevel):
    """Okno ustawień - edycja promptów systemowych"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚙️ Ustawienia - Prompty Systemowe")
        self.geometry("900x700")

        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)
        ctk.CTkLabel(
            header_frame,
            text="⚙️ Ustawienia Promptów Systemowych Bielika",
            font=("Arial", 18, "bold"),
        ).pack(pady=AppSpacing.SM)

        # Scrollable frame dla promptów
        scrollable = ctk.CTkScrollableFrame(self)
        scrollable.pack(fill="both", expand=True, padx=AppSpacing.SM, pady=AppSpacing.XS)

        # --- Sekcja OCR ---
        ocr_frame = ctk.CTkFrame(scrollable)
        ocr_frame.grid(row=0, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.SM)
        ocr_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(ocr_frame, text="Silnik OCR:", font=("Arial", 12, "bold")).grid(
            row=0, column=0, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w"
        )
        self.ocr_engine_var = ctk.StringVar(value=Config.OCR_ENGINE)
        self.ocr_engine_combo = ctk.CTkComboBox(
            ocr_frame,
            values=["tesseract", "easyocr"],
            variable=self.ocr_engine_var,
            width=200,
        )
        self.ocr_engine_combo.grid(row=0, column=1, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w")

        self.use_gpu_var = ctk.BooleanVar(value=Config.USE_GPU_OCR)
        self.use_gpu_check = ctk.CTkCheckBox(
            ocr_frame,
            text="Użyj GPU dla EasyOCR (jeśli dostępne)",
            variable=self.use_gpu_var,
        )
        self.use_gpu_check.grid(
            row=1, column=0, columnspan=2, padx=AppSpacing.SM, pady=AppSpacing.SM, sticky="w"
        )

        # --- Sekcja Promptów ---
        ctk.CTkLabel(
            scrollable, text="Prompty Systemowe", font=("Arial", 16, "bold")
        ).grid(row=1, column=0, sticky="w", padx=AppSpacing.SM, pady=(20, 5))

        # Wczytaj prompty
        self.prompts = load_prompts()
        self.text_boxes = {}

        # Opisy promptów
        prompt_descriptions = {
            "answer_question": "Prompt dla odpowiadania na pytania użytkownika",
            "suggest_dishes": "Prompt dla proponowania potraw",
            "shopping_list": "Prompt dla generowania list zakupów",
        }

        # Utwórz pola tekstowe dla każdego promptu
        for i, (key, value) in enumerate(self.prompts.items()):
            row_idx = i * 2 + 2  # Offset for OCR section

            # Label z opisem
            label = ctk.CTkLabel(
                scrollable,
                text=prompt_descriptions.get(key, key),
                font=("Arial", 14, "bold"),
            )
            label.grid(row=row_idx, column=0, sticky="w", padx=AppSpacing.SM, pady=(10, 5))

            # Textbox dla promptu
            textbox = ctk.CTkTextbox(scrollable, height=150, font=("Arial", 11))
            textbox.insert("1.0", value)
            textbox.grid(row=row_idx + 1, column=0, sticky="ew", padx=AppSpacing.SM, pady=AppSpacing.XS)
            scrollable.grid_columnconfigure(0, weight=1)

            self.text_boxes[key] = textbox

        # Footer z przyciskami
        footer_frame = ctk.CTkFrame(self)
        footer_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)

        btn_save = ctk.CTkButton(
            footer_frame,
            text=f"{Icons.SAVE} Zapisz",
            command=self.save_prompts,
            fg_color=AppColors.SUCCESS,
            hover_color=adjust_color(AppColors.SUCCESS, -15),
            width=150,
        )
        btn_save.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_save, "Zapisz zmiany w ustawieniach")

        btn_reset = ctk.CTkButton(
            footer_frame,
            text=f"{Icons.REFRESH} Resetuj do domyślnych",
            command=self.reset_prompts,
            fg_color=AppColors.WARNING,
            hover_color=adjust_color(AppColors.WARNING, -15),
            width=200,
        )
        btn_reset.pack(side="left", padx=AppSpacing.XS)
        ToolTip(btn_reset, "Przywróć domyślne prompty i ustawienia")

        btn_cancel = ctk.CTkButton(
            footer_frame,
            text="Anuluj",
            command=self.destroy,
            fg_color=AppColors.ERROR,
            hover_color=adjust_color(AppColors.ERROR, -15),
            width=150,
        )
        btn_cancel.pack(side="right", padx=AppSpacing.XS)
        ToolTip(btn_cancel, "Zamknij bez zapisywania")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.after(100, self.grab_set)

    def save_prompts(self):
        """Zapisuje ustawienia i prompty"""
        try:
            # 1. Zapisz ustawienia OCR do .env
            
            # Fix path for .env (3 levels up from gui_modules/dialogs/settings_dialog.py)
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")

            # Wczytaj obecną zawartość .env
            env_lines = []
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    env_lines = f.readlines()

            # Aktualizuj lub dodaj zmienne
            new_ocr_engine = self.ocr_engine_var.get()
            new_use_gpu = str(self.use_gpu_var.get()).lower()

            updated_engine = False
            updated_gpu = False

            new_lines = []
            for line in env_lines:
                if line.startswith("OCR_ENGINE="):
                    new_lines.append(f"OCR_ENGINE={new_ocr_engine}\n")
                    updated_engine = True
                elif line.startswith("USE_GPU_OCR="):
                    new_lines.append(f"USE_GPU_OCR={new_use_gpu}\n")
                    updated_gpu = True
                else:
                    new_lines.append(line)

            if not updated_engine:
                new_lines.append(f"OCR_ENGINE={new_ocr_engine}\n")
            if not updated_gpu:
                new_lines.append(f"USE_GPU_OCR={new_use_gpu}\n")

            with open(env_path, "w") as f:
                f.writelines(new_lines)

            # Aktualizuj Config w pamięci
            Config.OCR_ENGINE = new_ocr_engine
            Config.USE_GPU_OCR = self.use_gpu_var.get()

            # 2. Zapisz prompty
            new_prompts = {}
            for key, textbox in self.text_boxes.items():
                new_prompts[key] = textbox.get("1.0", "end-1c").strip()

            if save_prompts(new_prompts):
                if hasattr(self.master, "notifications"):
                    self.master.notifications.show_success(
                         "Ustawienia i prompty zostały zapisane!\nZmiana silnika OCR może wymagać restartu aplikacji."
                    )
                self.destroy()
            else:
                 if hasattr(self.master, "notifications"):
                    self.master.notifications.show_error("Nie udało się zapisać promptów.")
        except Exception as e:
            if hasattr(self.master, "notifications"):
                self.master.notifications.show_error(f"Wystąpił błąd podczas zapisywania: {e}")

    def reset_prompts(self):
        """Resetuje prompty do wartości domyślnych"""
        # For blocking confirmations, usage of self.master.notification.confirm usually would be better,
        # but NotificationsDialog was blocking/dialog-based anyway or toast based?
        # The user requested upgrading to toasts, but `confirm` is still often a blocking dialog.
        # Check src/notifications.py content again.
        # NotificationDialog class has `confirm` method.
        # I should check if App has NotificationDialog instance.
        
        confirmed = False
        if hasattr(self.master, "notifications_dialog"): # If I add this to App
             confirmed = self.master.notifications_dialog.confirm(
                "Potwierdzenie",
                "Czy na pewno chcesz zresetować wszystkie prompty do wartości domyślnych?"
            )
        else:
             # Fallback to messagebox if not refactored in App yet, or import messagebox
             from tkinter import messagebox
             confirmed = messagebox.askyesno(
                "Potwierdzenie",
                "Czy na pewno chcesz zresetować wszystkie prompty do wartości domyślnych?",
                parent=self
            )
            
        if confirmed:
            try:
                reset_prompts_to_default()
                # Odśwież okno
                self.destroy()
                # Otwórz ponownie
                SettingsDialog(self.master)
            except Exception as e:
                if hasattr(self.master, "notifications"):
                    self.master.notifications.show_error(f"Nie udało się zresetować promptów: {e}")
                else:
                    from tkinter import messagebox
                    messagebox.showerror("Błąd", f"Nie udało się zresetować promptów: {e}")
