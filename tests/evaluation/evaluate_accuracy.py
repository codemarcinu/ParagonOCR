import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from decimal import Decimal

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from ReceiptParser.src.llm import parse_receipt_from_text, parse_receipt_with_llm
from ReceiptParser.src.config import Config
from ReceiptParser.src.mistral_ocr import MistralOCRClient
from ReceiptParser.src.ocr import convert_pdf_to_image, extract_text_from_image
from ReceiptParser.src.strategies import get_strategy_for_store
from ReceiptParser.src.main import verify_math_consistency

# Configuration
GROUND_TRUTH_FILE = os.path.join(os.path.dirname(__file__), "ground_truth.json")
IMAGES_DIR = os.path.join(
    os.path.dirname(__file__), "../../ReceiptParser/data/receipts"
)


def load_ground_truth() -> Dict[str, Any]:
    if not os.path.exists(GROUND_TRUTH_FILE):
        print(f"ERROR: Ground truth file not found at {GROUND_TRUTH_FILE}")
        return {}
    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_decimal(value: Any) -> float:
    try:
        if isinstance(value, str):
            value = value.replace(",", ".")
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def compare_receipts(predicted: Dict, expected: Dict) -> Dict[str, Any]:
    """
    Porównuje przewidziane dane z oczekiwanymi (ground truth).
    Uwzględnia rabaty i ceny po rabacie po post-processingu.
    """
    metrics = {
        "store_match": False,
        "date_match": False,
        "total_match": False,
        "items_count_match": False,
        "items_found": 0,
        "items_expected": len(expected.get("pozycje", [])),
        "items_perfect_match": 0,
        "items_name_match": 0,
        "items_price_match": 0,
        "items_discount_match": 0,
    }

    # 1. Store Name (Fuzzy match)
    pred_store = predicted.get("sklep_info", {}).get("nazwa", "").lower()
    exp_store = expected.get("sklep_info", {}).get("nazwa", "").lower()
    if exp_store in pred_store or pred_store in exp_store:
        metrics["store_match"] = True

    # 2. Date
    pred_date = str(predicted.get("paragon_info", {}).get("data_zakupu", ""))
    exp_date = expected.get("paragon_info", {}).get("data_zakupu", "")
    # Simple string comparison for now (assuming YYYY-MM-DD)
    if pred_date.startswith(exp_date):
        metrics["date_match"] = True

    # 3. Total Amount
    pred_total = normalize_decimal(
        predicted.get("paragon_info", {}).get("suma_calkowita", 0)
    )
    exp_total = normalize_decimal(
        expected.get("paragon_info", {}).get("suma_calkowita", 0)
    )
    if abs(pred_total - exp_total) < 0.05:  # Tolerance 0.05
        metrics["total_match"] = True

    # 4. Items - porównywanie po post-processingu (rabaty już scalone)
    pred_items = predicted.get("pozycje", [])
    exp_items = expected.get("pozycje", [])

    if len(pred_items) == len(exp_items):
        metrics["items_count_match"] = True

    metrics["items_found"] = len(pred_items)

    # Check for matches (Name + Price + Discount)
    matched_pred_indices = set()
    
    for exp_item in exp_items:
        exp_name = exp_item.get("nazwa_raw", "").lower().strip()
        exp_price = normalize_decimal(exp_item.get("cena_po_rab", exp_item.get("cena_calk", 0)))
        exp_discount = normalize_decimal(exp_item.get("rabat", 0))

        best_match_idx = None
        best_match_score = 0

        for idx, pred_item in enumerate(pred_items):
            if idx in matched_pred_indices:
                continue
                
            pred_name = pred_item.get("nazwa_raw", "").lower().strip()
            pred_price = normalize_decimal(pred_item.get("cena_po_rab", pred_item.get("cena_calk", 0)))
            pred_discount = normalize_decimal(pred_item.get("rabat", 0))

            # Name matching (fuzzy)
            name_match = (
                exp_name in pred_name or 
                pred_name in exp_name or
                # Dla produktów z wagą - porównuj tylko część przed jednostką
                exp_name.split()[0] in pred_name or
                pred_name.split()[0] in exp_name
            )
            
            if not name_match:
                continue

            # Price matching (tolerancja 0.10 PLN)
            price_match = abs(exp_price - pred_price) < 0.10
            discount_match = abs(exp_discount - pred_discount) < 0.10

            # Score: name (2p) + price (2p) + discount (1p)
            score = 0
            if name_match:
                score += 2
                metrics["items_name_match"] += 1
            if price_match:
                score += 2
                metrics["items_price_match"] += 1
            if discount_match:
                score += 1
                metrics["items_discount_match"] += 1

            if score > best_match_score:
                best_match_score = score
                best_match_idx = idx

        # Perfect match = name + price + discount
        if best_match_idx is not None and best_match_score >= 5:
            metrics["items_perfect_match"] += 1
            matched_pred_indices.add(best_match_idx)

    return metrics


