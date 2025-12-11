"""
Smart Recipe Engine for ParagonOCR 2.0

Provides intelligent recipe suggestions based on available products,
with cost calculation and recipe details retrieval.

Author: ParagonOCR Team
Version: 2.0
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session, joinedload
from datetime import date, timedelta

from .database import Produkt, StanMagazynowy
from .llm import client, TIMEOUT_RECIPES
from .prompt_templates import PromptTemplates
from .config import Config

logger = logging.getLogger(__name__)


class RecipeEngine:
    """
    Smart Recipe Engine for suggesting recipes based on available products.
    
    Uses LLM to generate recipe suggestions and calculates recipe costs
    based on product metadata.
    
    Attributes:
        session: SQLAlchemy database session
        product_metadata: Loaded product metadata for cost calculation
    """
    
    def __init__(self, session: Session) -> None:
        """
        Initialize the Recipe Engine.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.product_metadata: Dict = {}
        self._load_product_metadata()
    
    def _load_product_metadata(self) -> None:
        """Load product metadata from product_metadata.json for cost calculation."""
        try:
            project_root = Path(__file__).parent.parent.parent
            metadata_path = project_root / "ReceiptParser" / "data" / "product_metadata.json"
            
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.product_metadata = data.get('products', {})
                logger.info(f"Loaded {len(self.product_metadata)} products metadata")
            else:
                logger.warning(f"product_metadata.json not found at {metadata_path}")
        except Exception as e:
            logger.error(f"Failed to load product metadata: {e}")
            self.product_metadata = {}
    
    def suggest_recipes(
        self,
        available_products: List[str],
        preferences: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Suggest recipes based on available products.
        
        Uses LLM to generate recipe suggestions with priority on expiring products.
        
        Args:
            available_products: List of normalized product names
            preferences: Optional preferences dict with keys:
                - dietary_preferences: str (e.g., "vegan", "vegetarian")
                - allergens: List[str] (e.g., ["gluten", "lactose"])
                - cuisine_type: str (e.g., "polish", "italian")
                - difficulty: str (e.g., "easy", "medium", "hard")
                - max_prep_time: int (minutes)
        
        Returns:
            List of recipe dictionaries with:
                - name: str
                - description: str
                - ingredients: List[str]
                - prep_time: int (minutes)
                - difficulty: str
                - score: float (relevance score)
        """
        if not available_products:
            return []
        
        # Get expiring products for priority
        expiring_products = self._get_expiring_products(available_products)
        
        # Format products for prompt
        available_str = self._format_products_list(available_products)
        expiring_str = self._format_products_list(expiring_products) if expiring_products else "Brak wygasających produktów"
        
        # Build preferences string
        prefs_str = self._format_preferences(preferences) if preferences else "Brak szczególnych preferencji"
        
        # Create prompt using template
        prompt = PromptTemplates.recipe_suggestion(
            available_products=available_str,
            expiring_products=expiring_str
        )
        
        # Add preferences if provided
        if preferences:
            prompt += f"\n\nPreferencje:\n{prefs_str}"
        
        prompt += "\n\nZwróć odpowiedź w formacie JSON z listą przepisów. Każdy przepis powinien mieć:\n"
        prompt += "- name: nazwa przepisu\n"
        prompt += "- description: krótki opis\n"
        prompt += "- ingredients: lista składników (tylko te dostępne)\n"
        prompt += "- prep_time: czas przygotowania w minutach\n"
        prompt += "- difficulty: poziom trudności (easy/medium/hard)\n"
        prompt += "- score: ocena trafności (0-1)\n\n"
        prompt += "Zwróć maksymalnie 5 najlepszych przepisów."
        
        try:
            if not client:
                logger.error("Ollama client not available")
                return []
            
            # Use LLM to generate recipes
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
                logger.warning("Empty response from LLM")
                return []
            
            # Parse JSON response
            response_text = response.get('message', {}).get('content', '').strip()
            
            # Try to extract JSON from response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                recipes = json.loads(json_str)
                
                # Validate and normalize recipes
                normalized_recipes = []
                for recipe in recipes:
                    if isinstance(recipe, dict) and 'name' in recipe:
                        normalized_recipe = {
                            'name': recipe.get('name', ''),
                            'description': recipe.get('description', ''),
                            'ingredients': recipe.get('ingredients', []),
                            'prep_time': recipe.get('prep_time', 30),
                            'difficulty': recipe.get('difficulty', 'medium'),
                            'score': float(recipe.get('score', 0.5))
                        }
                        normalized_recipes.append(normalized_recipe)
                
                # Sort by score (descending)
                normalized_recipes.sort(key=lambda x: x['score'], reverse=True)
                
                return normalized_recipes
            else:
                logger.warning("Could not extract JSON from LLM response")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to generate recipes: {e}")
            return []
    
    def get_recipe_details(self, recipe_name: str) -> Dict:
        """
        Get detailed information about a specific recipe.
        
        Args:
            recipe_name: Name of the recipe
            
        Returns:
            Dictionary with recipe details:
                - name: str
                - description: str
                - ingredients: List[Dict] with name, quantity, unit
                - instructions: List[str] (step-by-step)
                - prep_time: int (minutes)
                - cook_time: int (minutes)
                - difficulty: str
                - servings: int
                - nutrition: Dict (calories, protein, etc.)
        """
        if not recipe_name:
            return {}
        
        prompt = f"""Podaj szczegółowe informacje o przepisie: {recipe_name}

Zwróć odpowiedź w formacie JSON z następującymi polami:
- name: nazwa przepisu
- description: szczegółowy opis
- ingredients: lista obiektów z polami: name, quantity, unit
- instructions: lista kroków przygotowania (kolejno)
- prep_time: czas przygotowania w minutach
- cook_time: czas gotowania w minutach
- difficulty: poziom trudności (easy/medium/hard)
- servings: liczba porcji
- nutrition: obiekt z polami: calories, protein_g, fat_g, carbs_g
"""
        
        try:
            if not client:
                logger.error("Ollama client not available")
                return {}
            
            response = client.chat(
                model=Config.TEXT_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.5,
                }
            )
            
            if not response or 'message' not in response:
                return {}
            
            response_text = response.get('message', {}).get('content', '').strip()
            
            # Try to extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                recipe_details = json.loads(json_str)
                return recipe_details
            else:
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse recipe details JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to get recipe details: {e}")
            return {}
    
    def calculate_recipe_cost(self, recipe_name: str) -> float:
        """
        Calculate estimated cost of a recipe based on product prices.
        
        Args:
            recipe_name: Name of the recipe
            
        Returns:
            Estimated cost in PLN, or 0.0 if calculation fails
        """
        # Get recipe details first
        recipe_details = self.get_recipe_details(recipe_name)
        
        if not recipe_details or 'ingredients' not in recipe_details:
            return 0.0
        
        total_cost = 0.0
        
        for ingredient in recipe_details['ingredients']:
            if isinstance(ingredient, dict):
                ingredient_name = ingredient.get('name', '')
                quantity = float(ingredient.get('quantity', 1.0))
                unit = ingredient.get('unit', 'szt')
                
                # Get product price from metadata
                product_price = self._get_product_price(ingredient_name, unit)
                
                if product_price > 0:
                    # Calculate cost based on quantity and unit
                    cost = self._calculate_ingredient_cost(
                        product_price,
                        quantity,
                        unit
                    )
                    total_cost += cost
        
        return round(total_cost, 2)
    
    def _get_expiring_products(self, available_products: List[str]) -> List[str]:
        """
        Get list of products that are expiring soon.
        
        Args:
            available_products: List of normalized product names
            
        Returns:
            List of expiring product names
        """
        try:
            today = date.today()
            warning_date = today + timedelta(days=3)  # 3 days ahead
            
            expiring = (
                self.session.query(StanMagazynowy)
                .join(Produkt)
                .filter(
                    StanMagazynowy.ilosc > 0,
                    StanMagazynowy.data_waznosci.isnot(None),
                    StanMagazynowy.data_waznosci <= warning_date,
                    Produkt.znormalizowana_nazwa.in_(available_products)
                )
                .options(joinedload(StanMagazynowy.produkt))
                .all()
            )
            
            return [s.produkt.znormalizowana_nazwa for s in expiring]
        except Exception as e:
            logger.error(f"Failed to get expiring products: {e}")
            return []
    
    def _format_products_list(self, products: List[str]) -> str:
        """
        Format list of products for prompt.
        
        Args:
            products: List of product names
            
        Returns:
            Formatted string
        """
        if not products:
            return "Brak produktów"
        
        return "\n".join(f"- {product}" for product in products)
    
    def _format_preferences(self, preferences: Dict) -> str:
        """
        Format preferences dict for prompt.
        
        Args:
            preferences: Preferences dictionary
            
        Returns:
            Formatted string
        """
        lines = []
        
        if 'dietary_preferences' in preferences:
            lines.append(f"Preferencje dietetyczne: {preferences['dietary_preferences']}")
        
        if 'allergens' in preferences and preferences['allergens']:
            lines.append(f"Alergie: {', '.join(preferences['allergens'])}")
        
        if 'cuisine_type' in preferences:
            lines.append(f"Typ kuchni: {preferences['cuisine_type']}")
        
        if 'difficulty' in preferences:
            lines.append(f"Poziom trudności: {preferences['difficulty']}")
        
        if 'max_prep_time' in preferences:
            lines.append(f"Maksymalny czas przygotowania: {preferences['max_prep_time']} minut")
        
        return "\n".join(lines) if lines else "Brak preferencji"
    
    def _get_product_price(self, product_name: str, unit: str) -> float:
        """
        Get average price for a product from metadata.
        
        Args:
            product_name: Normalized product name
            unit: Unit of measurement
            
        Returns:
            Average price per unit, or 0.0 if not found
        """
        if not self.product_metadata:
            return 0.0
        
        # Try exact match first
        if product_name in self.product_metadata:
            price_range = self.product_metadata[product_name].get('price_range_pln', [])
            if price_range and len(price_range) >= 2:
                # Return average price
                return (price_range[0] + price_range[1]) / 2.0
        
        # Try fuzzy match on normalized names
        from rapidfuzz import fuzz
        
        best_match = None
        best_score = 0.0
        
        for normalized_name in self.product_metadata.keys():
            score = fuzz.partial_ratio(product_name.lower(), normalized_name.lower())
            if score > best_score and score >= 70:
                best_score = score
                best_match = normalized_name
        
        if best_match:
            price_range = self.product_metadata[best_match].get('price_range_pln', [])
            if price_range and len(price_range) >= 2:
                return (price_range[0] + price_range[1]) / 2.0
        
        return 0.0
    
    def _calculate_ingredient_cost(
        self,
        price_per_unit: float,
        quantity: float,
        unit: str
    ) -> float:
        """
        Calculate cost for an ingredient based on quantity and unit.
        
        Args:
            price_per_unit: Price per base unit (e.g., per 100g, per 1L)
            quantity: Quantity needed
            unit: Unit of measurement (g, kg, ml, l, szt)
            
        Returns:
            Calculated cost in PLN
        """
        # Normalize units
        unit_lower = unit.lower()
        
        # For weight units (g, kg)
        if unit_lower in ['g', 'gram', 'gramy']:
            # Assume price_per_unit is per 100g
            return (price_per_unit / 100.0) * quantity
        elif unit_lower in ['kg', 'kilogram', 'kilogramy']:
            # Assume price_per_unit is per 100g, convert to per kg
            return (price_per_unit * 10.0) * quantity
        
        # For volume units (ml, l)
        elif unit_lower in ['ml', 'mililitr', 'mililitry']:
            # Assume price_per_unit is per 100ml
            return (price_per_unit / 100.0) * quantity
        elif unit_lower in ['l', 'litr', 'litry', 'litrów']:
            # Assume price_per_unit is per 100ml, convert to per L
            return (price_per_unit * 10.0) * quantity
        
        # For pieces (szt)
        elif unit_lower in ['szt', 'sztuka', 'sztuki', 'sztuk']:
            return price_per_unit * quantity
        
        # Default: assume price_per_unit is already per unit
        return price_per_unit * quantity

