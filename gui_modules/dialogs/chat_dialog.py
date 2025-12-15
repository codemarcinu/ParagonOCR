import customtkinter as ctk
import threading

from src.bielik import BielikAssistant
from src.unified_design_system import AppColors, AppSpacing, Icons
from src.gui_optimizations import ToolTip

class BielikChatDialog(ctk.CTkToplevel):
    """Okno czatu z asystentem Bielik"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("🦅 Bielik - Asystent Kulinarny")
        self.geometry("800x600")
        self.assistant = None

        # Header
        header_frame = ctk.CTkFrame(self)
        header_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)
        ctk.CTkLabel(
            header_frame,
            text="🦅 Bielik - Asystent Kulinarny",
            font=("Arial", 18, "bold"),
        ).pack(pady=AppSpacing.SM)

        # Chat area (scrollable)
        self.chat_frame = ctk.CTkScrollableFrame(self)
        self.chat_frame.pack(fill="both", expand=True, padx=AppSpacing.SM, pady=AppSpacing.XS)

        # Input area
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.SM)

        self.input_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Zadaj pytanie Bielikowi...",
            font=("Arial", 14),
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=AppSpacing.XS)
        self.input_entry.bind("<Return>", lambda e: self.send_message())

        self.send_button = ctk.CTkButton(
            input_frame, text="Wyślij", command=self.send_message, width=100
        )
        self.send_button.pack(side="right", padx=AppSpacing.XS)
        ToolTip(self.send_button, "Wyślij wiadomość do asystenta")

        # Status label
        self.status_label = ctk.CTkLabel(self, text="Gotowy", font=("Arial", 10))
        self.status_label.pack(pady=AppSpacing.XS)

        # Inicjalizuj asystenta
        self.init_assistant()

        # Dodaj powitanie
        self.add_message(
            "Bielik",
            "Cześć! Jestem Bielik, twój asystent kulinarny. Jak mogę Ci pomóc?",
        )

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def init_assistant(self):
        """Inicjalizuje asystenta Bielik"""
        try:
            self.assistant = BielikAssistant()
            self.status_label.configure(text="Gotowy", text_color=AppColors.SUCCESS)
        except Exception as e:
            self.status_label.configure(text=f"Błąd: {e}", text_color=AppColors.ERROR)
            if hasattr(self.master, "notifications"):
                self.master.notifications.show_error(f"Nie udało się połączyć z bazą danych: {e}")
            else:
                print(f"Błąd inicjalizacji Bielika: {e}")

    def add_message(self, sender: str, message: str):
        """Dodaje wiadomość do czatu"""
        # Ramka dla wiadomości
        msg_frame = ctk.CTkFrame(self.chat_frame)
        msg_frame.pack(fill="x", padx=AppSpacing.XS, pady=AppSpacing.XS)

        # Kolor w zależności od nadawcy
        if sender == "Bielik":
            # AppColors.CHAT_BOT is tuple (light, dark) but ctk handles tuple for colors
            msg_frame.configure(fg_color=AppColors.CHAT_BOT)
            sender_text = f"{Icons.BEAR} Bielik:"
        else:
            msg_frame.configure(fg_color=AppColors.CHAT_USER)
            sender_text = "Ty:"

        # Label z wiadomością
        msg_label = ctk.CTkLabel(
            msg_frame,
            text=f"{sender_text} {message}",
            font=("Arial", 12),
            wraplength=700,
            justify="left",
            anchor="w",
        )
        msg_label.pack(fill="x", padx=AppSpacing.SM, pady=AppSpacing.XS)

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
        self.status_label.configure(text="Bielik myśli...", text_color=AppColors.WARNING)

        # Uruchom w osobnym wątku, żeby nie blokować GUI
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
            self.after(
                0,
                lambda: self.status_label.configure(text="Gotowy", text_color=AppColors.SUCCESS),
            )
            self.after(0, lambda: self.send_button.configure(state="normal"))
        except Exception as e:
            error_msg = f"Przepraszam, wystąpił błąd: {str(e)}"
            self.after(0, lambda: self.add_message("Bielik", error_msg))
            self.after(
                0, lambda: self.status_label.configure(text="Błąd", text_color=AppColors.ERROR)
            )
            self.after(0, lambda: self.send_button.configure(state="normal"))

    def on_close(self):
        """Zamyka okno i zwalnia zasoby"""
        if self.assistant:
            self.assistant.close()
        self.destroy()
