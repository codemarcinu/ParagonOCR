import json
import logging
import re
from typing import Dict, Any, List, Optional
import aiohttp
from app.config import settings

# --- Backward Compatibility Imports ---
try:
    from ollama import Client
    ollama_client = Client(host=settings.OLLAMA_HOST)
except ImportError:
    ollama_client = None

def chat(query: str, context: Dict = None) -> str:
    """
    Simple chat wrapper for RAG/Chat service.
    """
    if not ollama_client:
        return "Error: Ollama client not available."
    
    try:
        # Build prompt from context
        system_msg = "You are a helpful assistant."
        if context and "retrieved_info" in context:
            system_msg += f"\nContext:\n{context['retrieved_info']}"
            
        response = ollama_client.chat(
            model=settings.TEXT_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": query}
            ]
        )
        return response['message']['content']
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return "I encountered an error."

logger = logging.getLogger(__name__)

# --- NOWY, LEPSZY PROMPT ---
SYSTEM_PROMPT = """
Jesteś analitykiem paragonów (OCR). Masz wyciągnąć dane w formacie JSON.

ZASADY EKSTRAKCJI:
1. NAZWA SKLEPU (Krytyczne!):
   - Szukaj w nagłówku. Jeśli widzisz "Jeronimo Martins" -> wpisz "Biedronka".
   - Jeśli widzisz "Lidl" -> wpisz "Lidl".
   - Jeśli widzisz "Kaufland" -> wpisz "Kaufland".
   - Jeśli widzisz "Auchan" -> wpisz "Auchan".
2. POZYCJE (items):
   - Wyciągnij listę zakupów. Ignoruj linie "Suma", "PTU", "Sprzedaż opodatkowana".
   - RABATY: Jeśli pod produktem jest linia z minusem (np. "-4.00"), ODEJMIJ to od ceny produktu powyżej.
3. KWOTY:
   - Używaj kropki (np. 4.50).

FORMAT JSON (zwróć TYLKO to):
{
  "shop_name": "String",
  "date": "YYYY-MM-DD",
  "total_amount": Float,
  "items": [
    { "name": "String", "quantity": Float, "price": Float, "total_price": Float }
  ]
}

Paragon:
"""

class LLMService:
    def __init__(self):
        self.api_url = f"{settings.OLLAMA_HOST}/api/chat"
        self.model = settings.TEXT_MODEL  # np. "bielik"

    async def process_receipt(self, raw_text: str) -> Dict[str, Any]:
        """
        Wysyła tekst OCR do Ollamy i naprawia niedoskonałości modelu lokalnego.
        """
        logger.info(f"Parsing receipt with LLM. OCR text length: {len(raw_text)} chars")
        
        # 1. Budowanie zapytania do Ollamy
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text}
            ],
            "stream": False,
            "format": "json",  # Wymuszenie JSON mode w Ollamie
            "options": {
                "temperature": 0.1,  # Bardzo nisja temperatura dla precyzji
                "num_ctx": 4096
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status != 200:
                        raise Exception(f"Ollama Error: {response.status}")
                    
                    result = await response.json()
                    response_content = result['message']['content']
                    
                    # 2. Parsowanie JSON
                    try:
                        parsed_data = json.loads(response_content)
                    except json.JSONDecodeError:
                        # Fallback: próba wycięcia JSON z markdowna ```json ... ```
                        match = re.search(r'\{.*\}', response_content, re.DOTALL)
                        if match:
                            parsed_data = json.loads(match.group())
                        else:
                            raise ValueError("Model nie zwrócił poprawnego JSON.")

                    # 3. --- SEKCJA NAPRAWCZA (HARD FIX) ---
                    parsed_data = self._fix_shop_name(parsed_data, raw_text)
                    parsed_data = self._fix_total_amount(parsed_data)
                    parsed_data = self._normalize_items(parsed_data)

                    return parsed_data

        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            # Zwracamy pustą strukturę w razie awarii, żeby frontend nie padł
            return {
                "shop_name": "Błąd odczytu",
                "date": None,
                "total_amount": 0.0,
                "items": []
            }

    def _fix_shop_name(self, data: Dict, raw_text: str) -> Dict:
        """
        Naprawia nazwę sklepu na podstawie słów kluczowych w surowym tekście.
        Python ma tu wyższy priorytet niż halucynacje LLM.
        """
        text_lower = raw_text.lower()
        shop_current = data.get("shop_name", "").lower()

        # Lista reguł (Słowo kluczowe w OCR -> Prawidłowa nazwa)
        # Kolejność ma znaczenie! Specyficzne błędy OCR dajemy na górę.
        if "znucham" in text_lower or "auchan" in text_lower or "emchanfl" in text_lower:
            data["shop_name"] = "Auchan"
        elif "kaufland" in text_lower:
            data["shop_name"] = "Kaufland"
        elif "lidl" in text_lower:
            data["shop_name"] = "Lidl"
        elif "zabka" in text_lower or "żabka" in text_lower:
            data["shop_name"] = "Żabka"
        elif "carrefour" in text_lower:
            data["shop_name"] = "Carrefour"
        elif "rossmann" in text_lower:
            data["shop_name"] = "Rossmann"
        elif "biedronka" in text_lower or "jeronimo" in text_lower:
            data["shop_name"] = "Biedronka"
        
        # Jeśli nic nie znaleźliśmy w tekście, a LLM zwrócił "Nieznany", zostawiamy lub wpisujemy domyślny
        if data.get("shop_name") in ["Nieznany sklep", "Unknown", None, ""]:
             data["shop_name"] = "Inny sklep"

        return data

    def _fix_total_amount(self, data: Dict) -> Dict:
        """
        Jeśli Total jest 0.00, obliczamy go z sumy pozycji.
        """
        total = data.get("total_amount", 0.0)
        items = data.get("items", [])
        
        # Oblicz sumę z pozycji
        calculated_sum = sum(item.get("total_price", 0.0) for item in items)
        calculated_sum = round(calculated_sum, 2)

        # Jeśli LLM dał 0 albo null, bierzemy sumę wyliczoną
        if not total or float(total) == 0.0:
            data["total_amount"] = calculated_sum
            logger.info(f"Naprawiono Total Amount: 0.0 -> {calculated_sum}")
        
        return data

    def _normalize_items(self, data: Dict) -> Dict:
        """
        Czyści formatowanie liczb w pozycjach.
        """
        if "items" in data:
            for item in data["items"]:
                # Upewnij się, że liczby to float
                try:
                    item["quantity"] = float(item.get("quantity", 1.0))
                    item["price"] = float(item.get("price", 0.0))
                    item["total_price"] = float(item.get("total_price", 0.0))
                except (ValueError, TypeError):
                    pass
        return data
