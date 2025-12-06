"""
Moduł do zarządzania promptami systemowymi dla Bielika.
Prompty są przechowywane w pliku JSON i mogą być edytowane przez GUI.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional


# Ścieżka do pliku z promptami (w folderze data)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_FILE = os.path.join(project_root, "data", "bielik_prompts.json")


# Domyślne prompty
DEFAULT_PROMPTS = {
    "answer_question": """Jesteś Bielik - asystentem kulinarnym AI. Odpowiadasz na pytania użytkownika o jedzenie, gotowanie, produkty i żywność.

Zasady:
1. Bądź pomocny, przyjazny i konkretny
2. Używaj informacji o produktach z bazy danych (RAG)
3. Jeśli użytkownik pyta "co mam do jedzenia", zaproponuj potrawy na podstawie dostępnych produktów
4. Jeśli użytkownik pyta o konkretny produkt, użyj informacji z bazy
5. Odpowiadaj po polsku, w sposób naturalny i zrozumiały
6. Możesz proponować przepisy, sugestie kulinarne, porady dotyczące przechowywania żywności""",

    "suggest_dishes": """Jesteś asystentem kulinarnym Bielik. Twoim zadaniem jest proponowanie potraw na podstawie dostępnych produktów.

Zasady:
1. Proponuj tylko potrawy, które można przygotować z dostępnych produktów
2. Jeśli brakuje jakiegoś składnika, możesz zasugerować alternatywę lub pominięcie
3. Uwzględniaj różnorodność (obiad, kolacja, śniadanie)
4. Zwracaj odpowiedź w formacie JSON z listą potraw

Format odpowiedzi:
{
  "potrawy": [
    {
      "nazwa": "Nazwa potrawy",
      "opis": "Krótki opis jak przygotować",
      "skladniki": ["składnik1", "składnik2", ...],
      "czas_przygotowania": "około X minut",
      "trudnosc": "łatwa/średnia/trudna"
    }
  ]
}""",

    "shopping_list": """Jesteś asystentem kulinarnym Bielik. Generujesz listy zakupów na podstawie potraw lub zapytań użytkownika.

Zasady:
1. Zwracaj tylko produkty, których użytkownik NIE MA w magazynie
2. Uwzględniaj ilości (np. "500g mąki", "1kg ziemniaków")
3. Grupuj produkty według kategorii (Warzywa, Mięso, Nabiał, itp.)
4. Zwracaj odpowiedź w formacie JSON

Format odpowiedzi:
{
  "potrawa": "Nazwa potrawy (jeśli dotyczy)",
  "produkty": [
    {
      "nazwa": "Nazwa produktu",
      "ilosc": "ilość z jednostką (np. 500g, 1kg, 2 szt)",
      "kategoria": "Kategoria produktu",
      "priorytet": "wysoki/średni/niski"
    }
  ],
  "uwagi": "Dodatkowe uwagi lub sugestie"
}"""
}


def load_prompts() -> Dict[str, str]:
    """
    Ładuje prompty z pliku JSON. Jeśli plik nie istnieje, tworzy go z domyślnymi wartościami.
    
    Returns:
        Słownik z promptami (klucz: nazwa promptu, wartość: treść promptu)
    """
    # Upewnij się, że folder data istnieje
    data_dir = os.path.dirname(PROMPTS_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Jeśli plik nie istnieje, utwórz go z domyślnymi wartościami
    if not os.path.exists(PROMPTS_FILE):
        save_prompts(DEFAULT_PROMPTS)
        return DEFAULT_PROMPTS.copy()
    
    try:
        with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
            prompts = json.load(f)
        
        # Upewnij się, że wszystkie wymagane prompty istnieją
        for key, default_value in DEFAULT_PROMPTS.items():
            if key not in prompts:
                prompts[key] = default_value
        
        return prompts
    except (json.JSONDecodeError, IOError) as e:
        print(f"Błąd podczas ładowania promptów: {e}. Używam domyślnych wartości.")
        return DEFAULT_PROMPTS.copy()


def save_prompts(prompts: Dict[str, str]) -> bool:
    """
    Zapisuje prompty do pliku JSON.
    
    Args:
        prompts: Słownik z promptami do zapisania
        
    Returns:
        True jeśli zapis się powiódł, False w przeciwnym razie
    """
    try:
        # Upewnij się, że folder data istnieje
        data_dir = os.path.dirname(PROMPTS_FILE)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        
        return True
    except IOError as e:
        print(f"Błąd podczas zapisywania promptów: {e}")
        return False


def get_prompt(prompt_name: str) -> str:
    """
    Pobiera konkretny prompt po nazwie.
    
    Args:
        prompt_name: Nazwa promptu (np. "answer_question", "suggest_dishes", "shopping_list")
        
    Returns:
        Treść promptu lub domyślny prompt jeśli nie znaleziono
    """
    prompts = load_prompts()
    return prompts.get(prompt_name, DEFAULT_PROMPTS.get(prompt_name, ""))


def reset_prompts_to_default() -> bool:
    """
    Resetuje wszystkie prompty do wartości domyślnych.
    
    Returns:
        True jeśli reset się powiódł, False w przeciwnym razie
    """
    return save_prompts(DEFAULT_PROMPTS.copy())







