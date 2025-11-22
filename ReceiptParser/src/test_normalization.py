from normalization_rules import find_static_match


def test_rules():
    test_cases = [
        ("Mleko 3.2% Łaciate", "Mleko"),
        ("Kajzerka pszenna", "Bułka"),
        ("Chleb Baltonowski", "Chleb"),
        ("Serek wiejski Piątnica", "Ser Biały/Twaróg"),
        ("Coca Cola 0.5L", "Napój Gazowany"),
        ("Reklamówka", "POMIŃ"),
        ("Nieznany produkt 123", None),
        ("KawMiel", "Kawa"),
        ("SertMierzwGouda", "Ser Żółty"),
    ]

    print("--- Testowanie Reguł Normalizacji ---")
    passed = 0
    for raw, expected in test_cases:
        result = find_static_match(raw)
        status = "OK" if result == expected else "FAIL"
        if status == "OK":
            passed += 1
        print(f"[{status}] '{raw}' -> '{result}' (Oczekiwano: '{expected}')")

    print(f"\nWynik: {passed}/{len(test_cases)} testów zaliczonych.")


if __name__ == "__main__":
    test_rules()
