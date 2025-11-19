import sys
import os

# Add ReceiptParser to path so we can import src
sys.path.append(os.path.join(os.getcwd(), "ReceiptParser"))

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
