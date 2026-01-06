import time
import json
import os
import sys
from pathlib import Path
from ollama import Client

# --- KONFIGURACJA ŚCIEŻEK ---
# Dodajemy katalog backend do ścieżki, aby Python widział moduły 'app'
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent / 'backend'
sys.path.append(str(backend_dir))

try:
    from app.services.ocr_service import OCRService
except ImportError as e:
    print(f"BŁĄD IMPORTU: Nie znaleziono modułów backendu. {e}")
    sys.exit(1)

# Lista modeli
MODELS = [
    "bielik:latest",
    "gemma3:4b", 
    "llama3.2:latest"
]

# System Prompt (Taki sam jak w poprzednim teście, dla spójności)
SYSTEM_PROMPT = """
Jesteś asystentem AI. Analizujesz tekst paragonu.
Zwróć TYLKO JSON w formacie:
{
    "shop_name": "string",
    "date": "YYYY-MM-DD",
    "items": [{"name": "string", "quantity": float, "price": float}],
    "total_amount": float
}
Ignoruj rabaty, jeśli nie są częścią ceny końcowej. Suma (total_amount) to kwota do zapłaty.
"""

def run_benchmark():
    print("🚀 INICJALIZACJA BENCHMARKU NA PEŁNYM ZESTAWIE DANYCH...")
    
    # 1. Inicjalizacja OCR
    try:
        ocr_service = OCRService()
        print("✅ OCR Service gotowy.")
    except Exception as e:
        print(f"❌ Błąd OCR Service: {e}")
        return

    # 2. Pobranie plików
    samples_dir = Path("data/samples")
    if not samples_dir.exists():
        print(f"❌ Katalog {samples_dir} nie istnieje.")
        return
        
    supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg'}
    files = [f for f in samples_dir.iterdir() if f.suffix.lower() in supported_extensions]
    files.sort()
    
    if not files:
        print("❌ Brak plików do testów.")
        return

    print(f"📂 Znaleziono {len(files)} plików do przetworzenia.\n")
    
    # Inicjalizacja klienta Ollama
    try:
        client = Client(host='http://localhost:11434')
    except Exception as e:
        print(f"❌ Błąd Ollama: {e}")
        return

    results = []

    # 3. Główna pętla
    for file_path in files:
        print(f"🔹 PLIK: {file_path.name}")
        
        # A. OCR (raz na plik)
        try:
            print(f"   👁️  OCR...", end="", flush=True)
            ocr_start = time.time()
            ocr_text = ocr_service.parse_receipt(str(file_path))
            ocr_duration = time.time() - ocr_start
            print(f" OK ({ocr_duration:.2f}s, {len(ocr_text)} znaków)")
        except Exception as e:
            print(f" BŁĄD OCR: {e}")
            continue

        # B. Benchmark Modeli
        for model in MODELS:
            print(f"   🧠 {model:<15} ...", end="", flush=True)
            start_time = time.time()
            
            try:
                response = client.chat(model=model, messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': ocr_text},
                ])
                duration = time.time() - start_time
                content = response['message']['content']
                
                # Parsowanie
                try:
                    clean_json = content.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_json)
                    total = data.get('total_amount', 0.0)
                    shop = data.get('shop_name', '???')
                    status = "✅ OK"
                    error_msg = ""
                    
                    # Wstępna walidacja
                    if not isinstance(total, (int, float)) or total == 0:
                        status = "⚠️ ZERO/NULL"
                    
                except json.JSONDecodeError:
                    total = "---"
                    shop = "---"
                    status = "❌ JSON ERROR"
                    error_msg = "JSON Decode Error"
                except Exception as e:
                    total = "---"
                    shop = "---"
                    status = "❌ ERROR"
                    error_msg = str(e)

                print(f" {status} ({duration:.2f}s) | {shop} | {total}")
                
                results.append({
                    "file": file_path.name,
                    "model": model,
                    "time": duration,
                    "status": status,
                    "shop": shop,
                    "total": total,
                    "error": error_msg
                })

            except Exception as e:
                print(f" FAIL: {e}")
                results.append({
                    "file": file_path.name,
                    "model": model,
                    "time": 0,
                    "status": "CRITICAL FAIL",
                    "error": str(e)
                })

    # 4. Tabela Wyników
    print("\n" + "="*100)
    print(f"{'PLIK':<25} | {'MODEL':<15} | {'CZAS':<6} | {'STATUS':<12} | {'SKLEP':<15} | {'TOTAL':<8}")
    print("-" * 100)
    
    for r in results:
        status_icon = "✅" if r['status'] == "✅ OK" else "❌" if "ERROR" in r['status'] else "⚠️"
        print(f"{r['file'][:25]:<25} | {r['model']:<15} | {r['time']:<6.2f} | {r['status']:<12} | {str(r.get('shop', ''))[:15]:<15} | {str(r.get('total', '')):<8}")

    print("="*100)

    # 5. Podsumowanie średnich czasów
    print("\n📊 ŚREDNIE CZASY MODELI:")
    for model in MODELS:
        times = [r['time'] for r in results if r['model'] == model and r['status'] == "✅ OK"]
        if times:
            avg_time = sum(times) / len(times)
            print(f"   {model:<15}: {avg_time:.2f}s (na {len(times)} udanych prób)")
        else:
            print(f"   {model:<15}: brak udanych prób")

if __name__ == "__main__":
    run_benchmark()
