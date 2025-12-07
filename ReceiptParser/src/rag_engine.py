"""
RAG Search Engine for ParagonOCR 2.0

Provides retrieval-augmented generation search capabilities for products
with fuzzy matching, semantic search, and temporal ranking.

Author: ParagonOCR Team
Version: 2.0
"""

from typing import List, Dict, Optional, Tuple
from datetime import date, timedelta
from sqlalchemy.orm import Session, joinedload
from rapidfuzz import fuzz
import logging

from .database import Produkt, StanMagazynowy, AliasProduktu, KategoriaProduktu

logger = logging.getLogger(__name__)


class RAGSearchEngine:
    """
    RAG Search Engine for product retrieval.
    
    Combines fuzzy matching, semantic search, and temporal ranking
    to provide relevant product search results for AI chat context.
    
    Attributes:
        session: SQLAlchemy database session
    """
    
    def __init__(self, session: Session) -> None:
        """
        Initialize the RAG search engine.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
    
    def search(
        self,
        query: str,
        limit: int = 15
    ) -> List[Dict]:
        """
        Search for products using multi-factor ranking.
        
        Combines:
        - Factor 1: Fuzzy matching on names (weight: 0.4)
        - Factor 2: Semantic search on categories/tags (weight: 0.3)
        - Factor 3: Temporal ranking - expiry, frequency (weight: 0.3)
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of product dictionaries with scores, sorted by relevance
        """
        if not query or not query.strip():
            return []
        
        query_lower = query.lower().strip()
        
        # Get all available products with inventory
        products = self._get_available_products()
        
        if not products:
            return []
        
        # Calculate scores for each product
        scored_products = []
        for product in products:
            # Factor 1: Fuzzy matching on names (weight: 0.4)
            fuzzy_score = self._fuzzy_search(query_lower, product)
            fuzzy_weighted = fuzzy_score * 0.4
            
            # Factor 2: Semantic search on categories/tags (weight: 0.3)
            semantic_score = self._semantic_search(query_lower, product)
            semantic_weighted = semantic_score * 0.3
            
            # Factor 3: Temporal ranking (weight: 0.3)
            temporal_score = self._rank_results([product])[0]["temporal_score"] if self._rank_results([product]) else 0.0
            temporal_weighted = temporal_score * 0.3
            
            # Combined score
            combined_score = fuzzy_weighted + semantic_weighted + temporal_weighted
            
            product["search_score"] = combined_score
            product["fuzzy_score"] = fuzzy_score
            product["semantic_score"] = semantic_score
            product["temporal_score"] = temporal_score
            
            scored_products.append(product)
        
        # Sort by combined score (descending)
        scored_products.sort(key=lambda x: x["search_score"], reverse=True)
        
        # Return top N results
        return scored_products[:limit]
    
    def _fuzzy_search(
        self,
        query: str,
        product: Dict
    ) -> float:
        """
        Perform fuzzy matching on product names.
        
        Uses rapidfuzz.fuzz.partial_ratio() for fuzzy string matching.
        
        Args:
            query: Search query (lowercase)
            product: Product dictionary with 'nazwa' key
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        product_name = product.get("nazwa", "").lower()
        
        if not product_name:
            return 0.0
        
        # Check main name
        main_ratio = fuzz.partial_ratio(query, product_name) / 100.0
        
        # Check aliases
        aliases = product.get("aliases", [])
        alias_ratios = []
        for alias in aliases:
            alias_ratio = fuzz.partial_ratio(query, alias.lower()) / 100.0
            alias_ratios.append(alias_ratio)
        
        # Take the best match (main name or best alias)
        best_alias_ratio = max(alias_ratios) if alias_ratios else 0.0
        best_ratio = max(main_ratio, best_alias_ratio)
        
        return best_ratio
    
    def _semantic_search(
        self,
        query: str,
        product: Dict
    ) -> float:
        """
        Perform semantic search on categories, tags, and aliases.
        
        Searches database categories, tags, and aliases for semantic matches.
        
        Args:
            query: Search query (lowercase)
            product: Product dictionary
            
        Returns:
            Semantic match score (0.0 to 1.0)
        """
        score = 0.0
        
        # Check category
        category = product.get("kategoria", "").lower()
        if category and query in category:
            score += 0.5
        elif category:
            # Partial match in category
            category_ratio = fuzz.partial_ratio(query, category) / 100.0
            if category_ratio > 0.5:
                score += category_ratio * 0.5
        
        # Check tags (if available in future product metadata)
        tags = product.get("tags", [])
        for tag in tags:
            tag_lower = tag.lower()
            if query in tag_lower:
                score += 0.3
                break
            tag_ratio = fuzz.partial_ratio(query, tag_lower) / 100.0
            if tag_ratio > 0.6:
                score += tag_ratio * 0.2
                break
        
        # Check aliases for semantic matches
        aliases = product.get("aliases", [])
        for alias in aliases:
            alias_lower = alias.lower()
            if query in alias_lower:
                score += 0.2
                break
        
        # Normalize to 0.0-1.0 range
        return min(1.0, score)
    
    def _rank_results(
        self,
        results: List[Dict]
    ) -> List[Dict]:
        """
        Rank results by temporal factors (expiry, frequency).
        
        Scoring multipliers:
        - available: 1.0x
        - expiring_today: 1.5x
        - expiring_week: 1.2x
        - frequently_used: 1.1x
        
        Args:
            results: List of product dictionaries
            
        Returns:
            List of products with temporal_score added
        """
        today = date.today()
        week_from_now = today + timedelta(days=7)
        
        for product in results:
            temporal_score = 1.0  # Base score
            
            # Check expiry dates from inventory states
            stany = product.get("stany", [])
            if stany:
                # Find earliest expiry date
                expiry_dates = []
                for stan in stany:
                    if stan.get("data_waznosci"):
                        try:
                            expiry_date = date.fromisoformat(stan["data_waznosci"])
                            expiry_dates.append(expiry_date)
                        except (ValueError, TypeError):
                            continue
                
                if expiry_dates:
                    earliest_expiry = min(expiry_dates)
                    
                    if earliest_expiry < today:
                        # Expired - lower priority but still show
                        temporal_score = 0.5
                    elif earliest_expiry == today:
                        # Expiring today - highest priority
                        temporal_score = 1.5
                    elif earliest_expiry <= week_from_now:
                        # Expiring within week - high priority
                        temporal_score = 1.2
            
            # Check frequency (if available in future)
            # For now, we can use purchase frequency from database
            frequency = product.get("purchase_frequency", 0)
            if frequency > 10:  # Frequently purchased
                temporal_score *= 1.1
            
            product["temporal_score"] = min(2.0, temporal_score)  # Cap at 2.0
        
        return results
    
    def format_context(
        self,
        products: List[Dict],
        query_type: str
    ) -> str:
        """
        Format product context for different query types.
        
        Args:
            products: List of product dictionaries
            query_type: Type of query - one of:
                - "product_info": General product information
                - "recipe_suggestion": Recipe suggestions
                - "shopping_list": Shopping list generation
                - "expiry_usage": Using expiring products
        
        Returns:
            Formatted context string for LLM prompt
        """
        if not products:
            return "Brak dostępnych produktów."
        
        if query_type == "product_info":
            lines = ["Dostępne produkty:"]
            for i, product in enumerate(products[:10], 1):  # Limit to 10 for context
                nazwa = product.get("nazwa", "?")
                kategoria = product.get("kategoria", "?")
                ilosc = product.get("total_ilosc", 0)
                jednostka = product.get("stany", [{}])[0].get("jednostka", "szt") if product.get("stany") else "szt"
                lines.append(f"{i}. {nazwa} ({kategoria}) - {ilosc} {jednostka}")
            return "\n".join(lines)
        
        elif query_type == "recipe_suggestion":
            available_lines = ["Dostępne produkty:"]
            expiring_lines = ["Wygasające produkty (priorytet):"]
            
            for product in products[:15]:
                nazwa = product.get("nazwa", "?")
                kategoria = product.get("kategoria", "?")
                ilosc = product.get("total_ilosc", 0)
                jednostka = product.get("stany", [{}])[0].get("jednostka", "szt") if product.get("stany") else "szt"
                
                # Check if expiring soon
                is_expiring = False
                stany = product.get("stany", [])
                today = date.today()
                week_from_now = today + timedelta(days=7)
                
                for stan in stany:
                    if stan.get("data_waznosci"):
                        try:
                            expiry_date = date.fromisoformat(stan["data_waznosci"])
                            if expiry_date <= week_from_now:
                                is_expiring = True
                                break
                        except (ValueError, TypeError):
                            continue
                
                line = f"- {nazwa} ({kategoria}) - {ilosc} {jednostka}"
                if is_expiring:
                    expiring_lines.append(line)
                else:
                    available_lines.append(line)
            
            return "\n".join(available_lines) + "\n\n" + "\n".join(expiring_lines)
        
        elif query_type == "shopping_list":
            lines = ["Aktualny stan magazynu:"]
            for product in products[:20]:
                nazwa = product.get("nazwa", "?")
                ilosc = product.get("total_ilosc", 0)
                jednostka = product.get("stany", [{}])[0].get("jednostka", "szt") if product.get("stany") else "szt"
                lines.append(f"- {nazwa}: {ilosc} {jednostka}")
            return "\n".join(lines)
        
        elif query_type == "expiry_usage":
            lines = ["Wygasające produkty:"]
            today = date.today()
            week_from_now = today + timedelta(days=7)
            
            for product in products[:15]:
                nazwa = product.get("nazwa", "?")
                kategoria = product.get("kategoria", "?")
                stany = product.get("stany", [])
                
                expiring_stany = []
                for stan in stany:
                    if stan.get("data_waznosci"):
                        try:
                            expiry_date = date.fromisoformat(stan["data_waznosci"])
                            if expiry_date <= week_from_now:
                                expiring_stany.append({
                                    "ilosc": stan.get("ilosc", 0),
                                    "jednostka": stan.get("jednostka", "szt"),
                                    "data": expiry_date
                                })
                        except (ValueError, TypeError):
                            continue
                
                if expiring_stany:
                    for exp_stan in expiring_stany:
                        days_left = (exp_stan["data"] - today).days
                        days_str = "dziś" if days_left == 0 else f"{days_left} dni"
                        lines.append(
                            f"- {nazwa} ({kategoria}): {exp_stan['ilosc']} {exp_stan['jednostka']} "
                            f"(wygasa za {days_str})"
                        )
            
            if len(lines) == 1:
                return "Brak wygasających produktów."
            
            return "\n".join(lines)
        
        else:
            # Default format
            return self.format_context(products, "product_info")
    
    def _get_available_products(self) -> List[Dict]:
        """
        Get all available products with inventory (quantity > 0).
        
        Returns:
            List of product dictionaries with inventory information
        """
        try:
            stany = (
                self.session.query(StanMagazynowy)
                .join(Produkt, StanMagazynowy.produkt_id == Produkt.produkt_id)
                .options(
                    joinedload(StanMagazynowy.produkt)
                    .joinedload(Produkt.kategoria),
                    joinedload(StanMagazynowy.produkt)
                    .joinedload(Produkt.aliasy)
                )
                .filter(StanMagazynowy.ilosc > 0)
                .order_by(StanMagazynowy.data_waznosci)
                .all()
            )
            
            # Group by product
            products_dict = {}
            for stan in stany:
                produkt_id = stan.produkt_id
                
                if produkt_id not in products_dict:
                    # Get aliases
                    aliases = [alias.nazwa_z_paragonu for alias in stan.produkt.aliasy]
                    
                    products_dict[produkt_id] = {
                        "produkt_id": produkt_id,
                        "nazwa": stan.produkt.znormalizowana_nazwa,
                        "kategoria": (
                            stan.produkt.kategoria.nazwa_kategorii
                            if stan.produkt.kategoria
                            else "Inne"
                        ),
                        "aliases": aliases,
                        "total_ilosc": 0.0,
                        "stany": [],
                        "tags": [],  # Placeholder for future tags
                        "purchase_frequency": 0  # Placeholder for future frequency
                    }
                
                products_dict[produkt_id]["total_ilosc"] += float(stan.ilosc)
                products_dict[produkt_id]["stany"].append({
                    "ilosc": float(stan.ilosc),
                    "jednostka": stan.jednostka_miary or "szt",
                    "data_waznosci": (
                        stan.data_waznosci.isoformat()
                        if stan.data_waznosci
                        else None
                    ),
                    "zamrozone": stan.zamrozone,
                })
            
            return list(products_dict.values())
            
        except Exception as e:
            logger.error(f"Error getting available products: {e}")
            return []

