
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

print("Attempting to import app.main...")
try:
    from app.main import app
    print("SUCCESS: app.main imported successfully")
except Exception as e:
    print(f"ERROR: Failed to import app.main: {e}")
    import traceback
    traceback.print_exc()
