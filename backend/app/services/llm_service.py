"""
LLM Service for receipt parsing using Ollama (Bielik model).

Handles structured output parsing and error handling.
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
    
    # Create prompt - Simplified to focus on extraction, not math validation
    prompt = create_receipt_parsing_prompt(ocr_text)
    
    # Single attempt strategy - Retry is too expensive (45s per call)
    try:
        start_time = datetime.now()
        
        # Call Ollama API
        response = ollama_client.chat(
            model=settings.TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1, "num_predict": 4000},
            format="json",
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"LLM request completed in {duration:.2f}s")
        
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
            logger.warning("Failed to extract JSON from LLM response")
            return ParsedReceipt(error="Failed to parse JSON response form LLM")
        
        # Validate Math consistency (Non-blocking)
        is_valid, validation_msg = verify_math_consistency(parsed_data)
        if not is_valid:
            logger.warning(f"Math validation warning: {validation_msg}")
            # We continue anyway, as partial data is better than no data or retries
        
        return validate_and_normalize_receipt(parsed_data)

    except Exception as e:
        logger.error(f"Error parsing receipt with LLM: {e}")
        return ParsedReceipt(error=f"LLM parsing failed: {str(e)}")


def verify_math_consistency(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if items sum up to total and line items are consistent.
    Returns (is_valid, warning_message).
    """
    try:
        items = data.get("items", [])
        total = float(data.get("total", 0.0))
        
        if not items and total > 0:
             return False, "Brak pozycji na liście, ale total > 0"
             
        calculated_total = 0.0
        
        for i, item in enumerate(items):
            try:
                line_total = float(item.get("total_price", 0.0))
                calculated_total += line_total
            except (ValueError, TypeError):
                continue
            
        # Check global sum consistency
        if abs(calculated_total - total) > 0.10: # 10 groszy tolerance
            return False, f"Suma pozycji ({calculated_total:.2f}) nie zgadza się z Total ({total:.2f})"
            
        return True, None
        
    except Exception as e:
        return False, f"Błąd weryfikacji: {str(e)}"


def create_receipt_parsing_prompt(ocr_text: str) -> str:
    return """
Jesteś ekspertem od analizy polskich paragonów fiskalnych (OCR).
Twoim zadaniem jest wyciągnięcie danych strukturalnych z brudnego tekstu OCR.

### ZASADY KRYTYCZNE:
1.  **Format:** Zwróć TYLKO poprawny JSON. Żadnego markdowna (```json), żadnego gadania.
2.  **Sklep:** Rozpoznaj sklep (Biedronka, Lidl, Auchan, Kaufland, Żabka). Jeśli nie ma nazwy, zgadnij po adresie (np. "Jeronimo Martins" -> Biedronka).
3.  **Produkty (Lista 'items'):**
    - Ignoruj linie: "Sprzedaż opodatkowana", "SUMA", "PTU", "Suma PLN", "Rozliczenie płatności".
    - Jeśli nazwa produktu jest ucięta lub dziwna, spróbuj ją naprawić (np. "SerGouda" -> "Ser Gouda").
4.  **RABATY (Ważne!):**
    - W sklepach jak Biedronka, rabat często jest w nowej linii pod produktem, np. "Rabat -4,00".
    - Jeśli widzisz ujemną kwotę, odejmij ją od ceny *poprzedniego* produktu w polu `total_price` (cena końcowa) LUB `price` (cena jednostkowa).
    - NIE dodawaj rabatu jako osobnego produktu z ujemną ceną, chyba że nie wiesz do czego go przypisać.
5.  **Liczby:** Zamień przecinki na kropki (np. "5,99" -> 5.99).

### OCZEKIWANA STRUKTURA JSON:
{
  "shop_name": "Nazwa Sklepu",
  "date": "YYYY-MM-DD",
  "nip": "0000000000" (lub null),
  "total_amount": 0.00,
  "items": [
    {
      "name": "Pełna nazwa produktu",
      "quantity": 1.0,
      "price": 0.00,     // cena jednostkowa (przed rabatem, jeśli możliwy do wyliczenia)
      "total_price": 0.00, // cena końcowa za pozycję (PO RABACIE)
      "category": "inne" // sugerowana kategoria (spożywcze, chemia, warzywa, alkohol)
    }
  ]
}

### TEKST PARAGONU:
""" + ocr_text


def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling markdown code blocks and edge cases.
    """
    if not response_text:
        return None
    
    # Clean up response text
    response_text = response_text.strip()
    
    # Try to find JSON in markdown code blocks first
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find JSON object directly
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Simple repair - often LLM forgets the closing brace
        try:
            if json_str.strip().endswith(']'):
                json_str += '}'
            return json.loads(json_str)
        except:
             # Try simple truncate fix
            try:
                # Close open items list or object
                if '"items": [' in json_str and ']' not in json_str:
                    json_str += ']}'
                elif '}' not in json_str:
                    json_str += '}'
                return json.loads(json_str)
            except:
                logger.error(f"Failed to parse JSON: {json_str[:200]}...")
                return None


def validate_and_normalize_receipt(data: Dict[str, Any]) -> ParsedReceipt:
    """
    Validate and normalize parsed receipt data.
    """
    try:
        # Extract date
        date_str = data.get("date")
        if not date_str or not re.match(r'\d{4}-\d{2}-\d{2}', str(date_str)):
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Extract shop name
        shop_name = data.get("shop")
        if not shop_name or shop_name.lower() == "null":
            shop_name = "Nieznany sklep"
        
        # Extract items
        items = []
        raw_items = data.get("items", [])
        if isinstance(raw_items, list):
            for item in raw_items:
                try:
                    if not isinstance(item, dict): continue
                    
                    name = item.get("name", "").strip()
                    if not name: continue

                    # Flexible number parsing
                    def parse_num(v):
                        if not v: return 0.0
                        if isinstance(v, (int, float)): return float(v)
                        return float(str(v).replace(',', '.').replace(' ', ''))

                    normalized_item = {
                        "name": name,
                        "quantity": parse_num(item.get("quantity", 1)),
                        "unit": item.get("unit", "szt"),
                        "unit_price": parse_num(item.get("unit_price", 0)),
                        "total_price": parse_num(item.get("total_price", 0)),
                        "confidence": 0.9 # Default from LLM
                    }
                    items.append(normalized_item)
                except (ValueError, TypeError):
                    continue
        
        # Extract totals
        def parse_total(v):
            try:
                if isinstance(v, (int, float)): return float(v)
                return float(str(v).replace(',', '.').replace(' ', ''))
            except:
                 return 0.0

        total = parse_total(data.get("total", 0))
        
        # Auto-calculate total if missing but items exist
        if total == 0 and items:
            total = sum(i["total_price"] for i in items)

        return ParsedReceipt(
            date=date_str,
            time=data.get("time"),
            shop=shop_name,
            items=items,
            subtotal=total, # Simplified
            tax=0.0,
            total=total,
        )
        
    except Exception as e:
        logger.error(f"Error validating receipt data: {e}")
        return ParsedReceipt(error=f"Validation error: {str(e)}")


def chat(query: str, context: Optional[Dict[str, Any]] = None) -> str:
    """chat interface."""
    if not ollama_client:
        return "Error: Ollama client not initialized"
    try:
        prompt = query
        if context:
            prompt = f"Kontekst:\n{json.dumps(context)}\n\nPytanie: {query}"
        response = ollama_client.generate(model=settings.TEXT_MODEL, prompt=prompt)
        return response.get("response", "No response")
    except Exception as e:
        return f"Error: {str(e)}"
