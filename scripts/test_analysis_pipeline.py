import asyncio
import sys
import os
import logging
import json
from pathlib import Path
from time import time

# --- KONFIGURACJA ŚCIEŻEK ---
# Dodajemy katalog backend do ścieżki, aby Python widział moduły 'app'
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent / 'backend'
sys.path.append(str(backend_dir))

# --- IMPORTY Z TWOJEGO PROJEKTU ---
try:
    from app.services.ocr_service import OCRService
    from app.services.llm_service import parse_receipt_text
except ImportError as e:
    print(f"BŁĄD IMPORTU: Nie znaleziono modułów backendu. Upewnij się, że jesteś w katalogu głównym projektu.\nSzczegóły: {e}")
    sys.exit(1)

# --- KONFIGURACJA LOGOWANIA ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- PLIKI DO TESTÓW ---
TEST_FILES = [
    "20250121_063301.pdf",      # Kaufland/Inny PDF
    "Biedra20251118.pdf",       # Biedronka PDF (Test rabatów)
    "auchan.pdf",               # Auchan PDF (Test niefiskalnych)
    "kaufland.pdf",             # Kaufland PDF
    "20250125lidl.png",         # Lidl PNG (Test obrazu)
    "lidl.png"                  # Lidl PNG
]

SAMPLES_DIR = Path("data/samples")

async def run_test():
    print("="*60)
    print(" 🚀 ROZPOCZYNAM TESTY ANALIZY PARAGONÓW (TERMINAL ONLY)")
    print(f" 📂 Katalog próbek: {SAMPLES_DIR.resolve()}")
    print("="*60)

    # Inicjalizacja serwisów
    try:
        ocr_service = OCRService()
        # LLM service is functional, no init needed beyond module load
        print("✅ Serwisy zainicjowane poprawnie.\n")
    except Exception as e:
        print(f"❌ Błąd inicjalizacji serwisów: {e}")
        return

    results = []

    for filename in TEST_FILES:
        file_path = SAMPLES_DIR / filename
        
        print(f"\n🔹 PRZETWARZANIE: {filename}")
        
        if not file_path.exists():
            print(f"   ⚠️ Plik nie istnieje w {SAMPLES_DIR}. Pomijam.")
            continue

        start_time = time()
        
        # 1. ETAP OCR
        try:
            print("   1️⃣  OCR / Ekstrakcja tekstu...", end="", flush=True)
            with open(file_path, "rb") as f:
                content = f.read()
            
            # Wywołanie Twojego serwisu OCR
            raw_text = await ocr_service.extract_text(content, filename)
            
            ocr_time = time() - start_time
            print(f" OK ({ocr_time:.2f}s)")
            
            # Podgląd co widzi "oczami" skrypt (pierwsze 200 znaków)
            preview = raw_text[:200].replace('\n', ' ')
            print(f"      👀 Podgląd OCR: \"{preview}...\"")
            
        except Exception as e:
            print(f" BŁĄD: {e}")
            results.append({"file": filename, "status": "OCR_FAIL", "error": str(e)})
            continue

        # 2. ETAP LLM (ANALIZA)
        try:
            print("   2️⃣  LLM (Bielik) Analiza...", end="", flush=True)
            llm_start = time()
            
            # Wywołanie Twojego serwisu LLM - Sync call inside async wrapper often needs run_in_executor if blocking, 
            # but for this script we can just call it blocking.
            parsed_data = parse_receipt_text(raw_text)
            
            llm_time = time() - llm_start
            print(f" OK ({llm_time:.2f}s)")

            # Weryfikacja kluczowych pól
            shop = parsed_data.shop or 'NIEZNANY'
            total = parsed_data.total or 0
            items_count = len(parsed_data.items)
            
            print(f"      🛒 Sklep: {shop}")
            print(f"      💰 Kwota: {total} PLN")
            print(f"      📦 Pozycje: {items_count}")
            
            # Sprawdzenie czy JSON wygląda na poprawny
            if total == 0 or items_count == 0:
                 print("      ⚠️ OSTRZEŻENIE: Podejrzanie puste dane!")

            results.append({
                "file": filename,
                "status": "SUCCESS",
                "shop": shop,
                "total": total,
                "items": items_count,
                "time": ocr_time + llm_time
            })
            
            # Wyświetl pełny wynik dla jednego pliku (opcjonalnie)
            # print(json.dumps(parsed_data.to_dict(), indent=2, ensure_ascii=False))

        except Exception as e:
            print(f" BŁĄD LLM: {e}")
            results.append({"file": filename, "status": "LLM_FAIL", "error": str(e)})

    # PODSUMOWANIE
    print("\n" + "="*60)
    print(" 📊 PODSUMOWANIE WYNIKÓW")
    print("="*60)
    print(f"{'PLIK':<25} | {'STATUS':<10} | {'SKLEP':<15} | {'KWOTA':<10}")
    print("-" * 65)
    
    for r in results:
        if r['status'] == 'SUCCESS':
            print(f"{r['file']:<25} | ✅ OK     | {r['shop'][:15]:<15} | {r['total']:<10}")
        else:
            print(f"{r['file']:<25} | ❌ FAIL   | {r.get('error', '')[:25]}")
    print("="*60)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_test())
