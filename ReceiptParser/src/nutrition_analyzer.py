"""
Nutritional Analysis for ParagonOCR 2.0

Provides comprehensive nutritional analysis of meals and products,
with gap identification and balanced meal suggestions.

Author: ParagonOCR Team
Version: 2.0
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session

from .database import Produkt, StanMagazynowy, PozycjaParagonu
from .llm import client, TIMEOUT_ANALYSIS
from .prompt_templates import PromptTemplates
from .config import Config

logger = logging.getLogger(__name__)


class NutritionAnalyzer:
    """
    Nutritional Analysis Engine.
    
    Analyzes nutritional content of meals, tracks daily nutrition,
    identifies gaps, and suggests balanced combinations.
    
    Attributes:
        session: SQLAlchemy database session
        product_metadata: Loaded product metadata with nutrition info
    """
    
    # Daily recommended values (for average adult)
    DAILY_RECOMMENDED = {
        'calories': 2000,
        'protein_g': 50,
        'fat_g': 65,
        'carbs_g': 300,
        'fiber_g': 25,
        'calcium_mg': 1000,
        'iron_mg': 15,
        'vitamin_c_mg': 90
    }
    
    def __init__(self, session: Session) -> None:
        """
        Initialize Nutrition Analyzer.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.product_metadata: Dict = {}
        self._load_product_metadata()
    
    def _load_product_metadata(self) -> None:
        """Load product metadata with nutrition information."""
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
    
    def analyze_meal(
        self,
        products: List[str],
        quantities_g: List[float]
    ) -> Dict:
        """
        Analyze nutritional content of a meal.
        
        Args:
            products: List of normalized product names
            quantities_g: List of quantities in grams (corresponding to products)
            
        Returns:
            Dictionary with nutritional analysis:
                - total_nutrition: Dict (calories, protein, fat, carbs, etc.)
                - per_100g: Dict (normalized per 100g)
                - per_serving: Dict (assuming 1 serving = total)
                - health_score: float (0-1)
                - recommendations: List[str]
        """
        if len(products) != len(quantities_g):
            logger.warning("Products and quantities lists have different lengths")
            return {}
        
        total_nutrition = {
            'calories': 0.0,
            'protein_g': 0.0,
            'fat_g': 0.0,
            'carbs_g': 0.0,
            'fiber_g': 0.0,
            'calcium_mg': 0.0,
            'iron_mg': 0.0,
            'vitamin_c_mg': 0.0
        }
        
        total_weight = sum(quantities_g)
        
        # Calculate nutrition for each product
        for product_name, quantity_g in zip(products, quantities_g):
            nutrition = self._get_product_nutrition(product_name, quantity_g)
            
            for key in total_nutrition:
                total_nutrition[key] += nutrition.get(key, 0.0)
        
        # Calculate per 100g
        per_100g = {}
        if total_weight > 0:
            for key, value in total_nutrition.items():
                per_100g[key] = round((value / total_weight) * 100, 2)
        
        # Calculate health score
        health_score = self._calculate_health_score(total_nutrition)
        
        # Get AI recommendations
        recommendations = self._get_nutrition_recommendations(total_nutrition, products)
        
        return {
            'total_nutrition': {k: round(v, 2) for k, v in total_nutrition.items()},
            'per_100g': per_100g,
            'per_serving': {k: round(v, 2) for k, v in total_nutrition.items()},
            'total_weight_g': round(total_weight, 2),
            'health_score': round(health_score, 2),
            'recommendations': recommendations
        }
    
    def daily_nutritional_tracking(self, date_str: str) -> Dict:
        """
        Track daily nutritional intake from receipts.
        
        Args:
            date_str: Date string in format 'YYYY-MM-DD'
            
        Returns:
            Dictionary with daily nutrition:
                - date: str
                - total_nutrition: Dict
                - meals: List[Dict] (meals from receipts)
                - percentage_of_daily: Dict (percentage of recommended)
                - gaps: List[str]
        """
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"Invalid date format: {date_str}")
            return {}
        
        # Get all receipts for this date
        from .database import Paragon
        
        receipts = (
            self.session.query(Paragon)
            .filter(Paragon.data_zakupu == target_date)
            .all()
        )
        
        if not receipts:
            return {
                'date': date_str,
                'total_nutrition': {k: 0.0 for k in self.DAILY_RECOMMENDED.keys()},
                'meals': [],
                'percentage_of_daily': {k: 0.0 for k in self.DAILY_RECOMMENDED.keys()},
                'gaps': []
            }
        
        # Aggregate nutrition from all receipts
        total_nutrition = {k: 0.0 for k in self.DAILY_RECOMMENDED.keys()}
        meals = []
        
        for receipt in receipts:
            for pozycja in receipt.pozycje:
                if pozycja.produkt:
                    product_name = pozycja.produkt.znormalizowana_nazwa
                    quantity_g = float(pozycja.ilosc) * 100.0  # Assume 100g per unit if no unit specified
                    
                    nutrition = self._get_product_nutrition(product_name, quantity_g)
                    
                    for key in total_nutrition:
                        total_nutrition[key] += nutrition.get(key, 0.0)
                    
                    meals.append({
                        'product': product_name,
                        'quantity': float(pozycja.ilosc),
                        'nutrition': nutrition
                    })
        
        # Calculate percentage of daily recommended
        percentage_of_daily = {}
        for key, value in total_nutrition.items():
            recommended = self.DAILY_RECOMMENDED.get(key, 1.0)
            percentage_of_daily[key] = round((value / recommended) * 100, 1) if recommended > 0 else 0.0
        
        # Identify gaps
        gaps = self.identify_gaps(total_nutrition)
        
        return {
            'date': date_str,
            'total_nutrition': {k: round(v, 2) for k, v in total_nutrition.items()},
            'meals': meals,
            'percentage_of_daily': percentage_of_daily,
            'gaps': gaps
        }
    
    def identify_gaps(self, nutrition_profile: Dict) -> List[str]:
        """
        Identify nutritional gaps in a profile.
        
        Args:
            nutrition_profile: Dictionary with nutritional values
            
        Returns:
            List of gap descriptions
        """
        gaps = []
        
        for nutrient, recommended in self.DAILY_RECOMMENDED.items():
            actual = nutrition_profile.get(nutrient, 0.0)
            percentage = (actual / recommended) * 100 if recommended > 0 else 0.0
            
            if percentage < 80:  # Less than 80% of recommended
                nutrient_name = self._get_nutrient_name(nutrient)
                gaps.append(
                    f"{nutrient_name}: {actual:.1f} / {recommended:.1f} "
                    f"({percentage:.1f}% - niedobór)"
                )
        
        return gaps
    
    def suggest_balanced_combinations(
        self,
        available_products: List[str]
    ) -> List[Dict]:
        """
        Suggest balanced meal combinations from available products.
        
        Args:
            available_products: List of normalized product names
            
        Returns:
            List of balanced meal suggestions:
                - name: str
                - products: List[str]
                - nutrition: Dict
                - balance_score: float
        """
        if not available_products:
            return []
        
        # Format products for prompt
        products_str = "\n".join(f"- {p}" for p in available_products)
        
        prompt = PromptTemplates.nutrition_analysis(
            products=products_str,
            health_goals="Zbilansowana dieta z odpowiednią ilością białka, węglowodanów i tłuszczów"
        )
        
        prompt += "\n\nZwróć odpowiedź w formacie JSON z listą zbilansowanych kombinacji posiłków. Każda kombinacja powinna mieć:\n"
        prompt += "- name: nazwa posiłku\n"
        prompt += "- products: lista produktów (tylko z dostępnych)\n"
        prompt += "- description: krótki opis\n"
        prompt += "- balance_score: ocena zbilansowania (0-1)\n\n"
        prompt += "Zwróć maksymalnie 5 najlepszych kombinacji."
        
        try:
            if not client:
                logger.error("Ollama client not available")
                return []
            
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
            
            # Try to extract JSON
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                combinations = json.loads(json_str)
                
                # Calculate actual nutrition for each combination
                enriched_combinations = []
                for combo in combinations:
                    if isinstance(combo, dict) and 'products' in combo:
                        products = combo.get('products', [])
                        
                        # Estimate quantities (assume 100g per product)
                        quantities = [100.0] * len(products)
                        
                        # Analyze nutrition
                        analysis = self.analyze_meal(products, quantities)
                        
                        enriched_combinations.append({
                            'name': combo.get('name', ''),
                            'products': products,
                            'description': combo.get('description', ''),
                            'nutrition': analysis.get('total_nutrition', {}),
                            'balance_score': float(combo.get('balance_score', 0.5)),
                            'health_score': analysis.get('health_score', 0.5)
                        })
                
                # Sort by balance score
                enriched_combinations.sort(key=lambda x: x['balance_score'], reverse=True)
                
                return enriched_combinations
            else:
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse combinations JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to suggest balanced combinations: {e}")
            return []
    
    def _get_product_nutrition(self, product_name: str, quantity_g: float) -> Dict:
        """
        Get nutrition information for a product.
        
        Args:
            product_name: Normalized product name
            quantity_g: Quantity in grams
            
        Returns:
            Dictionary with nutrition values
        """
        product_info = self.product_metadata.get(product_name, {})
        
        # Try nutrition_per_100g first
        nutrition = product_info.get('nutrition_per_100g', {})
        if not nutrition:
            # Try nutrition_per_100ml for liquids
            nutrition = product_info.get('nutrition_per_100ml', {})
        
        if not nutrition:
            return {k: 0.0 for k in self.DAILY_RECOMMENDED.keys()}
        
        # Scale to quantity
        result = {}
        for key in self.DAILY_RECOMMENDED.keys():
            base_value = nutrition.get(key, 0.0)
            result[key] = (base_value / 100.0) * quantity_g
        
        return result
    
    def _calculate_health_score(self, nutrition: Dict) -> float:
        """
        Calculate health score based on nutrition balance.
        
        Args:
            nutrition: Dictionary with nutrition values
            
        Returns:
            Health score (0-1)
        """
        score = 0.0
        
        # Check if within recommended ranges
        for nutrient, recommended in self.DAILY_RECOMMENDED.items():
            actual = nutrition.get(nutrient, 0.0)
            
            if recommended > 0:
                ratio = actual / recommended
                
                # Optimal range: 0.8 - 1.2
                if 0.8 <= ratio <= 1.2:
                    score += 1.0
                elif 0.6 <= ratio < 0.8 or 1.2 < ratio <= 1.5:
                    score += 0.7
                elif 0.4 <= ratio < 0.6 or 1.5 < ratio <= 2.0:
                    score += 0.4
                else:
                    score += 0.1
        
        # Normalize to 0-1
        return score / len(self.DAILY_RECOMMENDED)
    
    def _get_nutrition_recommendations(
        self,
        nutrition: Dict,
        products: List[str]
    ) -> List[str]:
        """
        Get AI-powered nutrition recommendations.
        
        Args:
            nutrition: Current nutrition values
            products: List of products in meal
            
        Returns:
            List of recommendation strings
        """
        if not client:
            return []
        
        nutrition_str = "\n".join([f"- {k}: {v:.1f}" for k, v in nutrition.items()])
        products_str = ", ".join(products)
        
        prompt = f"""Przeanalizuj wartość odżywczą posiłku i zaproponuj ulepszenia:

Produkty: {products_str}

Wartość odżywcza:
{nutrition_str}

Zalecane dzienne wartości:
{json.dumps(self.DAILY_RECOMMENDED, indent=2, ensure_ascii=False)}

Zwróć listę praktycznych rekomendacji (maksymalnie 5) jak poprawić wartość odżywczą:
- Czy czegoś brakuje?
- Czy czegoś jest za dużo?
- Jakie produkty dodać/odjąć?

Zwróć odpowiedź jako listę JSON stringów, np. ["rekomendacja 1", "rekomendacja 2"]
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
                recommendations = json.loads(json_str)
                return recommendations if isinstance(recommendations, list) else []
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get nutrition recommendations: {e}")
            return []
    
    def _get_nutrient_name(self, nutrient_key: str) -> str:
        """
        Get human-readable nutrient name.
        
        Args:
            nutrient_key: Nutrient key (e.g., 'protein_g')
            
        Returns:
            Human-readable name
        """
        names = {
            'calories': 'Kalorie',
            'protein_g': 'Białko',
            'fat_g': 'Tłuszcze',
            'carbs_g': 'Węglowodany',
            'fiber_g': 'Błonnik',
            'calcium_mg': 'Wapń',
            'iron_mg': 'Żelazo',
            'vitamin_c_mg': 'Witamina C'
        }
        return names.get(nutrient_key, nutrient_key)

