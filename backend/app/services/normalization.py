"""
Service for data normalization (products, categories, units).
Enforces Polish language standards.
"""

import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None
    util = None

from app.models.product import Product, ProductAlias
from app.models.category import Category
from app.services.llm_service import ollama_client
from app.config import settings

logger = logging.getLogger(__name__)

# Global Embedding Model
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None and SentenceTransformer:
        try:
            logger.info("Loading sentence-transformers model...")
            # Using a lightweight multilingual model good for Polish
            _embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("Model loaded.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
    return _embedding_model

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


def normalize_product_name(db: Session, raw_name: str, shop_id: Optional[int] = None, create_threshold: float = 0.85) -> Tuple[Product, bool]:
    """
    Find or create a normalized product based on raw name.
    Uses Semantic Search (Embeddings) + LLM Verification.
    
    Args:
        db: Database session
        raw_name: Input product name from OCR
        shop_id: Optional shop ID for context
        create_threshold: Cosine similarity threshold to consider a match
        
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

    # 2. Semantic Search (Embeddings)
    model = get_embedding_model()
    if model:
        # Fetch all normalized product names (caching recommended for prod)
        existing_products = db.query(Product).all()
        
        if existing_products:
            # Prepare corpus
            corpus_names = [p.normalized_name for p in existing_products]
            corpus_embeddings = model.encode(corpus_names, convert_to_tensor=True)
            
            # Encode query
            query_embedding = model.encode(raw_name_clean, convert_to_tensor=True)
            
            # Find closest match
            # util.cos_sim returns query x corpus matrix
            hits = util.semantic_search(query_embedding, corpus_embeddings, top_k=1)
            
            if hits and hits[0]:
                top_hit = hits[0][0] # {corpus_id, score}
                score = top_hit['score']
                match_name = corpus_names[top_hit['corpus_id']]
                matched_product = existing_products[top_hit['corpus_id']]
                
                logger.info(f"Semantic match: '{raw_name_clean}' ~= '{match_name}' (score: {score:.4f})")
                
                # Decision Logic
                is_match = False
                
                if score > 0.92:
                    # High confidence -> Auto-match
                    is_match = True
                elif score > 0.65 and ollama_client:
                    # Ambiguous -> Ask LLM Judge
                    is_match = _llm_verify_match(raw_name_clean, match_name)
                    
                if is_match:
                    _create_alias(db, matched_product, raw_name_clean)
                    return matched_product, False

    # 3. No match -> Create New Product

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
            
            Zwróć TYLKO nazwę kategorii.
            NIE zwracaj kodu Python.
            NIE zwracaj definicji funkcji.
            """
            
            response = ollama_client.generate(
                model=settings.TEXT_MODEL,
                prompt=prompt,
                options={"temperature": 0.0}
            )
            cat_name = response.get("response", "").strip()
            
            # Cleanup response (remove quotes, dots, code blocks)
            cat_name = cat_name.replace('"', '').replace('.', '').replace('```python', '').replace('```', '').strip()

            # Strict validation against allowed categories
            allowed_categories = list(CATEGORY_KEYWORDS.keys()) + ["Inne"]
            
            # Check for exact match (case-insensitive)
            matched_cat = None
            for allowed in allowed_categories:
                if allowed.lower() == cat_name.lower():
                    matched_cat = allowed
                    break
            
            if matched_cat:
                return _assign_category_by_name(db, product, matched_cat)
            else:
                logger.warning(f"LLM returned invalid category '{cat_name}' for '{product.normalized_name}'. Fallback to 'Inne'.")
                return _assign_category_by_name(db, product, "Inne")
            
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

def _llm_verify_match(raw_name: str, candidate_name: str) -> bool:
    """Ask LLM if two products are the same type."""
    try:
        prompt = f"""
        Czy te dwie nazwy produktów z paragonów oznaczają ten sam rodzaj produktu?
        1. "{raw_name}"
        2. "{candidate_name}"
        
        Odpowiedz TYLKO słowem TAK lub NIE.
        """
        
        response = ollama_client.generate(
             model=settings.TEXT_MODEL,
             prompt=prompt,
             options={"temperature": 0.0}
        )
        answer = response.get("response", "").strip().upper()
        logger.info(f"LLM verification: '{raw_name}' vs '{candidate_name}' -> {answer}")
        return "TAK" in answer
    except Exception as e:
        logger.error(f"LLM verification failed: {e}")
        return False
