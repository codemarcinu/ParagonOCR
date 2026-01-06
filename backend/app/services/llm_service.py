import json
import logging
import re
from typing import Dict, Any
import aiohttp
import requests
from app.config import settings

logger = logging.getLogger(__name__)

# Prompt zoptymalizowany pod Bielika i polskie realia
SYSTEM_PROMPT = """
Jesteś precyzyjnym asystentem AI do ekstrakcji danych strukturalnych z paragonów fiskalnych.
Twoim zadaniem jest przeanalizowanie tekstu surowego paragonu i zwrócenie danych TYLKO w formacie JSON.

WEJŚCIE:
Otrzymasz tekst paragonu odczytany przez wysokiej jakości OCR. Tekst jest zazwyczaj poprawny, ale może zawierać szum informacyjny (reklamy, kody kasjera, stopki).

ZASADY EKSTRAKCJI:
1. Sklep: Podaj oficjalną nazwę (np. "Biedronka", "Lidl", "Auchan"). Jeśli jest inna nazwa prawna (np. "Jeronimo Martins"), użyj nazwy marketingowej.
2. Data: Format YYYY-MM-DD. Szukaj daty sprzedaży.
3. NIP: Wyciągnij numer NIP sprzedawcy (same cyfry lub z kreskami).
4. Pozycje (items):
   - Ignoruj linie typu "SPRZEDAŻ OPODATKOWANA", "SUMA PLN", "PTU".
   - Ignoruj rabaty, jeśli są osobną pozycją zmniejszającą sumę (chyba że są wyraźnie przypisane do produktu, wtedy podaj cenę końcową).
   - "quantity": domyślnie 1.0, chyba że w linii jest inna ilość (np. "2 x 3.50").
   - "price": cena jednostkowa lub wartość końcowa pozycji. Używaj kropki jako separatora (np. 4.50).
5. Suma (total_amount): Kwota "DO ZAPŁATY" lub "SUMA".

FORMAT WYJŚCIOWY (JSON):
{
    "shop_name": "string",
    "date": "YYYY-MM-DD",
    "nip": "string",
    "items": [
        {
            "name": "string",
            "quantity": float,
            "price": float
        }
    ],
    "total_amount": float
}

WAŻNE:
- Nie dodawaj żadnych komentarzy ani tekstu przed/po JSON.
- Jeśli jakiegoś pola nie ma, wpisz null.
- Zwracaj czysty JSON gotowy do parsowania.
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

# --- Sync Client for Normalization Service ---
class OllamaClient:
    def __init__(self, host: str):
        self.host = host

    def generate(self, model: str, prompt: str, options: Dict = None) -> Dict:
        url = f"{self.host}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options or {}
        }
        try:
            resp = requests.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(f"Ollama error: {resp.status_code} - {resp.text}")
                return {"response": ""}
            return resp.json()
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            return {"response": ""}

ollama_client = OllamaClient(settings.OLLAMA_HOST)

def chat(query: str, context: Dict = None) -> str:
    """
    Simple chat interface for the RAG system.
    """
    prompt = query
    if context and context.get("retrieved_info"):
        prompt = f"Kontekst:\n{context['retrieved_info']}\n\nPytanie: {query}"
    
    response = ollama_client.generate(
        model=settings.OLLAMA_MODEL,
        prompt=prompt,
        options={"temperature": 0.7}
    )
    return response.get("response", "Błąd komunikacji z modelem.")
