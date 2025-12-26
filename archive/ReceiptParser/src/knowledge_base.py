# src/knowledge_base.py

import re

# --- SŁOWNIK SKLEPÓW ---
# Klucz: Znormalizowana nazwa sklepu
# Wartość: Lista wzorców REGEX, które identyfikują ten sklep w nagłówku paragonu
SHOP_PATTERNS = {
    "Biedronka": [r"biedronka", r"jeronimo martins", r"sklep\s*\d+", r"kostrzyn"],
    "Lidl": [r"lidl", r"sp\.\s*z\s*o\.o\.\s*sp\.\s*k\.", r"jankowice"],
    "Auchan": [r"auchan"],
    "Kaufland": [r"kaufland"],
    "Carrefour": [r"carrefour", r"kerfur"],
    "Żabka": [r"żabka", r"zabka"],
    "Dino": [r"dino"],
    "Netto": [r"netto"],
    "Stokrotka": [r"stokrotka"],
    "Rossmann": [r"rossmann"],
    "Hebe": [r"hebe", r"drogeria"],
    "Orlen": [r"orlen", r"pkn"],
    "Shell": [r"shell"],
    "McDonald's": [r"mcdonald", r"mc\s*donald"],
}

# --- METADANE PRODUKTÓW (KATEGORIA + MROŻENIE) ---
# Klucz: Znormalizowana nazwa produktu (musi pasować do tej z normalization_rules.py!)
# Wartość: Słownik z kategorią i flagą can_freeze
# can_freeze: True (tak), False (nie), "Conditional" (tak, ale...)

PRODUCT_METADATA = {
    # --- PIECZYWO ---
    "Bułka": {"kategoria": "Pieczywo", "can_freeze": True},
    "Chleb": {"kategoria": "Pieczywo", "can_freeze": True},
    "Pączek": {
        "kategoria": "Pieczywo",
        "can_freeze": True,
    },  # Najlepiej bez lukru, ale da się
    "Bagietka": {"kategoria": "Pieczywo", "can_freeze": True},
    # --- NABIAŁ ---
    "Mleko": {
        "kategoria": "Nabiał",
        "can_freeze": True,
    },  # Ale może się rozwarstwić, ok do gotowania
    "Masło": {"kategoria": "Nabiał", "can_freeze": True},
    "Ser Żółty": {"kategoria": "Nabiał", "can_freeze": True},  # Może stać się kruchy
    "Ser Biały/Twaróg": {
        "kategoria": "Nabiał",
        "can_freeze": True,
    },  # Zmienia konsystencję
    "Śmietana": {"kategoria": "Nabiał", "can_freeze": False},  # Rozwarstwia się, słabe
    "Jogurt": {"kategoria": "Nabiał", "can_freeze": False},  # Traci konsystencję
    "Jajka": {"kategoria": "Nabiał", "can_freeze": False},  # W skorupkach NIE! (pękną)
    # --- WARZYWA I OWOCE ---
    "Ziemniaki": {
        "kategoria": "Warzywa",
        "can_freeze": False,
    },  # Surowe robią się słodkie i papkowate
    "Pomidory": {
        "kategoria": "Warzywa",
        "can_freeze": True,
    },  # Tylko na zupę/sos, tracą jędrność
    "Ogórki": {"kategoria": "Warzywa", "can_freeze": False},  # Robią się ciapowate
    "Papryka": {"kategoria": "Warzywa", "can_freeze": True},
    "Cebula": {"kategoria": "Warzywa", "can_freeze": True},
    "Banany": {"kategoria": "Owoce", "can_freeze": True},  # Super na lody/koktajle
    "Cytryna": {"kategoria": "Owoce", "can_freeze": True},  # W plastrach lub sok
    "Jabłka": {
        "kategoria": "Owoce",
        "can_freeze": True,
    },  # Najlepiej jako mus lub blanszowane
    # --- MIĘSO I WĘDLINY ---
    "Kurczak": {"kategoria": "Mięso", "can_freeze": True},
    "Szynka": {"kategoria": "Wędliny", "can_freeze": True},
    "Schab": {"kategoria": "Mięso", "can_freeze": True},
    "Kiełbasa": {"kategoria": "Wędliny", "can_freeze": True},
    "Parówki": {"kategoria": "Wędliny", "can_freeze": True},
    "Mięso Mielone": {"kategoria": "Mięso", "can_freeze": True},
    "Ryba": {"kategoria": "Ryby", "can_freeze": True},
    # --- NAPOJE I ALKOHOL ---
    "Woda Mineralna": {
        "kategoria": "Napoje",
        "can_freeze": True,
    },  # Ale butelka może pęknąć!
    "Sok": {"kategoria": "Napoje", "can_freeze": True},
    "Napój Gazowany": {
        "kategoria": "Napoje",
        "can_freeze": False,
    },  # Wybuchnie w zamrażarce
    "Piwo": {"kategoria": "Alkohol", "can_freeze": False},  # Puszka/butelka pęknie
    "Wódka": {
        "kategoria": "Alkohol",
        "can_freeze": True,
    },  # Nie zamarznie w domowej zamrażarce (gęstnieje)
    # --- SŁODYCZE I PRZEKĄSKI ---
    "Czekolada": {"kategoria": "Słodycze", "can_freeze": True},
    "Baton": {"kategoria": "Słodycze", "can_freeze": True},
    "Chipsy": {"kategoria": "Przekąski", "can_freeze": True},  # Tak! Pozostają chrupkie
    # --- SYPKIE / INNE ---
    "Kawa": {"kategoria": "Inne", "can_freeze": True},  # Ziarna tak, zachowują aromat
    "Herbata": {"kategoria": "Inne", "can_freeze": True},
    "Cukier": {"kategoria": "Inne", "can_freeze": False},  # Zbędne
    "Mąka": {"kategoria": "Sypkie", "can_freeze": True},  # Zabija mole spożywcze!
    "Olej": {"kategoria": "Tłuszcze", "can_freeze": True},
    "Ryż": {"kategoria": "Sypkie", "can_freeze": False},  # Surowy zbędne, ugotowany tak
    "Makaron": {"kategoria": "Sypkie", "can_freeze": False},  # Surowy zbędne
    # --- OPŁATY I KAUCJE ---
    "Kaucja": {"kategoria": "Inne", "can_freeze": False},
    "Opłata recyklingowa": {"kategoria": "Inne", "can_freeze": False},
}


def get_product_metadata(normalized_name: str):
    """
    Zwraca metadane dla produktu (kategoria, info o mrożeniu).
    Jeśli produkt nie istnieje w bazie wiedzy, zwraca domyślne 'Inne' i 'Nieznane'.
    """
    return PRODUCT_METADATA.get(
        normalized_name, {"kategoria": "Inne", "can_freeze": None}
    )


def normalize_shop_name(raw_header_text: str) -> str:
    """
    Próbuje dopasować nazwę sklepu na podstawie nagłówka paragonu (OCR).
    """
    raw_lower = raw_header_text.lower()
    for shop_name, patterns in SHOP_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, raw_lower):
                return shop_name
    return "Nieznany Sklep"
