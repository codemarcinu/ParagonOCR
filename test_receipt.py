#!/usr/bin/env python3
"""
Skrypt testowy do przetwarzania konkretnego paragonu z pełnym pipeline.
"""
import os
import sys
import json
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Dodaj ścieżkę do modułów
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ReceiptParser"))

from ReceiptParser.src.ocr import extract_text_from_image
from ReceiptParser.src.llm import parse_receipt_from_text, parse_receipt_with_llm
from ReceiptParser.src.strategies import get_strategy_for_store
from ReceiptParser.src.main import verify_math_consistency
from ReceiptParser.src.config import Config


def default_serializer(obj):
    """Serializuje Decimal i datetime do stringów dla JSON."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def test_receipt(file_path: str, use_mistral_ocr: bool = True, use_vision_model: bool = False):
    """
    Testuje przetwarzanie paragonu z pełnym pipeline.
    
    Args:
        file_path: Ścieżka do pliku z paragonem
        use_mistral_ocr: Jeśli True, używa Mistral OCR, w przeciwnym razie Tesseract
        use_vision_model: Jeśli True i nie używa Mistral OCR, używa modelu wizyjnego zamiast tekstowego
    """
    print("=" * 70)
    print(f"TEST PARAGONU: {file_path}")
    print("=" * 70)
    
    if not os.path.exists(file_path):
        print(f"BŁĄD: Plik nie istnieje: {file_path}")
        return None
    
    try:
        # Krok 1: OCR
        print("\n[1/5] Ekstrakcja tekstu z obrazu (OCR)...")
        if use_mistral_ocr:
            if not Config.MISTRAL_API_KEY:
                print("OSTRZEŻENIE: Brak klucza API Mistral. Przełączam na Tesseract OCR.")
                use_mistral_ocr = False
        
        if use_mistral_ocr:
            print("  -> Używam Mistral OCR...")
            try:
                from ReceiptParser.src.mistral_ocr import MistralOCRClient
                mistral_client = MistralOCRClient()
                ocr_text = mistral_client.process_image(file_path)
            except ImportError:
                print("  OSTRZEŻENIE: Moduł mistralai nie jest zainstalowany. Przełączam na Tesseract OCR.")
                use_mistral_ocr = False
            if not ocr_text:
                print("  BŁĄD: Mistral OCR nie zwrócił wyniku. Przełączam na Tesseract.")
                use_mistral_ocr = False
        
        if not use_mistral_ocr:
            print("  -> Używam Tesseract OCR...")
            ocr_text = extract_text_from_image(file_path)
        
        if not ocr_text:
            print("BŁĄD: Nie udało się wyekstrahować tekstu z obrazu.")
            return None
        
        print(f"  ✓ Tekst wyekstrahowany ({len(ocr_text)} znaków)")
        print(f"\n  --- Fragment tekstu OCR ---")
        print(ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text)
        print("  ----------------------------")
        
        # Krok 2: Detekcja strategii
        print("\n[2/5] Detekcja strategii parsowania...")
        header_sample = ocr_text[:1000] if ocr_text else ""
        strategy = get_strategy_for_store(header_sample)
        print(f"  ✓ Wybrano strategię: {strategy.__class__.__name__}")
        
        # Krok 3: Parsowanie przez LLM
        print("\n[3/5] Parsowanie przez LLM...")
        system_prompt = strategy.get_system_prompt()
        if use_mistral_ocr:
            print("  -> Używam modelu tekstowego (Bielik) z tekstem z Mistral OCR...")
            parsed_data = parse_receipt_from_text(ocr_text, system_prompt_override=system_prompt)
        elif use_vision_model:
            print(f"  -> Używam modelu wizyjnego ({Config.VISION_MODEL}) z OCR jako wsparciem...")
            parsed_data = parse_receipt_with_llm(
                file_path,
                Config.VISION_MODEL,
                system_prompt_override=system_prompt,
                ocr_text=ocr_text,
            )
        else:
            print("  -> Używam modelu tekstowego (Bielik) z tekstem z Tesseract OCR...")
            parsed_data = parse_receipt_from_text(ocr_text, system_prompt_override=system_prompt)
        
        if not parsed_data:
            print("  BŁĄD: Nie udało się sparsować danych przez LLM.")
            return None
        
        print("  ✓ Dane sparsowane przez LLM")
        
        # Krok 4: Post-processing
        print("\n[4/5] Post-processing (strategia + weryfikacja matematyczna)...")
        log_messages = []
        
        def log_callback(msg):
            log_messages.append(msg)
            if msg.startswith("OSTRZEŻENIE") or msg.startswith("BŁĄD"):
                print(f"  ⚠ {msg}")
            elif msg.startswith("INFO"):
                print(f"  ℹ {msg}")
        
        # Post-processing przez strategię
        parsed_data = strategy.post_process(parsed_data, ocr_text=ocr_text)
        print("  ✓ Post-processing przez strategię zakończony")
        
        # Weryfikacja matematyczna
        parsed_data = verify_math_consistency(parsed_data, log_callback)
        print("  ✓ Weryfikacja matematyczna zakończona")
        
        # Krok 5: Wyświetlenie wyników
        print("\n[5/5] WYNIKI:")
        print("=" * 70)
        
        # Informacje o sklepie
        sklep_info = parsed_data.get("sklep_info", {})
        print(f"\n📦 SKLEP:")
        print(f"   Nazwa: {sklep_info.get('nazwa', 'N/A')}")
        print(f"   Lokalizacja: {sklep_info.get('lokalizacja', 'N/A')}")
        
        # Informacje o paragonie
        paragon_info = parsed_data.get("paragon_info", {})
        print(f"\n🧾 PARAGON:")
        data_zakupu = paragon_info.get("data_zakupu")
        if isinstance(data_zakupu, datetime):
            print(f"   Data zakupu: {data_zakupu.strftime('%Y-%m-%d')}")
        else:
            print(f"   Data zakupu: {data_zakupu}")
        suma = paragon_info.get("suma_calkowita", 0)
        print(f"   Suma całkowita: {suma} PLN")
        
        # Pozycje
        pozycje = parsed_data.get("pozycje", [])
        print(f"\n🛒 POZYCJE ({len(pozycje)}):")
        for i, item in enumerate(pozycje, 1):
            print(f"\n   [{i}] {item.get('nazwa_raw', 'N/A')}")
            print(f"       Ilość: {item.get('ilosc', 'N/A')} {item.get('jednostka', 'szt.')}")
            print(f"       Cena jednostkowa: {item.get('cena_jedn', 'N/A')} PLN")
            print(f"       Cena całkowita: {item.get('cena_calk', 'N/A')} PLN")
            rabat = item.get('rabat', 0)
            if rabat and float(rabat) > 0:
                print(f"       Rabat: -{rabat} PLN")
            cena_po_rab = item.get('cena_po_rab', item.get('cena_calk', 0))
            print(f"       Cena po rabacie: {cena_po_rab} PLN")
        
        # Podsumowanie matematyczne
        suma_pozycji = sum(
            float(str(item.get('cena_po_rab', item.get('cena_calk', 0))).replace(',', '.'))
            for item in pozycje
        )
        print(f"\n💰 PODSUMOWANIE:")
        print(f"   Suma pozycji (po rabatach): {suma_pozycji:.2f} PLN")
        print(f"   Suma paragonu: {suma} PLN")
        roznica = suma_pozycji - float(str(suma).replace(',', '.'))
        roznica_abs = abs(roznica)
        if roznica_abs < 0.10:
            print(f"   ✓ Różnica: {roznica_abs:.2f} PLN (OK)")
        elif roznica > 0 and roznica <= 20.0:
            # Różnica dodatnia (suma pozycji > suma paragonu) może być rabatem z karty
            print(f"   ℹ Różnica: {roznica:.2f} PLN (prawdopodobnie rabat z karty)")
        else:
            print(f"   ⚠ Różnica: {roznica_abs:.2f} PLN (możliwa niezgodność)")
        
        # JSON output
        print("\n" + "=" * 70)
        print("JSON OUTPUT:")
        print("=" * 70)
        print(json.dumps(parsed_data, indent=2, default=default_serializer, ensure_ascii=False))
        
        print("\n" + "=" * 70)
        print("✓ TEST ZAKOŃCZONY POMYŚLNIE")
        print("=" * 70)
        
        return parsed_data
        
    except Exception as e:
        print(f"\n❌ BŁĄD KRYTYCZNY: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Użycie: python test_receipt.py <sciezka_do_paragonu> [--no-mistral] [--vision]")
        print("\nOpcje:")
        print("  --no-mistral  : Użyj Tesseract OCR zamiast Mistral OCR")
        print("  --vision      : Użyj modelu wizyjnego (tylko z Tesseract)")
        sys.exit(1)
    
    file_path = sys.argv[1]
    use_mistral = "--no-mistral" not in sys.argv
    use_vision = "--vision" in sys.argv
    
    test_receipt(file_path, use_mistral_ocr=use_mistral, use_vision_model=use_vision)

