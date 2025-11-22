# verify_knowledge.py
import sys
import os

# Dodaj ścieżkę do modułów (scripts/ jest w głównym katalogu, ReceiptParser/src/ też)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ReceiptParser', 'src'))

try:
    from knowledge_base import get_product_metadata, normalize_shop_name

    print("✅ Successfully imported knowledge_base")
except ImportError as e:
    print(f"❌ Failed to import knowledge_base: {e}")
    sys.exit(1)


def test_normalization():
    print("\n--- Testing Shop Normalization ---")
    test_cases = [
        ("PARAGON FISKALNY SKLEP 3218 TARGOWA", "Biedronka"),
        ("LIDL sp. z o.o. sp. k.", "Lidl"),
        ("Zabka Polska", "Żabka"),
        ("Unknown Shop", "Nieznany Sklep"),
    ]

    for header, expected in test_cases:
        result = normalize_shop_name(header)
        status = "✅" if result == expected else f"❌ (Expected {expected})"
        print(f"{status} Header: '{header}' -> Result: '{result}'")


def test_metadata():
    print("\n--- Testing Product Metadata ---")
    test_cases = [
        ("Mleko", "Nabiał", True),
        ("Śmietana", "Nabiał", False),
        ("Kurczak", "Mięso", True),
        ("Nieznany Produkt", "Inne", None),
    ]

    for name, expected_cat, expected_freeze in test_cases:
        meta = get_product_metadata(name)
        cat = meta["kategoria"]
        freeze = meta["can_freeze"]

        cat_status = "✅" if cat == expected_cat else f"❌ (Expected {expected_cat})"
        freeze_status = (
            "✅" if freeze == expected_freeze else f"❌ (Expected {expected_freeze})"
        )

        print(f"Product: '{name}'")
        print(f"  {cat_status} Category: {cat}")
        print(f"  {freeze_status} Can Freeze: {freeze}")


if __name__ == "__main__":
    test_normalization()
    test_metadata()
    print("\n✅ Verification Complete")
