"""
Food Waste Reduction AI Engine for ParagonOCR 2.0

Provides AI-powered suggestions for reducing food waste through
recipe recommendations, freezing advice, and waste statistics.

Author: ParagonOCR Team
Version: 2.0
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session, joinedload

from .database import StanMagazynowy, Produkt
from .food_waste_tracker import FoodWasteTracker
from .recipe_engine import RecipeEngine
from .llm import client, TIMEOUT_ANALYSIS
from .prompt_templates import PromptTemplates
from .config import Config

logger = logging.getLogger(__name__)


class WasteReductionEngine:
    """
    Food Waste Reduction AI Engine.
    
    Combines waste tracking with AI-powered suggestions for recipes
    and freezing advice to reduce food waste.
    
    Attributes:
        session: SQLAlchemy database session
        waste_tracker: FoodWasteTracker instance
        recipe_engine: RecipeEngine instance
        product_metadata: Loaded product metadata
    """
    
    def __init__(self, session: Session) -> None:
        """
        Initialize the Waste Reduction Engine.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.waste_tracker = FoodWasteTracker(session)
        self.recipe_engine = RecipeEngine(session)
        self.product_metadata: Dict = {}
        self._load_product_metadata()
    
    def _load_product_metadata(self) -> None:
        """Load product metadata from product_metadata.json."""
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
    
    def get_expiry_alerts(self) -> Dict[str, List[Dict]]:
        """
        Get expiry alerts with recipe suggestions for expiring products.
        
        Returns:
            Dictionary with keys: 'expired', 'critical', 'warning', 'normal'
            Each value is a list of products with recipe suggestions
        """
        # Update priorities first
        self.waste_tracker.update_priorities()
        
        # Get alerts from tracker
        alerts = self.waste_tracker.get_expiry_alerts()
        
        # Add recipe suggestions for expiring products
        expiring_products = (
            alerts.get('expired', []) +
            alerts.get('critical', []) +
            alerts.get('warning', [])
        )
        
        if expiring_products:
            # Get product names
            product_names = [p['nazwa'] for p in expiring_products]
            
            # Get recipe suggestions
            recipes = self.recipe_engine.suggest_recipes(
                available_products=product_names,
                preferences={'difficulty': 'easy', 'max_prep_time': 60}
            )
            
            # Match recipes to products (simple matching by ingredient names)
            for product in expiring_products:
                product_name = product['nazwa'].lower()
                matching_recipes = []
                
                for recipe in recipes[:3]:  # Top 3 recipes
                    ingredients_str = ' '.join(recipe.get('ingredients', [])).lower()
                    if product_name in ingredients_str or any(
                        product_name in ing.lower() for ing in recipe.get('ingredients', [])
                    ):
                        matching_recipes.append({
                            'name': recipe.get('name', ''),
                            'description': recipe.get('description', ''),
                            'prep_time': recipe.get('prep_time', 30),
                            'difficulty': recipe.get('difficulty', 'medium')
                        })
                
                product['suggested_recipes'] = matching_recipes[:2]  # Max 2 recipes per product
        
        return alerts
    
    def suggest_freezing(self, product_name: str) -> Dict:
        """
        Suggest freezing options for a product.
        
        Args:
            product_name: Normalized product name
            
        Returns:
            Dictionary with freezing suggestions:
                - can_freeze: bool
                - freeze_note: str
                - freezing_method: str
                - storage_duration: str
                - thawing_advice: str
        """
        # Check product metadata first
        product_info = self.product_metadata.get(product_name, {})
        properties = product_info.get('properties', {})
        
        can_freeze = properties.get('can_freeze', False)
        freeze_note = properties.get('freeze_note', '')
        
        # If metadata doesn't have info, ask LLM
        if not product_info or 'can_freeze' not in properties:
            return self._llm_suggest_freezing(product_name)
        
        # Build response from metadata
        result = {
            'can_freeze': can_freeze,
            'freeze_note': freeze_note or 'Brak dodatkowych uwag',
            'freezing_method': '',
            'storage_duration': '',
            'thawing_advice': ''
        }
        
        # Get detailed advice from LLM if can freeze
        if can_freeze:
            llm_advice = self._llm_suggest_freezing(product_name)
            result.update({
                'freezing_method': llm_advice.get('freezing_method', ''),
                'storage_duration': llm_advice.get('storage_duration', ''),
                'thawing_advice': llm_advice.get('thawing_advice', '')
            })
        
        return result
    
    def _llm_suggest_freezing(self, product_name: str) -> Dict:
        """
        Get freezing advice from LLM.
        
        Args:
            product_name: Normalized product name
            
        Returns:
            Dictionary with freezing advice
        """
        prompt = f"""Podaj poradę na temat mrożenia produktu: {product_name}

Zwróć odpowiedź w formacie JSON z następującymi polami:
- can_freeze: bool (czy produkt można mrozić)
- freeze_note: str (uwagi dotyczące mrożenia)
- freezing_method: str (sposób mrożenia - szczegółowy opis)
- storage_duration: str (jak długo można przechowywać w zamrażarce)
- thawing_advice: str (porada dotycząca rozmrażania)

Jeśli produkt nie nadaje się do mrożenia, ustaw can_freeze na false i podaj wyjaśnienie w freeze_note.
"""
        
        try:
            if not client:
                logger.error("Ollama client not available")
                return {
                    'can_freeze': False,
                    'freeze_note': 'Nie można określić - brak połączenia z AI',
                    'freezing_method': '',
                    'storage_duration': '',
                    'thawing_advice': ''
                }
            
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
                return {
                    'can_freeze': False,
                    'freeze_note': 'Nie udało się uzyskać odpowiedzi',
                    'freezing_method': '',
                    'storage_duration': '',
                    'thawing_advice': ''
                }
            
            response_text = response.get('message', {}).get('content', '').strip()
            
            # Try to extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                advice = json.loads(json_str)
                return advice
            else:
                # Fallback: try to parse from text
                return {
                    'can_freeze': 'można' in response_text.lower() or 'tak' in response_text.lower(),
                    'freeze_note': response_text[:200] if response_text else 'Brak informacji',
                    'freezing_method': '',
                    'storage_duration': '',
                    'thawing_advice': ''
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse freezing advice JSON: {e}")
            return {
                'can_freeze': False,
                'freeze_note': 'Błąd parsowania odpowiedzi',
                'freezing_method': '',
                'storage_duration': '',
                'thawing_advice': ''
            }
        except Exception as e:
            logger.error(f"Failed to get freezing advice: {e}")
            return {
                'can_freeze': False,
                'freeze_note': f'Błąd: {str(e)}',
                'freezing_method': '',
                'storage_duration': '',
                'thawing_advice': ''
            }
    
    def get_waste_stats(self, days: int = 30) -> Dict:
        """
        Get comprehensive waste statistics with AI analysis.
        
        Args:
            days: Number of days to analyze (default: 30)
            
        Returns:
            Dictionary with waste statistics:
                - expired_count: int
                - expired_value: float (PLN)
                - period_days: int
                - waste_trend: str (AI analysis)
                - recommendations: List[str] (AI recommendations)
                - top_wasted_categories: List[Dict]
        """
        # Get basic stats from tracker
        basic_stats = self.waste_tracker.get_waste_statistics(days=days)
        
        # Get expiring products
        alerts = self.waste_tracker.get_expiry_alerts()
        
        # Calculate category breakdown
        category_stats = {}
        all_expiring = (
            alerts.get('expired', []) +
            alerts.get('critical', []) +
            alerts.get('warning', [])
        )
        
        for product in all_expiring:
            category = product.get('kategoria', 'Inne')
            if category not in category_stats:
                category_stats[category] = {
                    'count': 0,
                    'products': []
                }
            category_stats[category]['count'] += 1
            category_stats[category]['products'].append(product['nazwa'])
        
        # Sort categories by count
        top_categories = sorted(
            [
                {'category': cat, 'count': data['count'], 'products': data['products'][:5]}
                for cat, data in category_stats.items()
            ],
            key=lambda x: x['count'],
            reverse=True
        )[:5]
        
        # Get AI analysis
        ai_analysis = self._analyze_waste_patterns(basic_stats, top_categories, days)
        
        return {
            **basic_stats,
            'waste_trend': ai_analysis.get('trend', ''),
            'recommendations': ai_analysis.get('recommendations', []),
            'top_wasted_categories': top_categories,
            'current_expiring': {
                'expired': len(alerts.get('expired', [])),
                'critical': len(alerts.get('critical', [])),
                'warning': len(alerts.get('warning', []))
            }
        }
    
    def _analyze_waste_patterns(
        self,
        stats: Dict,
        top_categories: List[Dict],
        days: int
    ) -> Dict:
        """
        Analyze waste patterns using AI.
        
        Args:
            stats: Basic waste statistics
            top_categories: Top wasted categories
            days: Analysis period
            
        Returns:
            Dictionary with trend analysis and recommendations
        """
        prompt = f"""Przeanalizuj wzorce marnowania żywności na podstawie następujących danych:

Statystyki za ostatnie {days} dni:
- Przeterminowane produkty: {stats.get('expired_count', 0)}
- Wartość zmarnowana: {stats.get('expired_value', 0):.2f} PLN

Najczęściej marnowane kategorie:
{json.dumps(top_categories, ensure_ascii=False, indent=2)}

Zwróć odpowiedź w formacie JSON z następującymi polami:
- trend: str (krótka analiza trendu - czy marnowanie rośnie, spada, stabilne)
- recommendations: List[str] (lista konkretnych rekomendacji jak zmniejszyć marnowanie)

Bądź konkretny i praktyczny w rekomendacjach.
"""
        
        try:
            if not client:
                return {
                    'trend': 'Nie można przeanalizować - brak połączenia z AI',
                    'recommendations': []
                }
            
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
                return {
                    'trend': 'Nie udało się uzyskać analizy',
                    'recommendations': []
                }
            
            response_text = response.get('message', {}).get('content', '').strip()
            
            # Try to extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)
                return analysis
            else:
                # Fallback
                return {
                    'trend': response_text[:200] if response_text else 'Brak analizy',
                    'recommendations': []
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse waste analysis JSON: {e}")
            return {
                'trend': 'Błąd parsowania analizy',
                'recommendations': []
            }
        except Exception as e:
            logger.error(f"Failed to analyze waste patterns: {e}")
            return {
                'trend': f'Błąd: {str(e)}',
                'recommendations': []
            }

