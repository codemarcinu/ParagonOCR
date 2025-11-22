import sys
import os

# Dodaj ścieżkę do modułów (scripts/ jest w głównym katalogu, ReceiptParser/ też)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ReceiptParser'))

try:
    from src.config import Config

    print("Config loaded successfully.")
    Config.print_config()

    print("Importing src.llm...")
    import src.llm

    print("src.llm imported successfully.")

    print("Importing src.main...")
    import src.main

    print("src.main imported successfully.")

    print("VERIFICATION SUCCESS")
except Exception as e:
    print(f"VERIFICATION FAILED: {e}")
    import traceback

    traceback.print_exc()
