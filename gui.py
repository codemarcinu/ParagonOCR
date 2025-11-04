
import customtkinter as ctk
from tkinter import filedialog
import threading
import queue
import os

# Lokalne importy - zakładamy, że gui.py jest w folderze głównym projektu
from src.main import run_processing_pipeline
from src.database import init_db

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ReceiptParser")
        self.geometry("800x600")
        ctk.set_appearance_mode("System")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- WIDGETY ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.main_frame.grid_columnconfigure(1, weight=1)

        self.file_button = ctk.CTkButton(self.main_frame, text="Wybierz plik paragonu", command=self.select_file)
        self.file_button.grid(row=0, column=0, padx=10, pady=10)

        self.file_label = ctk.CTkLabel(self.main_frame, text="Nie wybrano pliku", anchor="w")
        self.file_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.llm_switch_var = ctk.StringVar(value="off")
        self.llm_switch = ctk.CTkSwitch(self.main_frame, text="Użyj LLM do parsowania (np. llava)", variable=self.llm_switch_var, onvalue="llava:latest", offvalue="off")
        self.llm_switch.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.process_button = ctk.CTkButton(self.main_frame, text="Przetwórz", command=self.start_processing, state="disabled")
        self.process_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)
        
        self.init_db_button = ctk.CTkButton(self.main_frame, text="Inicjalizuj bazę danych", command=self.initialize_database)
        self.init_db_button.grid(row=3, column=0, columnspan=2, padx=10, pady=5)

        self.log_textbox = ctk.CTkTextbox(self, state="disabled", wrap="word")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        # --- Zmienne stanu ---
        self.selected_file_path = None
        self.log_queue = queue.Queue()
        self.prompt_queue = queue.Queue()
        self.prompt_result_queue = queue.Queue()

        self.after(100, self.process_log_queue)

    def select_file(self):
        file_path = filedialog.askopenfilename(title="Wybierz plik paragonu", filetypes=[
            ("Pliki obrazów", "*.png *.jpg *.jpeg"),
            ("Pliki PDF", "*.pdf"),
            ("Wszystkie pliki", "*.*"),
        ])
        if file_path:
            self.selected_file_path = file_path
            self.file_label.configure(text=os.path.basename(file_path))
            self.process_button.configure(state="normal")

    def log(self, message):
        self.log_queue.put(message)

    def prompt_user(self, prompt_text, default_value, raw_name):
        self.prompt_queue.put((prompt_text, default_value, raw_name))
        # Czekaj na wynik z głównego wątku GUI
        result = self.prompt_result_queue.get()
        return result

    def process_log_queue(self):
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", message + "\n")
                self.log_textbox.configure(state="disabled")
                self.log_textbox.see("end")
            
            # Sprawdź, czy jest prośba o prompt
            if not self.prompt_queue.empty():
                prompt_text, default_value, raw_name = self.prompt_queue.get_nowait()
                self.show_prompt_dialog(prompt_text, default_value, raw_name)

        finally:
            self.after(100, self.process_log_queue)

    def show_prompt_dialog(self, prompt_text, default_value, raw_name):
        dialog = ctk.CTkInputDialog(title="Potrzebna informacja", text=f"Nieznany produkt: {raw_name}\n{prompt_text}")
        # Niestety, CTkInputDialog nie wspiera wartości domyślnej w prosty sposób,
        # więc musimy obejść to, ustawiając tekst w polu wejściowym po utworzeniu.
        dialog.geometry("400x200")
        dialog._entry.delete(0, "end")
        dialog._entry.insert(0, default_value)
        
        user_input = dialog.get_input()
        self.prompt_result_queue.put(user_input if user_input is not None else "")

    def set_ui_state(self, state: str):
        self.process_button.configure(state=state)
        self.file_button.configure(state=state)
        self.llm_switch.configure(state=state)
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

        self.set_ui_state("disabled")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

        llm_model = self.llm_switch_var.get()
        if llm_model == "off":
            llm_model = None

        thread = threading.Thread(
            target=run_processing_pipeline,
            args=(self.selected_file_path, llm_model, self.log, self.prompt_user)
        )
        thread.daemon = True
        thread.start()

        # Sprawdzaj, czy wątek się zakończył
        self.monitor_thread(thread)

    def monitor_thread(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.monitor_thread(thread))
        else:
            self.set_ui_state("normal")
            self.log("INFO: Przetwarzanie zakończone.")

if __name__ == "__main__":
    app = App()
    app.mainloop()
