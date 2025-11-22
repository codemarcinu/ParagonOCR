import re


def clean_raw_name_ocr(raw_name: str) -> str:
    """
    Usuwa typowe śmieci z paragonów przed właściwą normalizacją.
    Zachowuje oryginalną wielkość liter, aby uniknąć problemów z case-sensitive
    wyszukiwaniem w bazie danych.
    """
    name = raw_name  # Zachowujemy oryginalną wielkość liter

    # 1. Usuń kody podatkowe i znaki na końcu (np. " A", " B", " 23%")
    # Używamy case-insensitive match dla kodów podatkowych
    name = re.sub(r'\s+[ABCabc]\s*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+\d{1,2}%\s*$', '', name)

    # 2. Usuń "1 x " lub "1.000 x" z początku (częsty błąd OCR sklejania ilości z nazwą)
    name = re.sub(r'^\d+([.,]\d+)?\s*[xX*]\s*', '', name, flags=re.IGNORECASE)

    # 3. Usuń dziwne znaki na początku/końcu (np. kropki, przecinki, myślniki)
    name = name.strip(" .,-_*")

    # 4. Usuń słowa "RABAT", "PROMOCJA" jeśli są doklejone do nazwy
    # Case-insensitive match dla słów rabatowych
    name = re.sub(r'\s+(RABAT|PROMOCJA|UPUST|rabat|promocja|upust).*$', '', name, flags=re.IGNORECASE)

    return name


# Twardy słownik mapowania.
# Klucz: Znormalizowana nazwa (cel)
# Wartość: Lista wzorców REGEX, które mają "złapać" tę nazwę w surowym tekście.
# Kolejność ma znaczenie - bardziej szczegółowe reguły dawaj wyżej (jeśli iterujesz liniowo),
# ale w tym podejściu sprawdzamy każdą kategorię.

