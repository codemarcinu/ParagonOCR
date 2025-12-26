"""
LLM Confidence Scoring for ParagonOCR 2.0

Adds confidence scores and alternatives to LLM suggestions for product normalization.

Author: ParagonOCR Team
Version: 2.0
"""

import json
import logging
import re
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

from .config import Config
from .security import sanitize_log_message
from .llm import client, clean_llm_suggestion
from .retry_handler import retry_with_backoff

logger = logging.getLogger(__name__)


@dataclass
class LLMSuggestion:
    """
    LLM suggestion with confidence score and alternatives.
    
    Attributes:
        suggestion: Normalized product name (or None if error)
        confidence: Confidence score (0.0-1.0)
        alternatives: List of alternative suggestions (if any)
        reasoning: Explanation of the suggestion (optional)
    """
    suggestion: Optional[str]
    confidence: float
    alternatives: List[str]
    reasoning: Optional[str] = None


def get_llm_suggestion_with_confidence(
    raw_name: str,
    model_name: str = Config.TEXT_MODEL,
    learning_examples: Optional[List[Tuple[str, str]]] = None
) -> LLMSuggestion:
    """
    Get LLM suggestion with confidence score and alternatives.
    
    Args:
        raw_name: Raw product name from receipt
        model_name: Ollama model name
        learning_examples: Optional learning examples
        
    Returns:
        LLMSuggestion with suggestion, confidence, alternatives, and reasoning
    """
    if not client:
        logger.error("Ollama client not configured")
        return LLMSuggestion(
            suggestion=None,
            confidence=0.0,
            alternatives=[],
            reasoning="Ollama client not available"
        )
    
    system_prompt = """
    Jesteś wirtualnym magazynierem. Twoim zadaniem jest zamiana nazwy z paragonu na KRÓTKĄ, GENERYCZNĄ nazwę produktu do domowej spiżarni.
    
    ZASADY KRYTYCZNE:
    1. USUWASZ marki (np. "Krakus", "Mlekovita", "Winiary" -> USUŃ).
    2. USUWASZ gramaturę i opakowania (np. "1L", "500g", "butelka", "szt" -> USUŃ).
    3. USUWASZ przymiotniki marketingowe (np. "tradycyjne", "babuni", "pyszne", "luksusowe" -> USUŃ).
    4. Zmieniasz na Mianownik Liczby Pojedynczej (np. "Bułki" -> "Bułka", "Jaja" -> "Jajka").
    5. Jeśli produkt to plastikowa torba/reklamówka, zwróć dokładnie słowo: "POMIŃ".
    
    Zwróć odpowiedź w formacie JSON:
    {
      "suggestion": "znormalizowana nazwa",
      "confidence": 0.95,
      "alternatives": ["alternatywa1", "alternatywa2"],
      "reasoning": "krótkie wyjaśnienie"
    }
    
    confidence: 0.0-1.0 (1.0 = bardzo pewny, 0.7-0.95 = średnio pewny, <0.7 = niepewny)
    alternatives: lista alternatywnych nazw (maksymalnie 3)
    reasoning: krótkie wyjaśnienie dlaczego ta nazwa (opcjonalne)
    """
    
    # Build learning examples section
    learning_section = ""
    if learning_examples and len(learning_examples) > 0:
        examples_lines = [
            f'    - "{raw}" -> "{normalized}"'
            for raw, normalized in learning_examples
        ]
        learning_section = "\n    PRZYKŁADY Z POPRZEDNICH WYBORÓW UŻYTKOWNIKA (użyj podobnego stylu normalizacji):\n" + "\n".join(examples_lines) + "\n"
    
    user_prompt = f"""
    PRZYKŁADY OGÓLNE:
    - "Mleko UHT 3,2% Łaciate 1L" -> "Mleko" (confidence: 0.98)
    - "Jaja z wolnego wybiegu L 10szt" -> "Jajka" (confidence: 0.95)
    - "Chleb Baltonowski krojony 500g" -> "Chleb" (confidence: 0.97)
    - "Kajzerka pszenna duża" -> "Bułka" (confidence: 0.90, alternatives: ["Kajzerka"])
    - "Szynka Konserwowa Krakus" -> "Szynka" (confidence: 0.95)
    - "Pomidor gałązka luz" -> "Pomidory" (confidence: 0.85, alternatives: ["Pomidor"])
    - "Coca Cola 0.5L" -> "Napój gazowany" (confidence: 0.80, alternatives: ["Cola"])
    - "Reklamówka mała płatna" -> "POMIŃ" (confidence: 1.0)
{learning_section}
    Nazwa z paragonu: "{raw_name}"
    
    Zwróć TYLKO JSON, bez dodatkowego tekstu.
    """
    
    @retry_with_backoff(
        max_retries=Config.RETRY_MAX_ATTEMPTS,
        initial_delay=Config.RETRY_INITIAL_DELAY,
        backoff_factor=Config.RETRY_BACKOFF_FACTOR,
        max_delay=Config.RETRY_MAX_DELAY,
        jitter=Config.RETRY_JITTER,
    )
    def _call_llm():
        return client.chat(
            model=model_name,
            format="json",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    
    try:
        response = _call_llm()
        response_text = response["message"]["content"].strip()
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = re.sub(r"```json\n?", "", response_text)
                response_text = re.sub(r"```\n?$", "", response_text)
            
            result = json.loads(response_text)
            
            # Extract fields
            suggestion = result.get("suggestion")
            if suggestion:
                suggestion = clean_llm_suggestion(suggestion)
            
            confidence = float(result.get("confidence", 0.5))
            # Clamp confidence to [0.0, 1.0]
            confidence = max(0.0, min(1.0, confidence))
            
            alternatives = result.get("alternatives", [])
            if not isinstance(alternatives, list):
                alternatives = []
            # Clean alternatives
            alternatives = [clean_llm_suggestion(alt) for alt in alternatives if alt]
            
            reasoning = result.get("reasoning")
            
            return LLMSuggestion(
                suggestion=suggestion if suggestion else None,
                confidence=confidence,
                alternatives=alternatives,
                reasoning=reasoning
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                f"Failed to parse confidence response: {sanitize_log_message(str(e))}"
            )
            logger.debug(f"Response text: {sanitize_log_message(response_text, max_length=500)}")
            # Fallback: return suggestion without confidence
            suggestion = clean_llm_suggestion(response_text) if response_text else None
            return LLMSuggestion(
                suggestion=suggestion,
                confidence=0.5,  # Default medium confidence
                alternatives=[],
                reasoning="Failed to parse confidence from response"
            )
    except Exception as e:
        logger.error(
            f"Error getting LLM suggestion with confidence: {sanitize_log_message(str(e))}"
        )
        return LLMSuggestion(
            suggestion=None,
            confidence=0.0,
            alternatives=[],
            reasoning=f"Error: {sanitize_log_message(str(e))}"
        )


def get_batch_suggestions_with_confidence(
    raw_names: List[str],
    model_name: str = Config.TEXT_MODEL,
    learning_examples: Optional[List[Tuple[str, str]]] = None
) -> Dict[str, LLMSuggestion]:
    """
    Get batch LLM suggestions with confidence scores.
    
    Args:
        raw_names: List of raw product names
        model_name: Ollama model name
        learning_examples: Optional learning examples
        
    Returns:
        Dictionary mapping raw_name -> LLMSuggestion
    """
    if not raw_names:
        return {}
    
    if not client:
        logger.error("Ollama client not configured")
        return {
            name: LLMSuggestion(
                suggestion=None,
                confidence=0.0,
                alternatives=[],
                reasoning="Ollama client not available"
            )
            for name in raw_names
        }
    
    system_prompt = """
    Jesteś wirtualnym magazynierem. Twoim zadaniem jest zamiana nazw z paragonu na KRÓTKIE, GENERYCZNE nazwy produktów do domowej spiżarni.
    
    ZASADY KRYTYCZNE:
    1. USUWASZ marki (np. "Krakus", "Mlekovita", "Winiary" -> USUŃ).
    2. USUWASZ gramaturę i opakowania (np. "1L", "500g", "butelka", "szt" -> USUŃ).
    3. USUWASZ przymiotniki marketingowe (np. "tradycyjne", "babuni", "pyszne", "luksusowe" -> USUŃ).
    4. Zmieniasz na Mianownik Liczby Pojedynczej (np. "Bułki" -> "Bułka", "Jaja" -> "Jajka").
    5. Jeśli produkt to plastikowa torba/reklamówka, zwróć dokładnie słowo: "POMIŃ".
    
    Zwróć odpowiedź w formacie JSON, gdzie klucz to surowa nazwa, a wartość to obiekt z suggestion, confidence, alternatives, reasoning.
    Przykład:
    {
      "Mleko UHT 3,2% Łaciate 1L": {
        "suggestion": "Mleko",
        "confidence": 0.98,
        "alternatives": [],
        "reasoning": "Standardowe mleko UHT"
      },
      "Jaja z wolnego wybiegu L 10szt": {
        "suggestion": "Jajka",
        "confidence": 0.95,
        "alternatives": [],
        "reasoning": "Jaja kurze"
      },
      "Kajzerka pszenna duża": {
        "suggestion": "Bułka",
        "confidence": 0.90,
        "alternatives": ["Kajzerka"],
        "reasoning": "Kajzerka to rodzaj bułki"
      }
    }
    """
    
    # Build learning examples section
    learning_section = ""
    if learning_examples and len(learning_examples) > 0:
        examples_lines = [
            f'    - "{raw}" -> "{normalized}"'
            for raw, normalized in learning_examples
        ]
        learning_section = "\n    PRZYKŁADY Z POPRZEDNICH WYBORÓW UŻYTKOWNIKA (użyj podobnego stylu normalizacji):\n" + "\n".join(examples_lines) + "\n"
    
    # Format product list
    products_list = "\n".join([f'    - "{name}"' for name in raw_names])
    
    user_prompt = f"""
    PRZYKŁADY OGÓLNE:
    - "Mleko UHT 3,2% Łaciate 1L" -> "Mleko" (confidence: 0.98)
    - "Jaja z wolnego wybiegu L 10szt" -> "Jajka" (confidence: 0.95)
    - "Chleb Baltonowski krojony 500g" -> "Chleb" (confidence: 0.97)
    - "Reklamówka mała płatna" -> "POMIŃ" (confidence: 1.0)
{learning_section}
    Znormalizuj następujące produkty (zwróć JSON z mapowaniem):
{products_list}
    
    Zwróć TYLKO JSON, bez dodatkowego tekstu.
    """
    
    @retry_with_backoff(
        max_retries=Config.RETRY_MAX_ATTEMPTS,
        initial_delay=Config.RETRY_INITIAL_DELAY,
        backoff_factor=Config.RETRY_BACKOFF_FACTOR,
        max_delay=Config.RETRY_MAX_DELAY,
        jitter=Config.RETRY_JITTER,
    )
    def _call_batch_llm():
        return client.chat(
            model=model_name,
            format="json",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    
    try:
        response = _call_batch_llm()
        response_text = response["message"]["content"].strip()
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                response_text = re.sub(r"```json\n?", "", response_text)
                response_text = re.sub(r"```\n?$", "", response_text)
            
            batch_results = json.loads(response_text)
            
            # Convert to LLMSuggestion objects
            result_dict = {}
            for raw_name in raw_names:
                item = batch_results.get(raw_name)
                if item and isinstance(item, dict):
                    suggestion = item.get("suggestion")
                    if suggestion:
                        suggestion = clean_llm_suggestion(suggestion)
                    
                    confidence = float(item.get("confidence", 0.5))
                    confidence = max(0.0, min(1.0, confidence))
                    
                    alternatives = item.get("alternatives", [])
                    if not isinstance(alternatives, list):
                        alternatives = []
                    alternatives = [clean_llm_suggestion(alt) for alt in alternatives if alt]
                    
                    reasoning = item.get("reasoning")
                    
                    result_dict[raw_name] = LLMSuggestion(
                        suggestion=suggestion if suggestion else None,
                        confidence=confidence,
                        alternatives=alternatives,
                        reasoning=reasoning
                    )
                else:
                    # Fallback: try to extract just the suggestion string
                    if isinstance(item, str):
                        suggestion = clean_llm_suggestion(item)
                        result_dict[raw_name] = LLMSuggestion(
                            suggestion=suggestion if suggestion else None,
                            confidence=0.5,
                            alternatives=[],
                            reasoning="Parsed as simple string"
                        )
                    else:
                        result_dict[raw_name] = LLMSuggestion(
                            suggestion=None,
                            confidence=0.0,
                            alternatives=[],
                            reasoning="No valid response"
                        )
            
            return result_dict
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                f"Failed to parse batch confidence response: {sanitize_log_message(str(e))}"
            )
            logger.debug(f"Response text: {sanitize_log_message(response_text, max_length=500)}")
            # Fallback: return None for all
            return {
                name: LLMSuggestion(
                    suggestion=None,
                    confidence=0.0,
                    alternatives=[],
                    reasoning="Failed to parse batch response"
                )
                for name in raw_names
            }
    except Exception as e:
        logger.error(
            f"Error getting batch LLM suggestions with confidence: {sanitize_log_message(str(e))}"
        )
        return {
            name: LLMSuggestion(
                suggestion=None,
                confidence=0.0,
                alternatives=[],
                reasoning=f"Error: {sanitize_log_message(str(e))}"
            )
            for name in raw_names
        }


def get_confidence_color(confidence: float) -> str:
    """
    Get color indicator for confidence score.
    
    Args:
        confidence: Confidence score (0.0-1.0)
        
    Returns:
        Color indicator string (✅ Green, ⚠️ Yellow, ❌ Red)
    """
    if confidence >= 0.95:
        return "✅"  # Green - High confidence
    elif confidence >= 0.7:
        return "⚠️"  # Yellow - Medium confidence
    else:
        return "❌"  # Red - Low confidence

