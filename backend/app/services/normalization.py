"""
Service for data normalization (products, categories, units).
Enforces Polish language standards.
"""

import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from thefuzz import fuzz, process
except ImportError:
    import warnings
    warnings.warn("thefuzz not installed, fuzzy matching will be disabled")
    fuzz = None
    process = None

from app.models.product import Product, ProductAlias
from app.models.category import Category
from app.services.llm_service import ollama_client
from app.config import settings

logger = logging.getLogger(__name__)

# Standard Unit Map (Polish)
UNIT_MAP = {
    "szt": ["szt", "szt.", "sztuka", "st", "st.", "op", "op.", "opak", "opak.", "kpl", "kpl."],
    "kg": ["kg", "kg.", "kilogram"],
    "g": ["g", "g.", "gram", "gr"],
    "l": ["l", "l.", "litr"],
    "ml": ["ml", "ml.", "mililitr"],
}

# Reverse map for O(1) lookup
NORMALIZED_UNITS = {}
for standard, variants in UNIT_MAP.items():
    for v in variants:
        NORMALIZED_UNITS[v.lower()] = standard

# Common Category Keywords (Polish) for fast-path classification
CATEGORY_KEYWORDS = {
    "Nabiał": ["mleko", "ser", "jogurt", "masło", "śmietana", "kefir", "twaróg"],
    "Pieczywo": ["chleb", "bułka", "bagietka", "kajzerka", "rogal"],
    "Owoce i Warzywa": ["jabłko", "banan", "ziemniaki", "pomidor", "ogórek", "cebula", "marchew"],
    "Mięso i Wędliny": ["schab", "szynka", "kiełbasa", "kurczak", "filet", "mięso", "parówki"],
    "Napoje": ["woda", "sok", "napój", "pepsi", "cola", "fanta", "sprite", "piwo"],
    "Słodycze": ["czekolada", "baton", "ciastko", "wafel", "cukierek", "lody"],
    "Chemia i Kosmetyki": ["mydło", "szampon", "płyn", "proszek", "papier", "chusteczki"],
    "Alkohol": ["wódka", "wino", "piwo", "whisky"],
}

def normalize_unit(raw_unit: Optional[str]) -> Optional[str]:
    """
    Normalize unit string to standard Polish unit (e.g., 'szt.', 'st' -> 'szt').
    """
    if not raw_unit:
        return None
    
    clean = raw_unit.lower().strip().replace(" ", "")
    return NORMALIZED_UNITS.get(clean, raw_unit) # Return raw if no match


def simple_polish_stemmer(word: str) -> str:
    """
    Very basic Polish stemmer to unify word forms.
    Removes common suffixes.
    """
    word = word.lower().strip()
    if len(word) < 4:
        return word
        
    suffixes = ["ego", "emu", "ym", "ych", "ymi", "iem", "ami", "ach", "om", "ow", "ów", "owie", "rzy", "rzy", "szy", "szy", "sze", "sze", "sza"]
    # Single char suffixes (check last)
    simple_suffixes = ["a", "e", "i", "o", "y", "ą", "ę", "ł"]
    
    for s in suffixes:
        if word.endswith(s):
            return word[:-len(s)]
            
    for s in simple_suffixes:
        if word.endswith(s):
            return word[:-len(s)]
            
    return word

def stem_sentence(sentence: str) -> str:
    """Apply stemming to all words in a sentence."""
    return " ".join([simple_polish_stemmer(w) for w in sentence.split()])