STATIC_RULES = {
    # --- PIECZYWO ---
    # Najpierw specyficzne
    "Bagietka": [r"bagietka", r"półbagietka", r"czosnkowa"],
    "Bułka": [
        r"bułka",
        r"bułki",
        r"kajzerka",
        r"grahamka",
        r"ciabatta",
        r"buł\.",
        r"pieczywo.*pszenne",
    ],
    "Chleb": [r"chleb", r"bochenek", r"baltonowski", r"razowy", r"żytni"],
    "Pączek": [r"pącz.*", r"donut", r"paczek"],
    # --- NABIAŁ ---
    "Mleko": [r"mleko", r"mlecz.*", r"uht"],
    "Masło": [r"masło", r"maslo", r"osełka", r"osełkowa"],
    # Najpierw specyficzne sery
    "Mozzarella": [r"mozzarella", r"mozarella"],
    "Ser Żółty": [
        r"ser.*gouda",
        r"ser.*edamski",
        r"ser.*podlaski",
        r"ser.*królewski",
        r"ser.*plastry",
        r"sert.*mierzw",
        r"ser.*morski",
    ],
    # Potem ogólne
    "Ser Biały/Twaróg": [
        r"twaróg",
        r"twarog",
        r"ser.*biały",
        r"serek.*wiejski",
        r"grani",
        r"bieluch",
    ],
    "Śmietana": [r"śmietana", r"smietana", r"śmietanka", r"smietanka", r"śmietan"],
    "Jogurt": [r"jogurt", r"jog\.", r"skyr", r"actimel", r"danone"],
    "Jajka": [r"jaja", r"jajka", r"wolny wybieg", r"ściółkowa"],
    # --- WARZYWA I OWOCE ---
    "Ziemniaki": [r"ziemnia.*", r"ziemniaki", r"wczesne"],
    "Pomidory": [r"pomidor", r"pom\.", r"cherry", r"gałązka", r"pomidory"],
    "Ogórki": [r"ogórek", r"ogorek", r"szklarniowy", r"gruntowy"],
    "Papryka": [r"papryka"],
    "Cebula": [r"cebula", r"dymka"],
    "Banany": [r"banan"],
    "Cytryna": [r"cytryna", r"cytryny"],
    "Jabłka": [r"jabłk.*", r"jablk.*", r"ligol", r"gala", r"jonagold", r"champion"],
    # --- MIĘSO I WĘDLINY ---
    "Kurczak": [r"kurczak", r"filet.*piersi", r"podudzie", r"skrzydełka", r"ćwiartka"],
    "Szynka": [r"szynka", r"szynkowa", r"konserwowa"],
    "Schab": [r"schab"],
    "Kiełbasa": [
        r"kiełbasa",
        r"kielbasa",
        r"śląska",
        r"podwawelska",
        r"żywiecka",
        r"kabanos",
    ],
    "Parówki": [r"parówki", r"berlinki", r"tarczyński"],
    # --- NAPOJE I ALKOHOL ---
    "Woda Mineralna": [
        r"woda",
        r"cisowianka",
        r"nałęczowianka",
        r"muszynianka",
        r"żywiec zdrój",
    ],
    "Sok": [r"sok\s", r"nektar", r"tymbark", r"hortex"],
    "Napój Gazowany": [
        r"coca.*cola",
        r"pepsi",
        r"fanta",
        r"sprite",
        r"oranżada",
        r"napój",
    ],
    "Piwo": [
        r"piwo",
        r"harnaś",
        r"tyskie",
        r"żubr",
        r"żywiec",
        r"heineken",
        r"piwo.*puszka",
        r"perła",
        r"łomża",
        r"carlsberg",
    ],
    "Wódka": [r"wódka", r"wodka", r"soplica", r"żołądkowa", r"wyborowa", r"bocian"],
    # --- SŁODYCZE I PRZEKĄSKI ---
    "Czekolada": [r"czekolada", r"milka", r"wedel", r"wawel", r"czek\."],
    "Baton": [r"baton", r"snickers", r"mars", r"prince polo", r"góralki"],
    "Chipsy": [r"chipsy", r"czipsy", r"lays", r"crunchips", r"wiejskie ziemniaczki"],
    # --- INNE ---
    "Kawa": [
        r"kawa",
        r"jacobs",
        r"nescafe",
        r"mk cafe",
        r"tchibo",
        r"lavazza",
        r"kawmiel",
    ],
    "Herbata": [r"herbata", r"lipton", r"saga", r"tetley", r"minutka"],
    "Cukier": [r"cukier"],
    "Mąka": [r"mąka", r"maka"],
    "Olej": [r"olej", r"kujawski"],
    "Ryż": [r"ryż", r"risana", r"sonko"],
    "Makaron": [r"makaron", r"lubella"],
    # --- OPŁATY I KAUCJE ---
    "Kaucja": [
        r"kaucja",
        r"butelka zwrotna",
        r"zwrot.*butelka",
        r"depozyt",
    ],
    "Opłata recyklingowa": [
        r"opłata.*recykling",
        r"recykling",
        r"bdo",
        r"oplrec",
    ],
    # --- ŚMIECI / OPŁATY (Ważne: mapujemy na 'POMIŃ' lub konkretną nazwę) ---
    "POMIŃ": [
        r"torba",
        r"reklamówka",
        r"siatka",  # Opakowania
        r"rabat",
        r"upust",  # Rabaty (często łapane przez logikę strategii, ale warto mieć)
        r"sprzedaż opodatkowana",
        r"ptu",
        r"suma pln",  # Śmieci z dołu paragonu
    ],
}


def find_static_match(raw_name: str) -> str | None:
    """
    Przeszukuje słownik STATIC_RULES w poszukiwaniu dopasowania dla raw_name.
    Zwraca znormalizowaną nazwę lub None.
    """
    raw_lower = raw_name.lower()

    for category, patterns in STATIC_RULES.items():
        for pattern in patterns:
            # Używamy re.search, żeby znaleźć wzorzec w środku nazwy
            if re.search(pattern, raw_lower):
                return category

    return None