def run_evaluation(use_mistral_ocr: bool = True, use_post_processing: bool = True):
    """
    Uruchamia ewaluację na podstawie ground truth.
    
    Args:
        use_mistral_ocr: Jeśli True, używa Mistral OCR, w przeciwnym razie Tesseract
        use_post_processing: Jeśli True, uruchamia post-processing (strategie + weryfikacja matematyczna)
    """
    ground_truth = load_ground_truth()
    if not ground_truth:
        return

    print(f"Loaded ground truth for {len(ground_truth)} receipts.")
    print(f"Scanning images in: {IMAGES_DIR}")
    print(f"Using Mistral OCR: {use_mistral_ocr}")
    print(f"Using post-processing: {use_post_processing}")

    results = []

    for filename, expected_data in ground_truth.items():
        file_path = os.path.join(IMAGES_DIR, filename)
        if not os.path.exists(file_path):
            print(f"WARNING: File not found: {filename}. Skipping.")
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {filename}...")
        print(f"{'='*60}")

        try:
            # Obsługa PDF
            processing_file_path = file_path
            temp_image_path = None

            if file_path.lower().endswith(".pdf"):
                print("  Converting PDF to image...")
                temp_image_path = convert_pdf_to_image(file_path)
                if not temp_image_path:
                    print("  ERROR: PDF conversion failed.")
                    continue
                processing_file_path = temp_image_path

            # 1. OCR
            if use_mistral_ocr:
                print("  Using Mistral OCR...")
                mistral = MistralOCRClient()
                ocr_text = mistral.process_image(processing_file_path)
                if not ocr_text:
                    print("  ERROR: Mistral OCR failed.")
                    if temp_image_path:
                        os.remove(temp_image_path)
                    continue
                print(f"  OCR text length: {len(ocr_text)} chars")
            else:
                print("  Using Tesseract OCR...")
                ocr_text = extract_text_from_image(processing_file_path)
                if not ocr_text:
                    print("  ERROR: Tesseract OCR failed.")
                    if temp_image_path:
                        os.remove(temp_image_path)
                    continue

            # 2. Detekcja strategii
            header_sample = ocr_text[:1000] if ocr_text else ""
            strategy = get_strategy_for_store(header_sample)
            print(f"  Detected strategy: {strategy.__class__.__name__}")

            # 3. LLM Parsing
            print("  Parsing with LLM...")
            if use_mistral_ocr:
                # Używamy tekstowego modelu dla Mistral OCR
                predicted_data = parse_receipt_from_text(ocr_text)
            else:
                # Używamy wizyjnego modelu z OCR jako wsparciem
                system_prompt = strategy.get_system_prompt()
                predicted_data = parse_receipt_with_llm(
                    processing_file_path,
                    Config.VISION_MODEL,
                    system_prompt_override=system_prompt,
                    ocr_text=ocr_text,
                )

            if not predicted_data:
                print("  ERROR: LLM parsing failed.")
                if temp_image_path:
                    os.remove(temp_image_path)
                continue

            # 4. Post-processing (strategia + weryfikacja matematyczna)
            if use_post_processing:
                print("  Running post-processing...")
                predicted_data = strategy.post_process(predicted_data)
                
                # Weryfikacja matematyczna (mock log callback)
                def mock_log(msg):
                    pass  # Cichy log dla testów
                predicted_data = verify_math_consistency(predicted_data, mock_log)

            # 5. Compare
            print("  Comparing with ground truth...")
            metrics = compare_receipts(predicted_data, expected_data)
            metrics["filename"] = filename
            results.append(metrics)

            # 6. Wyświetlanie wyników
            print("\n  Results:")
            print(f"    Store Match:     {metrics['store_match']} ✓" if metrics['store_match'] else f"    Store Match:     {metrics['store_match']} ✗")
            print(f"    Date Match:      {metrics['date_match']} ✓" if metrics['date_match'] else f"    Date Match:      {metrics['date_match']} ✗")
            print(f"    Total Match:     {metrics['total_match']} ✓" if metrics['total_match'] else f"    Total Match:     {metrics['total_match']} ✗")
            print(f"    Items Count:     {metrics['items_found']}/{metrics['items_expected']} {'✓' if metrics['items_count_match'] else '✗'}")
            print(f"    Perfect Matches: {metrics['items_perfect_match']}/{metrics['items_expected']}")
            print(f"    Name Matches:    {metrics['items_name_match']}/{metrics['items_expected']}")
            print(f"    Price Matches:   {metrics['items_price_match']}/{metrics['items_expected']}")
            print(f"    Discount Matches: {metrics['items_discount_match']}/{metrics['items_expected']}")

            # Cleanup
            if temp_image_path and os.path.exists(temp_image_path):
                os.remove(temp_image_path)

        except Exception as e:
            print(f"  CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            if temp_image_path and os.path.exists(temp_image_path):
                os.remove(temp_image_path)

    # --- SUMMARY ---
    if not results:
        print("\nNo results to summarize.")
        return

    print(f"\n{'='*60}")
    print("=== EVALUATION SUMMARY ===")
    print(f"{'='*60}")
    
    total_receipts = len(results)
    perfect_totals = sum(1 for r in results if r["total_match"])
    perfect_dates = sum(1 for r in results if r["date_match"])
    perfect_stores = sum(1 for r in results if r["store_match"])
    
    total_items_expected = sum(r["items_expected"] for r in results)
    total_items_perfect = sum(r["items_perfect_match"] for r in results)
    total_items_name = sum(r["items_name_match"] for r in results)
    total_items_price = sum(r["items_price_match"] for r in results)
    total_items_discount = sum(r["items_discount_match"] for r in results)

    print(f"\nTotal Receipts: {total_receipts}")
    print(f"  Correct Totals: {perfect_totals}/{total_receipts} ({perfect_totals/total_receipts:.1%})")
    print(f"  Correct Dates:  {perfect_dates}/{total_receipts} ({perfect_dates/total_receipts:.1%})")
    print(f"  Correct Stores: {perfect_stores}/{total_receipts} ({perfect_stores/total_receipts:.1%})")
    
    print(f"\nItems Accuracy:")
    print(f"  Perfect Matches: {total_items_perfect}/{total_items_expected} ({total_items_perfect/total_items_expected:.1%})")
    print(f"  Name Matches:    {total_items_name}/{total_items_expected} ({total_items_name/total_items_expected:.1%})")
    print(f"  Price Matches:   {total_items_price}/{total_items_expected} ({total_items_price/total_items_expected:.1%})")
    print(f"  Discount Matches: {total_items_discount}/{total_items_expected} ({total_items_discount/total_items_expected:.1%})")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate receipt parsing accuracy")
    parser.add_argument(
        "--no-mistral",
        action="store_true",
        help="Use Tesseract OCR instead of Mistral OCR",
    )
    parser.add_argument(
        "--no-post-processing",
        action="store_true",
        help="Skip post-processing (strategies + math verification)",
    )
    
    args = parser.parse_args()
    
    run_evaluation(
        use_mistral_ocr=not args.no_mistral,
        use_post_processing=not args.no_post_processing,
    )
