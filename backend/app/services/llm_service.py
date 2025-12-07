"""
LLM Service for receipt parsing using Ollama (Bielik model).

Handles structured output parsing and error handling with retry logic.
"""

import json
import re
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from decimal import Decimal, InvalidOperation

import ollama
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Ollama client
try:
    timeout = httpx.Timeout(settings.OLLAMA_TIMEOUT, connect=10.0)
    ollama_client = ollama.Client(host=settings.OLLAMA_HOST, timeout=timeout)
except Exception as e:
    logger.error(f"Failed to connect to Ollama at {settings.OLLAMA_HOST}: {e}")
    ollama_client = None


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
        return ParsedReceipt(
            error="Ollama client not initialized. Check Ollama connection."
        )
    
    if not ocr_text or not ocr_text.strip():
        return ParsedReceipt(error="Empty OCR text provided")
    
    # Create prompt for receipt parsing
    prompt = create_receipt_parsing_prompt(ocr_text)
    
    try:
        # Call Ollama API
        response = ollama_client.generate(
            model=settings.TEXT_MODEL,
            prompt=prompt,
            options={
                "temperature": 0.1,  # Low temperature for structured output
                "num_predict": 2000,  # Max tokens for response
            },
        )
        
        response_text = response.get("response", "")
        
        # Parse JSON from response
        parsed_data = extract_json_from_response(response_text)
        
        if not parsed_data:
            return ParsedReceipt(
                error="Failed to extract JSON from LLM response"
            )
        
        # Validate and normalize parsed data
        return validate_and_normalize_receipt(parsed_data)
        
    except Exception as e:
        logger.error(f"Error parsing receipt with LLM: {e}")
        return ParsedReceipt(error=f"LLM parsing error: {str(e)}")


def create_receipt_parsing_prompt(ocr_text: str) -> str:
    """
    Create prompt for receipt parsing optimized for Polish receipts.
    
    Args:
        ocr_text: Raw OCR text
        
    Returns:
        Formatted prompt string
    """
    return f"""Analizuj tekst z paragonu i wyodrębnij następujące informacje:
1. Data i godzina zakupu
2. Nazwa sklepu
3. Lista produktów: nazwa, ilość, jednostka miary, cena jednostkowa, cena całkowita
4. Suma częściowa (subtotal)
5. Podatek VAT (jeśli widoczny)
6. Suma całkowita

Tekst z paragonu:
---
{ocr_text}
---

Zwróć TYLKO poprawny JSON w następującym formacie (bez dodatkowego tekstu):
{{
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "shop": "Nazwa Sklepu",
  "items": [
    {{
      "name": "Nazwa produktu",
      "quantity": 1.0,
      "unit": "szt",
      "unit_price": 19.99,
      "total_price": 19.99
    }}
  ],
  "subtotal": 99.99,
  "tax": 0.00,
  "total": 99.99
}}

Jeśli jakiejś informacji nie możesz wyodrębnić, użyj null dla wartości opcjonalnych.
Dla daty użyj formatu YYYY-MM-DD. Jeśli data nie jest dostępna, użyj dzisiejszej daty.
Dla czasu użyj formatu HH:MM (24h).
"""


def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling markdown code blocks.
    
    Args:
        response_text: Raw LLM response
        
    Returns:
        Parsed JSON dictionary or None
    """
    # Remove markdown code blocks if present
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find JSON object directly
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text.strip()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}, text: {response_text[:200]}")
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

