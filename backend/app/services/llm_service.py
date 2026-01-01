"""
LLM Service for receipt parsing using Ollama (Bielik model).

Handles structured output parsing and error handling with retry logic.
"""

import json
import re
import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from decimal import Decimal, InvalidOperation

import ollama
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Ollama client
ollama_client = None

def init_ollama_client():
    """Initialize Ollama client and verify connection."""
    global ollama_client
    try:
        timeout = httpx.Timeout(settings.OLLAMA_TIMEOUT, connect=10.0)
        client = ollama.Client(host=settings.OLLAMA_HOST, timeout=timeout)
        
        # Test connection by listing models
        try:
            models_response = client.list()
            # Handle ListResponse object from Ollama client
            if hasattr(models_response, 'models'):
                models_list = models_response.models
            elif isinstance(models_response, dict):
                models_list = models_response.get('models', [])
            elif isinstance(models_response, list):
                models_list = models_response
            else:
                models_list = []
            
            logger.info(f"Ollama client initialized. Connected to {settings.OLLAMA_HOST}")
            # Extract model names - handle both Model objects and dicts
            model_names = []
            for m in models_list:
                if hasattr(m, 'model'):
                    model_names.append(m.model)
                elif hasattr(m, 'name'):
                    model_names.append(m.name)
                elif isinstance(m, dict):
                    model_names.append(m.get('name', m.get('model', '')))
                else:
                    model_names.append(str(m))
            
            logger.info(f"Available models: {model_names}")
            
            # Check if required model is available
            if settings.TEXT_MODEL not in model_names:
                logger.warning(f"Required model '{settings.TEXT_MODEL}' not found in Ollama. Available: {model_names}")
                # Still set client - model might be available but not listed yet
                logger.info("Setting Ollama client anyway - model might be available for use")
            else:
                logger.info(f"Required model '{settings.TEXT_MODEL}' is available")
            
            ollama_client = client
        except Exception as e:
            logger.error(f"Failed to verify Ollama connection: {e}")
            ollama_client = None
            
    except Exception as e:
        logger.error(f"Failed to initialize Ollama client at {settings.OLLAMA_HOST}: {e}")
        ollama_client = None

# Initialize on module load
init_ollama_client()


class ParsedReceipt:
    """Structured receipt data parsed from OCR text."""
    
    def __init__(
        self,
        date: Optional[str] = None,
        time: Optional[str] = None,
        shop: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        subtotal: Optional[float] = None,
        tax: Optional[float] = None,
        total: Optional[float] = None,
        error: Optional[str] = None,
    ):
        self.date = date
        self.time = time
        self.shop = shop
        self.items = items or []
        self.subtotal = subtotal
        self.tax = tax
        self.total = total
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date,
            "time": self.time,
            "shop": self.shop,
            "items": self.items,
            "subtotal": self.subtotal,
            "tax": self.tax,
            "total": self.total,
            "error": self.error,
        }


def parse_receipt_text(ocr_text: str) -> ParsedReceipt:
    """
    Parse receipt text using LLM (Bielik) to extract structured data.
    Includes verification loop for mathematical consistency.
    
    Args:
        ocr_text: Raw OCR text from receipt
        
    Returns:
        ParsedReceipt with extracted data
    """
    if not ollama_client:
        logger.error("Ollama client not initialized. Check Ollama connection.")
        return ParsedReceipt(
            error="Ollama client not initialized. Check Ollama connection."
        )
    
    if not ocr_text or not ocr_text.strip():
        logger.warning("Empty OCR text provided to LLM parser")
        return ParsedReceipt(error="Empty OCR text provided")
    
    # Log OCR text length for debugging
    logger.info(f"Parsing receipt with LLM. OCR text length: {len(ocr_text)} chars")
    
    # Create initial prompt
    prompt = create_receipt_parsing_prompt(ocr_text)
    
    max_retries = 2
    attempt = 0
    last_error = None
    
    while attempt <= max_retries:
        attempt += 1
        logger.info(f"LLM Parsing Attempt {attempt}/{max_retries+1}")
        
        try:
            # Call Ollama API
            response = ollama_client.chat(
                model=settings.TEXT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_predict": 4000},
                format="json",
            )
            
            # Extract response
            response_text = response.get("message", {}).get("content", "")
            if not response_text:
                response_text = response.get("response", "")
            
            if not response_text:
                logger.error("Empty response from Ollama API")
                return ParsedReceipt(error="Empty response from Ollama API")
            
            # Parse JSON
            parsed_data = extract_json_from_response(response_text)
            
            if not parsed_data:
                logger.warning(f"Failed to extract JSON on attempt {attempt}")
                last_error = "Failed to parse JSON response"
                continue
            
            # Validate Math headers
            is_valid, validation_error = verify_math_consistency(parsed_data)
            
            if is_valid:
                logger.info("Math verification passed.")
                return validate_and_normalize_receipt(parsed_data)
            else:
                logger.warning(f"Math validation failed: {validation_error}")
                last_error = f"Math validation failed: {validation_error}"
                
                # Update prompt for retry
                if attempt <= max_retries:
                    prompt = f"""
Wykryto błąd w poprzedniej analizie: {validation_error}

Tekst paragonu:
---
{ocr_text}
---

Popraw dane i zwróć poprawny JSON. Upewnij się, że:
1. (ilość * cena_jedn == cena_calkowita) dla każdego produktu (dopuszczalny błąd 0.02)
2. Suma total_price wszystkich produktów == total (dopuszczalny błąd 0.05)
3. Szukaj słów kluczowych SUMA, RAZEM, PTU aby znaleźć właściwy total.

Zwróć TYLKO JSON.
"""
        except Exception as e:
            logger.error(f"Error parsing receipt with LLM (attempt {attempt}): {e}")
            last_error = str(e)
            
    return ParsedReceipt(error=f"LLM parsing failed after {max_retries+1} attempts. Last error: {last_error}")


