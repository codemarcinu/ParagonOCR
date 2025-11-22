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
    metrics = {
        "store_match": False,
        "date_match": False,
        "total_match": False,
        "items_count_match": False,
        "items_found": 0,
        "items_expected": len(expected.get("pozycje", [])),
        "items_perfect_match": 0,
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

    # 4. Items
    pred_items = predicted.get("pozycje", [])
    exp_items = expected.get("pozycje", [])

    if len(pred_items) == len(exp_items):
        metrics["items_count_match"] = True

    metrics["items_found"] = len(pred_items)

    # Check for perfect matches (Name + Price)
    for exp_item in exp_items:
        exp_name = exp_item.get("nazwa_raw", "").lower()
        exp_price = normalize_decimal(exp_item.get("cena_calk", 0))

        for pred_item in pred_items:
            pred_name = pred_item.get("nazwa_raw", "").lower()
            pred_price = normalize_decimal(pred_item.get("cena_calk", 0))

            # Loose name matching
            name_match = exp_name in pred_name or pred_name in exp_name
            price_match = abs(exp_price - pred_price) < 0.05

            if name_match and price_match:
                metrics["items_perfect_match"] += 1
                break

    return metrics


def run_evaluation():
    ground_truth = load_ground_truth()
    if not ground_truth:
        return

    print(f"Loaded ground truth for {len(ground_truth)} receipts.")
    print(f"Scanning images in: {IMAGES_DIR}")

    results = []

    for filename, expected_data in ground_truth.items():
        image_path = os.path.join(IMAGES_DIR, filename)
        if not os.path.exists(image_path):
            print(f"WARNING: Image not found: {filename}. Skipping.")
            continue

        print(f"\nProcessing: {filename}...")

        # --- PIPELINE SELECTION ---
        # For now, we use the Mistral OCR + LLM pipeline as it's the target
        try:
            # 1. OCR
            mistral = MistralOCRClient()
            ocr_text = mistral.process_image(image_path)
            if not ocr_text:
                print("  ERROR: OCR failed.")
                continue

            # 2. LLM Parsing
            predicted_data = parse_receipt_from_text(ocr_text)
            if not predicted_data:
                print("  ERROR: LLM parsing failed.")
                continue

            # 3. Compare
            metrics = compare_receipts(predicted_data, expected_data)
            metrics["filename"] = filename
            results.append(metrics)

            print("  Metrics:")
            print(f"    Store Match: {metrics['store_match']}")
            print(f"    Date Match:  {metrics['date_match']}")
            print(f"    Total Match: {metrics['total_match']}")
            print(
                f"    Items:       {metrics['items_found']}/{metrics['items_expected']} (Perfect: {metrics['items_perfect_match']})"
            )

        except Exception as e:
            print(f"  CRITICAL ERROR: {e}")

    # --- SUMMARY ---
    if not results:
        print("\nNo results to summarize.")
        return

    print("\n=== EVALUATION SUMMARY ===")
    total_receipts = len(results)
    perfect_totals = sum(1 for r in results if r["total_match"])
    perfect_dates = sum(1 for r in results if r["date_match"])
    perfect_stores = sum(1 for r in results if r["store_match"])

    print(f"Total Receipts: {total_receipts}")
    print(f"Correct Totals: {perfect_totals} ({perfect_totals/total_receipts:.1%})")
    print(f"Correct Dates:  {perfect_dates} ({perfect_dates/total_receipts:.1%})")
    print(f"Correct Stores: {perfect_stores} ({perfect_stores/total_receipts:.1%})")


if __name__ == "__main__":
    run_evaluation()
