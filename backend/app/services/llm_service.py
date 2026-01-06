import json
import logging
import re
from typing import Dict, Any
import aiohttp
from app.config import settings

logger = logging.getLogger(__name__)

# Prompt zoptymalizowany pod Bielika i polskie realia
SYSTEM_PROMPT = """
Jesteś analitykiem paragonów (OCR). Twoim celem jest wyciągnięcie danych JSON.

### INSTRUKCJE DLA SKLEPÓW:
1. SZUKANIE NAZWY:
   - "Jeronimo Martins" -> Zapisz jako "Biedronka"
   - "Lidl" -> Zapisz jako "Lidl"
   - "Kaufland" -> Zapisz jako "Kaufland"
   - "Auchan" -> Zapisz jako "Auchan"
   - "Żabka" -> Zapisz jako "Żabka"
   - "Carrefour" -> Zapisz jako "Carrefour"

2. POZYCJE (items):
   - Wyciągnij nazwę, ilość i cenę KOŃCOWĄ (po rabacie).
   - RABATY (Biedronka/Lidl): Jeśli pod produktem jest linia "Rabat" lub kwota z minusem (np. -4.00), ODEJMIJ ją od ceny produktu powyżej. Nie dodawaj rabatu jako osobnej pozycji.

3. DATA: Format YYYY-MM-DD.

Format wyjściowy (JSON Only):
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
        self.model = settings.OLLAMA_MODEL

    async def process_receipt(self, raw_text: str) -> Dict[str, Any]:
        """
        Wysyła OCR do LLM, a potem Python naprawia błędy modelu.
        """
        logger.info(f"LLM: Analiza tekstu ({len(raw_text)} znaków)...")
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text}
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_ctx": 2048,
                "num_predict": 1000, # Limit tokenów wyjściowych
                "num_gpu": 99,       # <--- KLUCZOWE: Wymuś 99 warstw na GPU (wszystkie)
                "num_thread": 4      # Ogranicz wątki CPU, żeby nie dławić systemu
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status != 200:
                        raise Exception(f"Ollama Error: {response.status}")
                    
                    result = await response.json()
                    content = result['message']['content']
                    
                    # Parsowanie JSON (z obsługą błędów formatowania)
                    try:
                        parsed_data = json.loads(content)
                    except json.JSONDecodeError:
                        # Ratunek regexem jeśli model dodał tekst przed klamrą
                        match = re.search(r'\{.*\}', content, re.DOTALL)
                        if match:
                            parsed_data = json.loads(match.group())
                        else:
                            # Ostateczny fallback - pusty paragon
                            parsed_data = {}

                    # --- LOGIKA NAPRAWCZA (PYTHON GLUE) ---
                    # To naprawia błędy, których model AI nie widzi
                    parsed_data = self._fix_shop_name(parsed_data, raw_text)
                    parsed_data = self._fix_financials(parsed_data)
                    
                    return parsed_data

        except Exception as e:
            logger.error(f"LLM processing failed: {e}")
            return self._get_empty_structure()

    def _fix_shop_name(self, data: Dict, raw_text: str) -> Dict:
        """
        Autorytatywna naprawa nazwy sklepu na podstawie słów kluczowych OCR.
        Rozwiązuje problem: Auchan -> ZNUCHAM, Biedronka -> Jeronimo.
        """
        text_lower = raw_text.lower()
        
        # Lista priorytetowa (Specyficzne błędy OCR na górze)
        if any(x in text_lower for x in ["znucham", "auchan", "emchanfl", "ruchan"]):
            data["shop_name"] = "Auchan"
        elif any(x in text_lower for x in ["biedronka", "jeronimo", "jemp"]):
            data["shop_name"] = "Biedronka"
        elif "lidl" in text_lower:
            data["shop_name"] = "Lidl"
        elif "kaufland" in text_lower:
            data["shop_name"] = "Kaufland"
        elif any(x in text_lower for x in ["zabka", "żabka"]):
            data["shop_name"] = "Żabka"
        elif "carrefour" in text_lower:
            data["shop_name"] = "Carrefour"
        elif "rossmann" in text_lower:
            data["shop_name"] = "Rossmann"
        elif "stokrotka" in text_lower:
            data["shop_name"] = "Stokrotka"
            
        # Domyślna wartość
        if not data.get("shop_name"):
            data["shop_name"] = "Inny sklep"
            
        return data

    def _fix_financials(self, data: Dict) -> Dict:
        """
        Naprawia formatowanie liczb i przelicza sumę całkowitą, 
        jeśli LLM zwrócił 0.00.
        """
        items = data.get("items", [])
        calculated_total = 0.0
        
        if items:
            for item in items:
                # Konwersja na float i zaokrąglenie
                try:
                    price = float(item.get("price", 0))
                    qty = float(item.get("quantity", 1))
                    
                    # Jeśli total_price jest pusty, wylicz go
                    if not item.get("total_price"):
                        item["total_price"] = price * qty
                    
                    item["total_price"] = round(float(item["total_price"]), 2)
                    item["price"] = round(price, 2)
                    calculated_total += item["total_price"]
                except (ValueError, TypeError):
                    continue
        
        # Nadpisz Total Amount jeśli jest błędny/pusty
        current_total = data.get("total_amount")
        try:
             current_total = float(current_total)
        except (ValueError, TypeError):
            current_total = 0.0

        if current_total == 0.0 and calculated_total > 0:
            data["total_amount"] = round(calculated_total, 2)
            logger.info(f"Naprawiono Total Amount (z sumy pozycji): {data['total_amount']}")
        else:
            data["total_amount"] = round(current_total, 2)
            
        return data

    def _get_empty_structure(self):
        return {
            "shop_name": "Błąd przetwarzania",
            "date": None,
            "total_amount": 0.0,
            "items": []
        }
