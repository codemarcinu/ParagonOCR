"""
Moduł asystenta AI "Bielik" - asystent kulinarny z RAG.

Funkcjonalności:
- Odpowiadanie na pytania o jedzenie
- Proponowanie potraw na podstawie dostępnych produktów
- Generowanie list zakupów
- Wyszukiwanie produktów w bazie danych (RAG)
"""

import ollama
import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from rapidfuzz import fuzz
from datetime import date, datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

from .database import (
    engine,
    Produkt,
    StanMagazynowy,
    KategoriaProduktu,
    sessionmaker,
)
from .config import Config
from .llm import client
from .config_prompts import get_prompt


class BielikAssistant:
    """Asystent AI Bielik - pomocnik kulinarny z RAG."""

    def __init__(self, session: Optional[Session] = None):
        """
        Inicjalizuje asystenta Bielik.
        
        Args:
            session: Opcjonalna sesja SQLAlchemy. Jeśli None, tworzy nową.
        """
        self.session = session or sessionmaker(bind=engine)()
        self.model_name = Config.TEXT_MODEL

    def _search_products_rag(
        self, query: str, limit: int = 10, min_similarity: int = 40
    ) -> List[Dict]:
        """
        Wyszukuje produkty w bazie danych używając RAG (Retrieval-Augmented Generation).
        Używa fuzzy matching do znalezienia podobnych produktów.
        
        Args:
            query: Zapytanie użytkownika (np. "mleko", "chleb", "co mam do jedzenia")
            limit: Maksymalna liczba wyników
            min_similarity: Minimalne podobieństwo (0-100)
            
        Returns:
            Lista słowników z informacjami o produktach
        """
        # Pobierz wszystkie produkty z bazy
        produkty = (
            self.session.query(Produkt)
            .options(joinedload(Produkt.kategoria))
            .all()
        )

        if not produkty:
            return []

        # Oblicz podobieństwo dla każdego produktu
        scored_products = []
        query_lower = query.lower()

        for produkt in produkty:
            # Sprawdź podobieństwo nazwy produktu
            name_similarity = fuzz.partial_ratio(
                query_lower, produkt.znormalizowana_nazwa.lower()
            )

            # Sprawdź podobieństwo kategorii
            category_similarity = 0
            if produkt.kategoria:
                category_similarity = fuzz.partial_ratio(
                    query_lower, produkt.kategoria.nazwa_kategorii.lower()
                )

            # Weź maksymalne podobieństwo
            max_similarity = max(name_similarity, category_similarity)

            if max_similarity >= min_similarity:
                # Pobierz stan magazynowy
                stany = (
                    self.session.query(StanMagazynowy)
                    .filter_by(produkt_id=produkt.produkt_id)
                    .filter(StanMagazynowy.ilosc > 0)
                    .all()
                )

                total_ilosc = sum(float(stan.ilosc) for stan in stany)
                has_stock = total_ilosc > 0

                scored_products.append(
                    {
                        "produkt": produkt,
                        "similarity": max_similarity,
                        "ilosc": total_ilosc,
                        "has_stock": has_stock,
                        "stany": stany,
                    }
                )

        # Sortuj po podobieństwie (malejąco)
        scored_products.sort(key=lambda x: x["similarity"], reverse=True)

        # Zwróć najlepsze wyniki
        results = []
        for item in scored_products[:limit]:
            produkt = item["produkt"]
            results.append(
                {
                    "nazwa": produkt.znormalizowana_nazwa,
                    "kategoria": (
                        produkt.kategoria.nazwa_kategorii
                        if produkt.kategoria
                        else "Inne"
                    ),
                    "ilosc": item["ilosc"],
                    "has_stock": item["has_stock"],
                    "stany": [
                        {
                            "ilosc": float(stan.ilosc),
                            "jednostka": stan.jednostka_miary or "szt",
                            "data_waznosci": (
                                stan.data_waznosci.isoformat()
                                if stan.data_waznosci
                                else None
                            ),
                            "zamrozone": stan.zamrozone,
                        }
                        for stan in item["stany"]
                    ],
                    "similarity": item["similarity"],
                }
            )

        return results

    def get_available_products(self) -> List[Dict]:
        """
        Pobiera wszystkie dostępne produkty z magazynu (ilość > 0).
        
        Returns:
            Lista słowników z informacjami o dostępnych produktach
        """
        stany = (
            self.session.query(StanMagazynowy)
            .join(Produkt, StanMagazynowy.produkt_id == Produkt.produkt_id)
            .options(joinedload(StanMagazynowy.produkt).joinedload(Produkt.kategoria))
            .filter(StanMagazynowy.ilosc > 0)
            .order_by(StanMagazynowy.data_waznosci)
            .all()
        )

        # Grupuj po produkcie
        products_dict = {}
        for stan in stany:
            produkt_id = stan.produkt_id
            if produkt_id not in products_dict:
                products_dict[produkt_id] = {
                    "nazwa": stan.produkt.znormalizowana_nazwa,
                    "kategoria": (
                        stan.produkt.kategoria.nazwa_kategorii
                        if stan.produkt.kategoria
                        else "Inne"
                    ),
                    "total_ilosc": 0.0,
                    "stany": [],
                }

            products_dict[produkt_id]["total_ilosc"] += float(stan.ilosc)
            products_dict[produkt_id]["stany"].append(
                {
                    "ilosc": float(stan.ilosc),
                    "jednostka": stan.jednostka_miary or "szt",
                    "data_waznosci": (
                        stan.data_waznosci.isoformat()
                        if stan.data_waznosci
                        else None
                    ),
                    "zamrozone": stan.zamrozone,
                }
            )

        return list(products_dict.values())

    def suggest_dishes(
        self, query: Optional[str] = None, max_dishes: int = 5
    ) -> List[Dict]:
        """
        Sugeruje potrawy na podstawie dostępnych produktów.
        
        Args:
            query: Opcjonalne zapytanie użytkownika (np. "obiad", "kolacja", "coś szybkiego")
            max_dishes: Maksymalna liczba potraw do zaproponowania
            
        Returns:
            Lista słowników z propozycjami potraw
        """
        available_products = self.get_available_products()

        if not available_products:
            return [
                {
                    "nazwa": "Brak produktów",
                    "opis": "Nie masz żadnych produktów w magazynie. Dodaj paragony, aby zacząć!",
                    "skladniki": [],
                }
            ]

        # Przygotuj kontekst dla LLM
        products_text = "\n".join(
            [
                f"- {p['nazwa']} ({p['kategoria']}) - {p['total_ilosc']} {p['stany'][0]['jednostka'] if p['stany'] else 'szt'}"
                for p in available_products[:30]  # Limit do 30 produktów
            ]
        )

        system_prompt = get_prompt("suggest_dishes")

        user_prompt = f"""Dostępne produkty w magazynie:
{products_text}

{"Zapytanie użytkownika: " + query if query else "Zaproponuj różnorodne potrawy, które można przygotować z tych produktów."}

Zwróć propozycje w formacie JSON."""

        try:
            if not client:
                return [
                    {
                        "nazwa": "Błąd połączenia",
                        "opis": "Nie można połączyć się z serwerem Ollama.",
                        "skladniki": [],
                    }
                ]

            response = client.chat(
                model=self.model_name,
                format="json",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": 0.7, "num_predict": 2000},
            )

            import json

            result = json.loads(response["message"]["content"])
            potrawy = result.get("potrawy", [])

            # Ogranicz liczbę potraw
            return potrawy[:max_dishes]

        except Exception as e:
            return [
                {
                    "nazwa": "Błąd",
                    "opis": f"Nie udało się wygenerować propozycji: {str(e)}",
                    "skladniki": [],
                }
            ]

    def generate_shopping_list(
        self, dish_name: Optional[str] = None, query: Optional[str] = None
    ) -> Dict:
        """
        Generuje listę zakupów na podstawie potrawy lub zapytania użytkownika.
        
        Args:
            dish_name: Nazwa potrawy, dla której generować listę
            query: Opcjonalne zapytanie użytkownika (np. "co potrzebuję na obiad")
            
        Returns:
            Słownik z listą zakupów
        """
        available_products = self.get_available_products()
        available_names = {p["nazwa"].lower() for p in available_products}

        system_prompt = get_prompt("shopping_list")

        available_text = "\n".join(
            [f"- {p['nazwa']}" for p in available_products[:50]]
        )

        if dish_name:
            user_prompt = f"""Użytkownik chce przygotować: {dish_name}

Dostępne produkty w magazynie (NIE dodawaj ich do listy zakupów):
{available_text}

Wygeneruj listę zakupów - tylko produkty, których brakuje."""
        elif query:
            user_prompt = f"""Zapytanie użytkownika: {query}

Dostępne produkty w magazynie (NIE dodawaj ich do listy zakupów):
{available_text}

Wygeneruj listę zakupów na podstawie zapytania."""
        else:
            user_prompt = f"""Wygeneruj ogólną listę zakupów na podstawie typowych potrzeb kuchennych.

Dostępne produkty w magazynie (NIE dodawaj ich do listy zakupów):
{available_text}"""

        try:
            if not client:
                return {
                    "potrawa": dish_name or "",
                    "produkty": [],
                    "uwagi": "Nie można połączyć się z serwerem Ollama.",
                }

            response = client.chat(
                model=self.model_name,
                format="json",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": 0.5, "num_predict": 1500},
            )

            import json

            result = json.loads(response["message"]["content"])

            # Filtruj produkty, które użytkownik już ma
            produkty = result.get("produkty", [])
            filtered_produkty = [
                p
                for p in produkty
                if p.get("nazwa", "").lower() not in available_names
            ]

            return {
                "potrawa": result.get("potrawa", dish_name or ""),
                "produkty": filtered_produkty,
                "uwagi": result.get("uwagi", ""),
            }

        except Exception as e:
            return {
                "potrawa": dish_name or "",
                "produkty": [],
                "uwagi": f"Błąd podczas generowania listy: {str(e)}",
            }

    def suggest_use_expiring_products(self) -> str:
        """
        Sugeruje jak wykorzystać wygasające produkty.
        
        Returns:
            Sugestia od Bielika
        """
        from .food_waste_tracker import FoodWasteTracker

        with FoodWasteTracker(self.session) as tracker:
            tracker.update_priorities()
            expiring = tracker.get_expiring_products(priority=tracker.PRIORITY_CRITICAL)
            expiring.extend(tracker.get_expiring_products(priority=tracker.PRIORITY_WARNING))

            if not expiring:
                return "✅ Nie masz produktów wymagających pilnego zużycia. Wszystko w porządku!"

            # Przygotuj listę wygasających produktów
            expiring_text = "\n".join(
                [
                    f"- {p['nazwa']} ({p['ilosc']} {p['jednostka']}) - wygasa za {p['days_until_expiry']} dni"
                    if p['days_until_expiry'] is not None and p['days_until_expiry'] >= 0
                    else f"- {p['nazwa']} ({p['ilosc']} {p['jednostka']}) - już przeterminowany"
                    for p in expiring[:10]
                ]
            )

            system_prompt = get_prompt("answer_question")

            user_prompt = f"""Użytkownik ma następujące produkty wygasające w najbliższych dniach:

{expiring_text}

Sugeruj konkretne potrawy lub sposoby wykorzystania tych produktów, aby uniknąć marnotrawstwa. 
Bądź konkretny i praktyczny. Jeśli produkt jest już przeterminowany, zasugeruj bezpieczne sposoby sprawdzenia czy nadal nadaje się do spożycia."""

            try:
                if not client:
                    return "Przepraszam, nie mogę połączyć się z serwerem Ollama."

                response = client.chat(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    options={"temperature": 0.7, "num_predict": 2000},
                )

                return response["message"]["content"].strip()

            except Exception as e:
                return f"Przepraszam, wystąpił błąd: {str(e)}"

    def answer_question(self, question: str) -> str:
        """
        Odpowiada na pytania użytkownika o jedzenie, produkty, gotowanie.
        Używa RAG do wyszukiwania produktów w bazie.
        
        Args:
            question: Pytanie użytkownika
            
        Returns:
            Odpowiedź asystenta
        """
        # Wyszukaj produkty używając RAG
        relevant_products = self._search_products_rag(question, limit=15)
        available_products = self.get_available_products()

        # Przygotuj kontekst
        products_context = ""
        if relevant_products:
            products_context = "\nZnalezione produkty w bazie:\n"
            for p in relevant_products[:10]:
                status = "✅ dostępne" if p["has_stock"] else "❌ brak w magazynie"
                products_context += f"- {p['nazwa']} ({p['kategoria']}) - {status}\n"

        available_context = ""
        if available_products:
            available_context = "\nDostępne produkty w magazynie:\n"
            for p in available_products[:20]:
                available_context += f"- {p['nazwa']} ({p['kategoria']}) - {p['total_ilosc']} {p['stany'][0]['jednostka'] if p['stany'] else 'szt'}\n"

        system_prompt = get_prompt("answer_question")

        user_prompt = f"""Pytanie użytkownika: {question}
{products_context}
{available_context}

Odpowiedz na pytanie użytkownika, korzystając z dostępnych informacji o produktach."""

        try:
            if not client:
                return "Przepraszam, nie mogę połączyć się z serwerem Ollama. Sprawdź, czy serwer działa."

            response = client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": 0.7, "num_predict": 2000},
            )

            return response["message"]["content"].strip()

        except Exception as e:
            logger.error(f"Error processing question: {e}", exc_info=True)
            return "Przepraszam, wystąpił błąd podczas przetwarzania pytania. Spróbuj ponownie."

    def close(self):
        """Zamyka sesję bazy danych."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# --- Funkcje pomocnicze dla łatwego użycia ---


def ask_bielik(question: str, session: Optional[Session] = None) -> str:
    """
    Prosta funkcja do zadawania pytań Bielikowi.
    
    Args:
        question: Pytanie użytkownika
        session: Opcjonalna sesja SQLAlchemy
        
    Returns:
        Odpowiedź asystenta
    """
    with BielikAssistant(session) as assistant:
        return assistant.answer_question(question)


def get_dish_suggestions(
    query: Optional[str] = None, max_dishes: int = 5, session: Optional[Session] = None
) -> List[Dict]:
    """
    Pobiera sugestie potraw od Bielika.
    
    Args:
        query: Opcjonalne zapytanie (np. "obiad", "kolacja")
        max_dishes: Maksymalna liczba potraw
        session: Opcjonalna sesja SQLAlchemy
        
    Returns:
        Lista propozycji potraw
    """
    with BielikAssistant(session) as assistant:
        return assistant.suggest_dishes(query, max_dishes)


def get_shopping_list(
    dish_name: Optional[str] = None,
    query: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict:
    """
    Generuje listę zakupów.
    
    Args:
        dish_name: Nazwa potrawy
        query: Opcjonalne zapytanie
        session: Opcjonalna sesja SQLAlchemy
        
    Returns:
        Słownik z listą zakupów
    """
    with BielikAssistant(session) as assistant:
        return assistant.generate_shopping_list(dish_name, query)

