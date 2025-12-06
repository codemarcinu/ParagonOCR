"""
Moduł Weekly Meal Planner - planer posiłków na 7 dni.

Funkcjonalności:
- Generowanie planu posiłków na tydzień (7 dni x 3 posiłki)
- Uwzględnianie wygasających produktów
- Integracja z Bielik dla sugestii
"""

from typing import List, Dict, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session

from .bielik import BielikAssistant
from .food_waste_tracker import FoodWasteTracker
from .database import engine, sessionmaker


class MealPlanner:
    """Klasa do generowania tygodniowego planu posiłków."""

    def __init__(self, session: Optional[Session] = None):
        """
        Inicjalizuje planer posiłków.
        
        Args:
            session: Opcjonalna sesja SQLAlchemy. Jeśli None, tworzy nową.
        """
        self.session = session or sessionmaker(bind=engine)()

    def generate_weekly_plan(
        self, start_date: Optional[date] = None, preferences: Optional[str] = None
    ) -> Dict:
        """
        Generuje plan posiłków na 7 dni.
        
        Args:
            start_date: Data rozpoczęcia (domyślnie dzisiaj)
            preferences: Opcjonalne preferencje użytkownika
            
        Returns:
            Słownik z planem posiłków
        """
        if start_date is None:
            start_date = date.today()

        # Pobierz wygasające produkty
        with FoodWasteTracker(self.session) as tracker:
            tracker.update_priorities()
            expiring = tracker.get_expiring_products(
                priority=tracker.PRIORITY_CRITICAL
            )
            expiring.extend(
                tracker.get_expiring_products(priority=tracker.PRIORITY_WARNING)
            )

        # Pobierz dostępne produkty
        with BielikAssistant(self.session) as assistant:
            available_products = assistant.get_available_products()

        # Przygotuj kontekst dla LLM
        expiring_text = ""
        if expiring:
            expiring_text = "\nProdukty wygasające (użyj ich najpierw):\n"
            for p in expiring[:10]:
                days = p.get("days_until_expiry", 0)
                if days is not None and days >= 0:
                    expiring_text += f"- {p['nazwa']} ({p['ilosc']} {p['jednostka']}) - wygasa za {days} dni\n"
                else:
                    expiring_text += f"- {p['nazwa']} ({p['ilosc']} {p['jednostka']}) - już przeterminowany\n"

        available_text = "\nDostępne produkty w magazynie:\n"
        for p in available_products[:30]:
            available_text += f"- {p['nazwa']} ({p['kategoria']}) - {p['total_ilosc']} {p['stany'][0]['jednostka'] if p['stany'] else 'szt'}\n"

        # Generuj plan używając Bielika
        with BielikAssistant(self.session) as assistant:
            plan = self._generate_plan_with_bielik(
                assistant, start_date, expiring_text, available_text, preferences
            )

        return plan

    def _generate_plan_with_bielik(
        self,
        assistant: BielikAssistant,
        start_date: date,
        expiring_text: str,
        available_text: str,
        preferences: Optional[str],
    ) -> Dict:
        """
        Generuje plan posiłków używając Bielika.
        
        Args:
            assistant: Instancja BielikAssistant
            start_date: Data rozpoczęcia
            expiring_text: Tekst z wygasającymi produktami
            available_text: Tekst z dostępnymi produktami
            preferences: Preferencje użytkownika
            
        Returns:
            Słownik z planem posiłków
        """
        from .config_prompts import get_prompt
        from .llm import client
        from .config import Config
        import json

        system_prompt = get_prompt("suggest_dishes")

        # Przygotuj daty dla 7 dni
        dates = [start_date + timedelta(days=i) for i in range(7)]
        dates_text = "\n".join(
            [
                f"- {d.strftime('%A, %Y-%m-%d')}"  # np. "Monday, 2024-01-15"
                for d in dates
            ]
        )

        user_prompt = f"""Wygeneruj plan posiłków na 7 dni dla osoby samotnej.

Daty:
{dates_text}

{expiring_text}

{available_text}

{"Preferencje użytkownika: " + preferences if preferences else ""}

Wygeneruj plan w formacie JSON z następującą strukturą:
{{
  "plan": [
    {{
      "dzien": "YYYY-MM-DD",
      "dzien_tygodnia": "Monday",
      "sniadanie": {{
        "nazwa": "Nazwa potrawy",
        "skladniki": ["składnik1", "składnik2"],
        "czas": "15 min",
        "opis": "Krótki opis"
      }},
      "obiad": {{...}},
      "kolacja": {{...}}
    }}
  ]
}}

Uwzględnij:
- Użyj najpierw wygasających produktów
- Różnorodność posiłków
- Realistyczne porcje dla 1 osoby
- Czas przygotowania"""

        try:
            if not client:
                return self._get_empty_plan(start_date)

            response = client.chat(
                model=Config.TEXT_MODEL,
                format="json",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": 0.7, "num_predict": 3000},
            )

            result = json.loads(response["message"]["content"])
            return result

        except Exception as e:
            # W przypadku błędu, zwróć pusty plan
            return self._get_empty_plan(start_date)

    def _get_empty_plan(self, start_date: date) -> Dict:
        """Zwraca pusty plan posiłków."""
        plan = {"plan": []}
        for i in range(7):
            day_date = start_date + timedelta(days=i)
            plan["plan"].append(
                {
                    "dzien": day_date.isoformat(),
                    "dzien_tygodnia": day_date.strftime("%A"),
                    "sniadanie": {
                        "nazwa": "Brak propozycji",
                        "skladniki": [],
                        "czas": "",
                        "opis": "Nie udało się wygenerować planu",
                    },
                    "obiad": {
                        "nazwa": "Brak propozycji",
                        "skladniki": [],
                        "czas": "",
                        "opis": "Nie udało się wygenerować planu",
                    },
                    "kolacja": {
                        "nazwa": "Brak propozycji",
                        "skladniki": [],
                        "czas": "",
                        "opis": "Nie udało się wygenerować planu",
                    },
                }
            )
        return plan

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


# --- Funkcje pomocnicze ---


def generate_weekly_meal_plan(
    start_date: Optional[date] = None,
    preferences: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict:
    """
    Generuje tygodniowy plan posiłków.
    
    Args:
        start_date: Data rozpoczęcia
        preferences: Preferencje użytkownika
        session: Opcjonalna sesja SQLAlchemy
        
    Returns:
        Słownik z planem posiłków
    """
    with MealPlanner(session) as planner:
        return planner.generate_weekly_plan(start_date, preferences)

