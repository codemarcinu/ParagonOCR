"""
Prompt Templates for ParagonOCR 2.0

Provides standardized prompt templates for different AI chat use cases.

Author: ParagonOCR Team
Version: 2.0
"""

from typing import Dict, Optional


class PromptTemplates:
    """
    Prompt templates for various AI chat scenarios.
    
    Provides consistent, well-structured prompts for different
    types of queries to improve AI response quality.
    """
    
    @staticmethod
    def product_info(products_context: str, query: str) -> str:
        """
        Template for product information queries.
        
        Args:
            products_context: Formatted list of available products
            query: User's question about products
            
        Returns:
            Formatted prompt string
        """
        return f"""Odpowiadaj na pytania o produkty.

Dostępne:
{products_context}

Pytanie: {query}"""
    
    @staticmethod
    def recipe_suggestion(
        available_products: str,
        expiring_products: str
    ) -> str:
        """
        Template for recipe suggestions.
        
        Args:
            available_products: Formatted list of available products
            expiring_products: Formatted list of expiring products (priority)
            
        Returns:
            Formatted prompt string
        """
        return f"""Zaproponuj potrawy z dostępnych produktów. Priorityzuj wygasające.

Dostępne:
{available_products}

Wygasające:
{expiring_products}"""
    
    @staticmethod
    def shopping_list(
        current_inventory: str,
        planned_meals: str,
        budget: Optional[float] = None
    ) -> str:
        """
        Template for shopping list generation.
        
        Args:
            current_inventory: Formatted list of current inventory
            planned_meals: List of planned meals/dishes
            budget: Optional budget in PLN
            
        Returns:
            Formatted prompt string
        """
        budget_str = f"{budget:.2f} PLN" if budget else "Nie określono"
        return f"""Generuj listę zakupów.

Mają już:
{current_inventory}

Chce zrobić:
{planned_meals}

Budżet: {budget_str}"""
    
    @staticmethod
    def expiry_usage(expiring_products: str) -> str:
        """
        Template for expiring products usage suggestions.
        
        Args:
            expiring_products: Formatted list of expiring products
            
        Returns:
            Formatted prompt string
        """
        return f"""Pomóż wykorzystać wygasające produkty.

Wygasające:
{expiring_products}"""
    
    @staticmethod
    def nutrition_analysis(
        products: str,
        health_goals: Optional[str] = None
    ) -> str:
        """
        Template for nutritional analysis.
        
        Args:
            products: Formatted list of products to analyze
            health_goals: Optional health goals
            
        Returns:
            Formatted prompt string
        """
        goals_str = health_goals if health_goals else "Brak określonych celów"
        return f"""Przeanalizuj wartość odżywczą.

Produkty:
{products}

Cele: {goals_str}"""
    
    @staticmethod
    def storage_advice(products: str) -> str:
        """
        Template for storage and freezing advice.
        
        Args:
            products: Formatted list of products
            
        Returns:
            Formatted prompt string
        """
        return f"""Podaj poradę na temat przechowywania i mrożenia.

Produkty:
{products}"""
    
    @staticmethod
    def waste_reduction(
        wasted_products: str,
        current_inventory: str
    ) -> str:
        """
        Template for food waste reduction analysis.
        
        Args:
            wasted_products: Formatted list of wasted products
            current_inventory: Formatted list of current inventory
            
        Returns:
            Formatted prompt string
        """
        return f"""Przeanalizuj marnowanie żywności.

Wyrzucone:
{wasted_products}

Bieżące:
{current_inventory}"""
    
    @staticmethod
    def meal_planning(
        available_products: str,
        preferences: Optional[str] = None
    ) -> str:
        """
        Template for meal planning.
        
        Args:
            available_products: Formatted list of available products
            preferences: Optional dietary preferences
            
        Returns:
            Formatted prompt string
        """
        prefs_str = preferences if preferences else "Brak szczególnych preferencji"
        return f"""Zaplanuj menu na tydzień.

Dostępne:
{available_products}

Preferencje:
{prefs_str}"""
    
    @staticmethod
    def budget_optimization(
        shopping_list: str,
        budget_pln: float,
        stores: Optional[str] = None
    ) -> str:
        """
        Template for budget optimization.
        
        Args:
            shopping_list: Formatted shopping list
            budget_pln: Budget in PLN
            stores: Optional list of available stores
            
        Returns:
            Formatted prompt string
        """
        stores_str = stores if stores else "Wszystkie dostępne sklepy"
        return f"""Zaproponuj najtańsze opcje.

Lista:
{shopping_list}

Budżet: {budget_pln:.2f} PLN

Sklepy: {stores_str}"""
    
    @staticmethod
    def dietary_preferences(
        dietary_preferences: str,
        allergens: Optional[str] = None,
        available_products: Optional[str] = None
    ) -> str:
        """
        Template for dietary preferences and allergen considerations.
        
        Args:
            dietary_preferences: Dietary preferences (vegan, vegetarian, etc.)
            allergens: Optional list of allergens to avoid
            available_products: Optional list of available products
            
        Returns:
            Formatted prompt string
        """
        allergens_str = allergens if allergens else "Brak alergii"
        products_str = available_products if available_products else "Wszystkie dostępne produkty"
        return f"""Zaproponuj potrawy dostosowane.

Preferencje:
{dietary_preferences}

Alergie:
{allergens_str}

Dostępne:
{products_str}"""


# Convenience function to get template by key
def get_template(template_key: str) -> callable:
    """
    Get a template function by key.
    
    Args:
        template_key: Template key (e.g., 'product_info', 'recipe_suggestion')
        
    Returns:
        Template function or None if not found
    """
    templates = {
        "product_info": PromptTemplates.product_info,
        "recipe_suggestion": PromptTemplates.recipe_suggestion,
        "shopping_list": PromptTemplates.shopping_list,
        "expiry_usage": PromptTemplates.expiry_usage,
        "nutrition_analysis": PromptTemplates.nutrition_analysis,
        "storage_advice": PromptTemplates.storage_advice,
        "waste_reduction": PromptTemplates.waste_reduction,
        "meal_planning": PromptTemplates.meal_planning,
        "budget_optimization": PromptTemplates.budget_optimization,
        "dietary_preferences": PromptTemplates.dietary_preferences,
    }
    return templates.get(template_key)