def normalize_product_name(db: Session, raw_name: str, create_threshold: int = 88) -> Tuple[Product, bool]:
    """
    Find or create a normalized product based on raw name.
    Uses fuzzy matching to avoid duplicates.
    
    Returns:
        (Product, is_new): The product object and a boolean indicating if it was newly created.
    """
    if not raw_name:
        return None, False
        
    raw_name_clean = raw_name.strip()
    
    # 1. Exact match on Alias
    alias = db.query(ProductAlias).filter(ProductAlias.raw_name == raw_name_clean).first()
    if alias:
        logger.info(f"Alias match: '{raw_name_clean}' -> '{alias.product.normalized_name}'")
        return alias.product, False

    # 2. Fuzzy match against existing Aliases (expensive if many, but we catch duplicates)
    # Optimization: Loading all aliases might be heavy. For now, we'll try a simpler approach 
    # or rely on exact match if DB gets huge.
    # To be safe/fast, let's skip full DB fuzzy scan for now and rely on exact match,
    # UNLESS the user explicitly wants full dedupe.
    # Implementation Plan requested fuzzy matching. We can do it on 'normalized_name' of Products.
    
    if fuzz: # Only if installed
        # Get all normalized names (caching this in mem would be better for prod)
        existing_products = db.query(Product).all()
        
        # Prepare choices: list of (orig_name, stemmed_name, product_obj)
        # This is n^2 complexity effectively if we scan everything, but for small DB ok.
        # Let's map normalized names.
        
        # Apply stemming to query
        query_stemmed = stem_sentence(raw_name_clean)
        
        choices = {p.normalized_name: p for p in existing_products}
        choices_stemmed = {stem_sentence(name): name for name in choices.keys()}
        
        # 2a. Try stemming match first (exact match on stemmed)
        if query_stemmed in choices_stemmed:
            original_match = choices_stemmed[query_stemmed]
            matched_product = choices[original_match]
            logger.info(f"Stemming match: '{raw_name_clean}' ({query_stemmed}) -> '{original_match}'")
            
            # Create alias
            _create_alias(db, matched_product, raw_name_clean)
            return matched_product, False
            
        # 2b. Fuzzy match
        if choices:
            # Match against stemmed versions for better results? Or original?
            # Let's match against original normalized names for now to keep it simple,
            # or stemmed if original fails.
            
            match, score = process.extractOne(raw_name_clean, list(choices.keys()), scorer=fuzz.token_sort_ratio)
            
            if score >= create_threshold:
                logger.info(f"Fuzzy match found: '{raw_name_clean}' ~= '{match}' (score: {score})")
                # Found a close match, allow it but create a NEW ALIAS for the existing product
                matched_product = choices[match]
                
                # Create alias linking this raw name to existing product
                _create_alias(db, matched_product, raw_name_clean)
                return matched_product, False

    # 3. No match -> Create New Product
    # Create Product
    new_product = Product(normalized_name=raw_name_clean)
    db.add(new_product)
    db.flush() # Get ID
    
    # Create Alias
    _create_alias(db, new_product, raw_name_clean)
    
    logger.info(f"Created new product: '{raw_name_clean}'")
    return new_product, True


def _create_alias(db: Session, product: Product, raw_name: str):
    """Helper to create alias if it doesn't exist."""
    exists = db.query(ProductAlias).filter(
        ProductAlias.product_id == product.id,
        ProductAlias.raw_name == raw_name
    ).first()
    
    if not exists:
        new_alias = ProductAlias(product_id=product.id, raw_name=raw_name)
        db.add(new_alias)
        db.flush()


def learn_product_alias(db: Session, raw_name: str, correct_product_id: int):
    """
    Explicitly learn a new alias for a product (e.g. from UI correction).
    """
    product = db.query(Product).filter(Product.id == correct_product_id).first()
    if not product:
        logger.error(f"Cannot learn alias: Product {correct_product_id} not found")
        return
        
    _create_alias(db, product, raw_name)
    logger.info(f"Learned alias: '{raw_name}' -> '{product.normalized_name}'")


def classify_product_category(db: Session, product: Product) -> Optional[int]:
    """
    Determine category for a product using Keywords first, then LLM.
    Updates the product.category_id field.
    """
    if not product or not product.normalized_name:
        return None
        
    name_lower = product.normalized_name.lower()
    
    # 1. Keyword Check
    for cat_name, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return _assign_category_by_name(db, product, cat_name)
            
    # 2. LLM Fallback
    if ollama_client and settings.TEXT_MODEL:
        try:
            logger.info(f"Asking LLM to categorize: {product.normalized_name}")
            prompt = f"""
            Zaklasyfikuj produkt do jednej z poniższych kategorii.
            Produkt: "{product.normalized_name}"
            
            Dostępne kategorie:
            - Nabiał
            - Pieczywo
            - Owoce i Warzywa
            - Mięso i Wędliny
            - Napoje
            - Słodycze
            - Chemia i Kosmetyki
            - Alkohol
            - Inne
            
            Zwróć TYLKO nazwę kategorii, nic więcej.
            """
            
            response = ollama_client.generate(
                model=settings.TEXT_MODEL,
                prompt=prompt,
                options={"temperature": 0.0}
            )
            cat_name = response.get("response", "").strip()
            
            # Cleanup response (remove quotes, dots)
            cat_name = cat_name.replace('"', '').replace('.', '').strip()
            
            # Validate against our list (optional, but safer to match DB)
            return _assign_category_by_name(db, product, cat_name)
            
        except Exception as e:
            logger.error(f"LLM Categorization failed: {e}")
            return None
            
    return None

def _assign_category_by_name(db: Session, product: Product, category_name: str) -> Optional[int]:
    """Helper to find/create category and assign to product."""
    if not category_name:
        return None
        
    # Find existing
    category = db.query(Category).filter(Category.name == category_name).first()
    
    if not category:
        # Create new category
        category = Category(name=category_name)
        db.add(category)
        db.flush()
        
    product.category_id = category.id
    return category.id