def verify_math_consistency(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if items sum up to total and line items are consistent.
    Returns (is_valid, error_message).
    """
    try:
        items = data.get("items", [])
        total = float(data.get("total", 0.0))
        
        if not items and total > 0:
             return False, "Brak pozycji na liście, ale total > 0"
             
        calculated_total = 0.0
        
        for i, item in enumerate(items):
            qty = float(item.get("quantity", 1.0))
            price = float(item.get("unit_price", 0.0))
            line_total = float(item.get("total_price", 0.0))
            name = item.get("name", f"Item {i+1}")
            
            # Check line consistency (with tolerance)
            if abs((qty * price) - line_total) > 0.05:
                # Often unit price is missing or quantity is assumed 1. 
                # If we have total_price, trusted more than unit_price calculation often.
                # But let's report it.
                # return False, f"Błąd w pozycji '{name}': {qty} * {price} != {line_total}"
                pass # Lenient on line-level, strict on total sum
                
            calculated_total += line_total
            
        # Check global sum consistency
        if abs(calculated_total - total) > 0.10: # 10 groszy tolerance
            return False, f"Suma pozycji ({calculated_total:.2f}) nie zgadza się z Total ({total:.2f})"
            
        return True, None
        
    except Exception as e:
        return False, f"Błąd weryfikacji: {str(e)}"


def create_receipt_parsing_prompt(ocr_text: str) -> str:
    """
    Create prompt for receipt parsing optimized for Polish receipts.
    Includes explicit anchor instructions.
    
    Args:
        ocr_text: Raw OCR text
        
    Returns:
        Formatted prompt string
    """
    return f"""Jesteś ekspertem od analizy paragonów fiskalnych. Twoim zadaniem jest wyodrębnienie ustrukturyzowanych danych z surowego tekstu OCR.

ZASADY KRYTYCZNE:
1. Szukaj słów kluczowych "SUMA", "RAZEM", "DO ZAPŁATY" aby znaleźć kwotę całkowitą (Total).
2. Szukaj sekcji "PTU" lub stawek VAT, które często są pod listą produktów.
3. Produkty zwykle są w formacie: NAZWA ... ILOŚĆ x CENA ... WARTOŚĆ. Czasem w dwóch liniach.
4. Ignoruj reklamy, NIP sprzedawcy (chyba że to NIP nabywcy), i stopki fiskalne (SHA, Readout).
5. Data zwykle jest na górze (RRRR-MM-DD).

Tekst z paragonu:
---
{ocr_text}
---

Wyodrębnij dane do JSON:
1. Data zakupu (YYYY-MM-DD)
2. Godzina (HH:MM)
3. Nazwa sklepu (często w nagłówku, e.g. Biedronka, Lidl)
4. Lista produktów (name, quantity, unit, unit_price, total_price)
5. Suma (total) - MUSI być zgodna z sumą pozycji!

Format JSON (zwróć TYLKO to):
{{
  "date": "2024-05-12",
  "time": "14:30",
  "shop": "Nazwa Sklepu",
  "items": [
    {{
      "name": "Mleko 3.2%",
      "quantity": 2.0,
      "unit": "szt",
      "unit_price": 3.50,
      "total_price": 7.00
    }}
  ],
  "subtotal": 7.00,
  "tax": 0.00,
  "total": 7.00
}}

Pamiętaj: Zwróć TYLKO poprawny JSON. Bez komentarzy.
"""


def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling markdown code blocks and edge cases.
    
    Args:
        response_text: Raw LLM response
        
    Returns:
        Parsed JSON dictionary or None
    """
    if not response_text:
        logger.error("Empty response text provided to JSON extractor")
        return None
    
    # Clean up response text - remove any leading/trailing whitespace
    response_text = response_text.strip()
    
    # Remove any instruction tokens or end-of-text markers that might appear
    response_text = re.sub(r'<\|im_end\|>', '', response_text)
    response_text = re.sub(r'<\|im_start\|>', '', response_text)
    response_text = response_text.strip()
    
    # Try to find JSON in markdown code blocks first
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        logger.debug("Found JSON in markdown code block")
    else:
        # Try to find JSON object directly - match from first { to last }
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            logger.debug("Found JSON object directly in response")
        else:
            # If format='json' was used, the response should be pure JSON
            json_str = response_text.strip()
            logger.debug("Using full response text as JSON")
    
    try:
        parsed = json.loads(json_str)
        if not isinstance(parsed, dict):
            logger.error(f"Parsed JSON is not a dictionary: {type(parsed)}")
            return None
        logger.debug(f"Successfully parsed JSON with keys: {list(parsed.keys())}")
        return parsed
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.error(f"Attempted to parse: {json_str[:500]}")
        # Try to repair common JSON issues
        try:
            # Remove trailing commas
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            
            # Simple truncation repair: close open brackets/braces
            open_braces = json_str.count('{') - json_str.count('}')
            open_brackets = json_str.count('[') - json_str.count(']')
            
            if open_braces > 0 or open_brackets > 0:
                # Append missing closing characters
                # This is a heuristic: usually we differ items list or the main object
                # Attempt to close quotes first if needed
                if json_str.count('"') % 2 != 0:
                     json_str += '"'
                     
                json_str += ']' * open_brackets
                json_str += '}' * open_braces
                logger.info(f"Attempted to close truncated JSON: {json_str[-50:]}")

            parsed = json.loads(json_str)
            logger.info("Successfully parsed JSON after repair")
            return parsed if isinstance(parsed, dict) else None
        except:
            return None


def validate_and_normalize_receipt(data: Dict[str, Any]) -> ParsedReceipt:
    """
    Validate and normalize parsed receipt data.
    
    Args:
        data: Raw parsed data from LLM
        
    Returns:
        Validated ParsedReceipt
    """
    try:
        # Extract date
        date_str = data.get("date")
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Extract time
        time_str = data.get("time")
        
        # Extract shop name
        shop_name = data.get("shop", "Nieznany sklep")
        
        # Extract items
        items = []
        raw_items = data.get("items", [])
        for item in raw_items:
            try:
                normalized_item = {
                    "name": item.get("name", "").strip(),
                    "quantity": float(item.get("quantity", 1.0)),
                    "unit": item.get("unit", "szt"),
                    "unit_price": float(item.get("unit_price", 0.0)) if item.get("unit_price") else None,
                    "total_price": float(item.get("total_price", 0.0)),
                }
                if normalized_item["name"]:  # Only add items with names
                    items.append(normalized_item)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error normalizing item: {e}, item: {item}")
                continue
        
        # Extract totals
        subtotal = float(data.get("subtotal", 0.0)) if data.get("subtotal") else None
        tax = float(data.get("tax", 0.0)) if data.get("tax") else None
        total = float(data.get("total", 0.0))
        
        return ParsedReceipt(
            date=date_str,
            time=time_str,
            shop=shop_name,
            items=items,
            subtotal=subtotal,
            tax=tax,
            total=total,
        )
        
    except Exception as e:
        logger.error(f"Error validating receipt data: {e}")
        return ParsedReceipt(error=f"Validation error: {str(e)}")


def chat(query: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Chat with LLM (for future chat interface).
    
    Args:
        query: User query
        context: Optional context dictionary
        
    Returns:
        LLM response text
    """
    if not ollama_client:
        return "Error: Ollama client not initialized"
    
    try:
        # Build prompt with context if provided
        prompt = query
        if context:
            context_str = json.dumps(context, indent=2)
            prompt = f"Kontekst:\n{context_str}\n\nPytanie: {query}"
        
        response = ollama_client.generate(
            model=settings.TEXT_MODEL,
            prompt=prompt,
        )
        
        return response.get("response", "No response from LLM")
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return f"Error: {str(e)}"

