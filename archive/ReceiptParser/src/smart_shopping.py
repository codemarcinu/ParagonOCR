"""
Smart Shopping Lists for ParagonOCR 2.0

Provides intelligent shopping list generation with store layout grouping,
alternative suggestions, and budget optimization.

Author: ParagonOCR Team
Version: 2.0
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from .llm import client, TIMEOUT_ANALYSIS
from .prompt_templates import PromptTemplates
from .config import Config

logger = logging.getLogger(__name__)


class SmartShopping:
    """
    Smart Shopping List Generator.
    
    Generates optimized shopping lists with store layout grouping,
    alternative product suggestions, and budget considerations.
    
    Attributes:
        session: SQLAlchemy database session
        product_metadata: Loaded product metadata
        shop_variants: Loaded shop-specific variants
    """
    
    def __init__(self, session: Session) -> None:
        """
        Initialize Smart Shopping.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.product_metadata: Dict = {}
        self.shop_variants: Dict = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Load product metadata and shop variants."""
        try:
            project_root = Path(__file__).parent.parent.parent
            
            # Load product metadata
            metadata_path = project_root / "ReceiptParser" / "data" / "product_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.product_metadata = data.get('products', {})
                logger.info(f"Loaded {len(self.product_metadata)} products metadata")
            
            # Load shop variants
            shop_variants_path = project_root / "ReceiptParser" / "data" / "shop_variants.json"
            if shop_variants_path.exists():
                with open(shop_variants_path, 'r', encoding='utf-8') as f:
                    self.shop_variants = json.load(f)
                logger.info(f"Loaded shop variants for {len(self.shop_variants)} shops")
        except Exception as e:
            logger.error(f"Failed to load shopping data: {e}")
    
    def generate_shopping_list(
        self,
        planned_meals: List[str],
        budget_pln: Optional[float] = None
    ) -> Dict:
        """
        Generate a smart shopping list based on planned meals.
        
        Args:
            planned_meals: List of planned meal/dish names
            budget_pln: Optional budget in PLN
            
        Returns:
            Dictionary with shopping list:
                - items: List[Dict] with name, quantity, unit, estimated_price
                - total_estimated_cost: float
                - budget_pln: float
                - within_budget: bool
                - suggestions: List[str] (AI suggestions)
        """
        if not planned_meals:
            return {
                'items': [],
                'total_estimated_cost': 0.0,
                'budget_pln': budget_pln or 0.0,
                'within_budget': True,
                'suggestions': []
            }
        
        # Format meals for prompt
        meals_str = "\n".join(f"- {meal}" for meal in planned_meals)
        
        # Create prompt
        prompt = PromptTemplates.shopping_list(
            current_inventory="Brak informacji o aktualnym stanie magazynu",
            planned_meals=meals_str,
            budget=budget_pln
        )
        
        prompt += "\n\nZwróć odpowiedź w formacie JSON z listą produktów. Każdy produkt powinien mieć:\n"
        prompt += "- name: znormalizowana nazwa produktu\n"
        prompt += "- quantity: ilość (liczba)\n"
        prompt += "- unit: jednostka miary (szt, kg, l, g, ml)\n"
        prompt += "- category: kategoria produktu\n"
        prompt += "- priority: priorytet (high/medium/low)\n\n"
        prompt += "Zwróć tylko produkty, których nie ma w aktualnym magazynie."
        
        try:
            if not client:
                logger.error("Ollama client not available")
                return self._fallback_shopping_list(planned_meals, budget_pln)
            
            response = client.chat(
                model=Config.TEXT_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.7,
                }
            )
            
            if not response or 'message' not in response:
                return self._fallback_shopping_list(planned_meals, budget_pln)
            
            response_text = response.get('message', {}).get('content', '').strip()
            
            # Try to extract JSON
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                items = json.loads(json_str)
                
                # Calculate costs and build shopping list
                shopping_list = []
                total_cost = 0.0
                
                for item in items:
                    if isinstance(item, dict) and 'name' in item:
                        product_name = item.get('name', '')
                        quantity = float(item.get('quantity', 1.0))
                        unit = item.get('unit', 'szt')
                        
                        # Estimate price
                        estimated_price = self._estimate_product_price(product_name, quantity, unit)
                        total_cost += estimated_price
                        
                        shopping_list.append({
                            'name': product_name,
                            'quantity': quantity,
                            'unit': unit,
                            'category': item.get('category', 'Inne'),
                            'priority': item.get('priority', 'medium'),
                            'estimated_price': round(estimated_price, 2)
                        })
                
                # Get AI suggestions
                suggestions = self._get_shopping_suggestions(shopping_list, budget_pln, total_cost)
                
                return {
                    'items': shopping_list,
                    'total_estimated_cost': round(total_cost, 2),
                    'budget_pln': budget_pln or 0.0,
                    'within_budget': budget_pln is None or total_cost <= budget_pln,
                    'suggestions': suggestions
                }
            else:
                return self._fallback_shopping_list(planned_meals, budget_pln)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse shopping list JSON: {e}")
            return self._fallback_shopping_list(planned_meals, budget_pln)
        except Exception as e:
            logger.error(f"Failed to generate shopping list: {e}")
            return self._fallback_shopping_list(planned_meals, budget_pln)
    
    def group_by_store_layout(
        self,
        store_name: str,
        items: List[str]
    ) -> List[List[str]]:
        """
        Group shopping list items by store layout sections.
        
        Args:
            store_name: Name of the store (LIDL, BIEDRONKA, KAUFLAND, AUCHAN)
            items: List of product names
            
        Returns:
            List of lists, where each inner list represents a store section
        """
        # Standard store layout sections (typical Polish supermarket)
        standard_sections = [
            "Warzywa i owoce",
            "Pieczywo",
            "Nabiał",
            "Mięso i wędliny",
            "Napoje",
            "Słodycze i przekąski",
            "Przyprawy i sypkie",
            "Mrożonki",
            "Konserwy i słoiki",
            "Inne"
        ]
        
        # Map products to sections based on metadata
        section_groups: Dict[str, List[str]] = {section: [] for section in standard_sections}
        
        for item in items:
            # Get product category from metadata
            product_info = self.product_metadata.get(item, {})
            category = product_info.get('kategoria', 'Inne')
            
            # Map category to section
            section = self._category_to_section(category)
            if section in section_groups:
                section_groups[section].append(item)
            else:
                section_groups["Inne"].append(item)
        
        # Return non-empty sections
        return [section_groups[section] for section in standard_sections if section_groups[section]]
    
    def suggest_alternatives(
        self,
        product_name: str,
        max_price_pln: Optional[float] = None
    ) -> List[Dict]:
        """
        Suggest alternative products with similar properties.
        
        Args:
            product_name: Normalized product name
            max_price_pln: Optional maximum price constraint
            
        Returns:
            List of alternative products with:
                - name: str
                - price: float
                - similarity_score: float
                - reason: str (why it's a good alternative)
        """
        if not self.product_metadata:
            return []
        
        # Get product info
        product_info = self.product_metadata.get(product_name, {})
        if not product_info:
            return []
        
        product_category = product_info.get('kategoria', '')
        product_tags = set(product_info.get('tags', []))
        product_price_range = product_info.get('price_range_pln', [])
        avg_price = (product_price_range[0] + product_price_range[1]) / 2.0 if len(product_price_range) >= 2 else 0.0
        
        # Find alternatives in same category
        alternatives = []
        for alt_name, alt_info in self.product_metadata.items():
            if alt_name == product_name:
                continue
            
            alt_category = alt_info.get('kategoria', '')
            alt_tags = set(alt_info.get('tags', []))
            alt_price_range = alt_info.get('price_range_pln', [])
            alt_avg_price = (alt_price_range[0] + alt_price_range[1]) / 2.0 if len(alt_price_range) >= 2 else 0.0
            
            # Check price constraint
            if max_price_pln and alt_avg_price > max_price_pln:
                continue
            
            # Calculate similarity
            similarity = 0.0
            
            # Category match
            if alt_category == product_category:
                similarity += 0.5
            
            # Tag overlap
            tag_overlap = len(product_tags & alt_tags) / max(len(product_tags | alt_tags), 1)
            similarity += tag_overlap * 0.3
            
            # Price similarity (closer price = higher similarity)
            if avg_price > 0 and alt_avg_price > 0:
                price_diff = abs(avg_price - alt_avg_price) / max(avg_price, alt_avg_price)
                similarity += (1.0 - min(price_diff, 1.0)) * 0.2
            
            if similarity > 0.3:  # Minimum similarity threshold
                alternatives.append({
                    'name': alt_name,
                    'price': round(alt_avg_price, 2),
                    'similarity_score': round(similarity, 2),
                    'reason': self._generate_alternative_reason(product_name, alt_name, similarity)
                })
        
        # Sort by similarity (descending)
        alternatives.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return alternatives[:5]  # Top 5 alternatives
    
    def _category_to_section(self, category: str) -> str:
        """
        Map product category to store section.
        
        Args:
            category: Product category
            
        Returns:
            Store section name
        """
        category_mapping = {
            'Warzywa': 'Warzywa i owoce',
            'Owoce': 'Warzywa i owoce',
            'Piekarnicze': 'Pieczywo',
            'Nabiał': 'Nabiał',
            'Mięso': 'Mięso i wędliny',
            'Napoje': 'Napoje',
            'Snacki': 'Słodycze i przekąski',
            'Przyprawy': 'Przyprawy i sypkie',
            'Mrożone': 'Mrożonki',
            'Słoiki/Puszki': 'Konserwy i słoiki'
        }
        
        return category_mapping.get(category, 'Inne')
    
    def _estimate_product_price(
        self,
        product_name: str,
        quantity: float,
        unit: str
    ) -> float:
        """
        Estimate price for a product.
        
        Args:
            product_name: Normalized product name
            quantity: Quantity needed
            unit: Unit of measurement
            
        Returns:
            Estimated price in PLN
        """
        product_info = self.product_metadata.get(product_name, {})
        price_range = product_info.get('price_range_pln', [])
        
        if not price_range or len(price_range) < 2:
            return 0.0
        
        # Use average price
        avg_price = (price_range[0] + price_range[1]) / 2.0
        
        # Adjust for quantity and unit (simplified)
        if unit in ['kg', 'l']:
            return avg_price * quantity
        elif unit in ['g', 'ml']:
            return (avg_price / 1000.0) * quantity
        else:  # szt, etc.
            return avg_price * quantity
    
    def _get_shopping_suggestions(
        self,
        items: List[Dict],
        budget: Optional[float],
        total_cost: float
    ) -> List[str]:
        """
        Get AI-powered shopping suggestions.
        
        Args:
            items: Shopping list items
            budget: Optional budget
            total_cost: Total estimated cost
            
        Returns:
            List of suggestion strings
        """
        if not client:
            return []
        
        items_str = "\n".join([
            f"- {item['name']} ({item['quantity']} {item['unit']}) - {item['estimated_price']:.2f} PLN"
            for item in items
        ])
        
        budget_str = f"{budget:.2f} PLN" if budget else "Nie określono"
        
        prompt = f"""Przeanalizuj listę zakupów i zaproponuj optymalizacje:

Lista zakupów:
{items_str}

Szacowany koszt: {total_cost:.2f} PLN
Budżet: {budget_str}

Zwróć listę praktycznych sugestii (maksymalnie 5) jak zoptymalizować zakupy:
- Czy można coś zastąpić tańszym odpowiednikiem?
- Czy można kupić większe opakowania (oszczędność)?
- Czy są produkty, które można pominąć?
- Czy można kupić w innym sklepie taniej?

Zwróć odpowiedź jako listę JSON stringów, np. ["sugestia 1", "sugestia 2"]
"""
        
        try:
            response = client.chat(
                model=Config.TEXT_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.7,
                }
            )
            
            if not response or 'message' not in response:
                return []
            
            response_text = response.get('message', {}).get('content', '').strip()
            
            # Try to extract JSON array
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                suggestions = json.loads(json_str)
                return suggestions if isinstance(suggestions, list) else []
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get shopping suggestions: {e}")
            return []
    
    def _generate_alternative_reason(
        self,
        original: str,
        alternative: str,
        similarity: float
    ) -> str:
        """
        Generate reason why alternative is good.
        
        Args:
            original: Original product name
            alternative: Alternative product name
            similarity: Similarity score
            
        Returns:
            Reason string
        """
        if similarity >= 0.8:
            return f"Bardzo podobny do {original}"
        elif similarity >= 0.6:
            return f"Dobry zamiennik dla {original}"
        else:
            return f"Alternatywa dla {original}"
    
    def _fallback_shopping_list(
        self,
        planned_meals: List[str],
        budget: Optional[float]
    ) -> Dict:
        """
        Generate fallback shopping list when LLM fails.
        
        Args:
            planned_meals: List of planned meals
            budget: Optional budget
            
        Returns:
            Basic shopping list structure
        """
        return {
            'items': [],
            'total_estimated_cost': 0.0,
            'budget_pln': budget or 0.0,
            'within_budget': True,
            'suggestions': ['Nie udało się wygenerować szczegółowej listy. Spróbuj ponownie.']
        }

