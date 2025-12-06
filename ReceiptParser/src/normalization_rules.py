"""
Multi-Stage Product Normalization Pipeline.

This module implements a 5-stage normalization pipeline for converting
raw product names from receipts into standardized product names.

Stages:
1. Cleanup OCR (100% coverage) - Remove tax codes, quantities, promo keywords
2. Static Rules (80% coverage) - Apply regex patterns from static_rules.json
3. Alias Lookup (15% coverage) - Fuzzy matching against expanded_products.json
4. LLM-based (4% coverage) - Query Ollama for normalization
5. User Confirmation (1% coverage) - Flag for manual confirmation in GUI
"""

import re
import json
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from rapidfuzz import fuzz

from .config import Config

logger = logging.getLogger(__name__)

# --- Legacy Functions (kept for backward compatibility) ---


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


# --- Multi-Stage Normalization Pipeline ---


class NormalizationPipeline:
    """
    Multi-stage normalization pipeline for product names.
    
    Implements 5 stages:
    1. Cleanup OCR (100% coverage)
    2. Static Rules (80% coverage)
    3. Alias Lookup (15% coverage)
    4. LLM-based (4% coverage)
    5. User Confirmation (1% coverage)
    
    Attributes:
        static_rules: Dictionary of normalized names to regex patterns
        products_data: List of products from expanded_products.json
        llm_client: Optional LLM client for stage 4
    """
    
    def __init__(
        self,
        static_rules_path: Optional[Path] = None,
        products_json_path: Optional[Path] = None,
        llm_client: Optional[object] = None
    ):
        """
        Initialize the normalization pipeline.
        
        Args:
            static_rules_path: Optional path to static_rules.json
            products_json_path: Optional path to expanded_products.json
            llm_client: Optional LLM client for stage 4 normalization
        """
        self.static_rules: Dict[str, List[Dict[str, float]]] = {}
        self.products_data: List[Dict] = []
        self.llm_client = llm_client
        
        # Load static rules
        self._load_static_rules(static_rules_path)
        
        # Load products data
        self._load_products_data(products_json_path)
    
    def _load_static_rules(self, static_rules_path: Optional[Path]) -> None:
        """
        Load static rules from JSON file or use default STATIC_RULES.
        
        Args:
            static_rules_path: Optional path to static_rules.json
        """
        if static_rules_path and static_rules_path.exists():
            try:
                with open(static_rules_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert to format: {normalized_name: [{regex: str, confidence: float}]}
                    for rule in data.get('rules', []):
                        normalized_name = rule.get('normalized_name')
                        patterns = rule.get('patterns', [])
                        self.static_rules[normalized_name] = patterns
                logger.info(f"Loaded {len(self.static_rules)} static rules from {static_rules_path}")
            except Exception as e:
                logger.warning(f"Failed to load static_rules.json: {e}. Using default STATIC_RULES.")
                self._load_default_static_rules()
        else:
            self._load_default_static_rules()
    
    def _load_default_static_rules(self) -> None:
        """Load default STATIC_RULES dictionary."""
        for normalized_name, patterns in STATIC_RULES.items():
            # Convert to format: [{regex: str, confidence: float}]
            self.static_rules[normalized_name] = [
                {'regex': pattern, 'confidence': 0.90}  # Default confidence
                for pattern in patterns
            ]
        logger.info(f"Loaded {len(self.static_rules)} default static rules")
    
    def _load_products_data(self, products_json_path: Optional[Path]) -> None:
        """
        Load products data from expanded_products.json.
        
        Args:
            products_json_path: Optional path to expanded_products.json
        """
        if products_json_path is None:
            # Try default path
            project_root = Path(__file__).parent.parent.parent
            products_json_path = project_root / "ReceiptParser" / "data" / "expanded_products.json"
        
        if products_json_path and products_json_path.exists():
            try:
                with open(products_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.products_data = data.get('produkty', [])
                logger.info(f"Loaded {len(self.products_data)} products from {products_json_path}")
            except Exception as e:
                logger.warning(f"Failed to load expanded_products.json: {e}")
                self.products_data = []
        else:
            logger.warning(f"expanded_products.json not found at {products_json_path}")
            self.products_data = []
    
    def normalize(self, raw_name: str) -> Tuple[str, float]:
        """
        Normalize a raw product name through all 5 stages.
        
        Args:
            raw_name: Raw product name from receipt
            
        Returns:
            Tuple of (normalized_name, confidence_score) where confidence is 0.0-1.0
        """
        # Stage 1: Cleanup OCR (100% coverage)
        cleaned_name = self._cleanup_ocr(raw_name)
        
        # Stage 2: Static Rules (80% coverage)
        normalized, confidence = self._apply_static_rules(cleaned_name)
        if normalized and confidence >= 0.80:
            return normalized, confidence
        
        # Stage 3: Alias Lookup (15% coverage)
        normalized, confidence = self._check_aliases(cleaned_name)
        if normalized and confidence >= 0.60:
            return normalized, confidence
        
        # Stage 4: LLM-based (4% coverage)
        if self.llm_client:
            normalized, confidence = self._llm_normalize(cleaned_name)
            if normalized and confidence >= 0.40:
                return normalized, confidence
        
        # Stage 5: User Confirmation (1% coverage)
        # Return with low confidence to flag for manual confirmation
        return cleaned_name, 0.20
    
    def _cleanup_ocr(self, name: str) -> str:
        """
        Stage 1: Cleanup OCR artifacts.
        
        Operations:
        - Remove tax codes (A, B, C suffix)
        - Remove quantities (1x, 2.5x)
        - Remove promo keywords (RABAT, PROMOCJA)
        - Normalize whitespace
        - Remove duplicate words
        - Convert to title case
        
        Args:
            name: Raw product name
            
        Returns:
            Cleaned product name
        """
        # Use existing cleanup function
        cleaned = clean_raw_name_ocr(name)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove duplicate words (case-insensitive)
        words = cleaned.split()
        seen = set()
        unique_words = []
        for word in words:
            word_lower = word.lower()
            if word_lower not in seen:
                seen.add(word_lower)
                unique_words.append(word)
        cleaned = ' '.join(unique_words)
        
        # Convert to title case (but preserve acronyms)
        cleaned = cleaned.title()
        
        return cleaned
    
    def _apply_static_rules(self, name: str) -> Tuple[Optional[str], float]:
        """
        Stage 2: Apply static regex rules.
        
        Args:
            name: Cleaned product name
            
        Returns:
            Tuple of (normalized_name, confidence) or (None, 0.0)
        """
        name_lower = name.lower()
        
        best_match = None
        best_confidence = 0.0
        
        for normalized_name, patterns in self.static_rules.items():
            for pattern_data in patterns:
                if isinstance(pattern_data, dict):
                    regex_pattern = pattern_data.get('regex', '')
                    confidence = pattern_data.get('confidence', 0.90)
                else:
                    # Backward compatibility: pattern_data is just a string
                    regex_pattern = pattern_data
                    confidence = 0.90
                
                try:
                    if re.search(regex_pattern, name_lower, re.IGNORECASE):
                        if confidence > best_confidence:
                            best_match = normalized_name
                            best_confidence = confidence
                except re.error:
                    logger.warning(f"Invalid regex pattern: {regex_pattern}")
                    continue
        
        if best_match:
            return best_match, best_confidence
        
        return None, 0.0
    
    def _check_aliases(self, name: str) -> Tuple[Optional[str], float]:
        """
        Stage 3: Check aliases using fuzzy matching.
        
        Uses rapidfuzz.fuzz.partial_ratio() for fuzzy string matching.
        
        Args:
            name: Cleaned product name
            
        Returns:
            Tuple of (normalized_name, confidence) or (None, 0.0)
        """
        if not self.products_data:
            return None, 0.0
        
        best_match = None
        best_score = 0.0
        threshold = 60.0  # Minimum similarity score (0-100)
        
        name_lower = name.lower()
        
        for product in self.products_data:
            normalized_name = product.get('znormalizowana_nazwa', '')
            aliases = product.get('aliases', [])
            
            # Check against normalized name
            score = fuzz.partial_ratio(name_lower, normalized_name.lower())
            if score > best_score:
                best_match = normalized_name
                best_score = score
            
            # Check against aliases
            for alias in aliases:
                score = fuzz.partial_ratio(name_lower, alias.lower())
                if score > best_score:
                    best_match = normalized_name
                    best_score = score
        
        if best_match and best_score >= threshold:
            # Convert score (0-100) to confidence (0.0-1.0)
            confidence = best_score / 100.0
            return best_match, confidence
        
        return None, 0.0
    
    def _llm_normalize(self, name: str) -> Tuple[Optional[str], float]:
        """
        Stage 4: LLM-based normalization.
        
        Queries Ollama with product normalization prompt.
        
        Args:
            name: Cleaned product name
            
        Returns:
            Tuple of (normalized_name, confidence) or (None, 0.0)
        """
        if not self.llm_client:
            return None, 0.0
        
        try:
            prompt = f"""Jesteś wirtualnym magazynierem. Twoim zadaniem jest zamiana nazwy z paragonu na KRÓTKIE, GENERYCZNE nazwy produktów do domowej spiżarni.

ZASADY KRYTYCZNE:
1. USUWASZ marki (np. "Krakus", "Mlekovita", "Winiary" -> USUŃ).
2. USUWASZ gramaturę i opakowania (np. "1L", "500g", "butelka", "szt" -> USUŃ).
3. USUWASZ przymiotniki marketingowe (np. "tradycyjne", "babuni", "pyszne", "luksusowe" -> USUŃ).
4. Zmieniasz na Mianownik Liczby Pojedynczej (np. "Bułki" -> "Bułka", "Jaja" -> "Jajka").
5. Jeśli produkt to plastikowa torba/reklamówka, zwróć dokładnie słowo: "POMIŃ".

Zwróć TYLKO znormalizowaną nazwę, bez dodatkowych wyjaśnień.

Nazwa z paragonu: {name}
Znormalizowana nazwa:"""
            
            # Use LLM client to generate response
            # Assuming llm_client has a generate method
            if hasattr(self.llm_client, 'generate'):
                response = self.llm_client.generate(prompt)
            elif hasattr(self.llm_client, 'chat'):
                # Try chat interface
                response = self.llm_client.chat(
                    model=Config.TEXT_MODEL,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                if isinstance(response, dict):
                    response = response.get('message', {}).get('content', '')
            else:
                # Try ollama client interface
                import ollama
                response_obj = ollama.generate(
                    model=Config.TEXT_MODEL,
                    prompt=prompt
                )
                response = response_obj.get('response', '')
            
            if response:
                normalized = response.strip()
                # Remove quotes if present
                normalized = normalized.strip('"\'')
                
                # Confidence based on response quality
                confidence = 0.70 if len(normalized) > 0 and len(normalized) < 50 else 0.50
                
                return normalized, confidence
            
        except Exception as e:
            logger.warning(f"LLM normalization failed for '{name}': {e}")
        
        return None, 0.0
    
    def get_confidence_level(self, score: float) -> str:
        """
        Get human-readable confidence level from score.
        
        Args:
            score: Confidence score (0.0-1.0)
            
        Returns:
            Confidence level string:
            - "certain" (0.95+)
            - "high" (0.80-0.95)
            - "medium" (0.60-0.80)
            - "low" (0.40-0.60)
            - "needs_confirmation" (<0.40)
        """
        if score >= 0.95:
            return "certain"
        elif score >= 0.80:
            return "high"
        elif score >= 0.60:
            return "medium"
        elif score >= 0.40:
            return "low"
        else:
            return "needs_confirmation"
