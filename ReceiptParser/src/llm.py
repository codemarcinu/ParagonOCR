import ollama
import base64
import json
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation

# --- Klient Ollama ---
# Globalny klient do komunikacji z serwerem Ollama.
# Upewnij się, że kontener Docker z Ollamą jest uruchomiony.
from .config import Config

# --- Klient Ollama ---
# Globalny klient do komunikacji z serwerem Ollama.
# Upewnij się, że kontener Docker z Ollamą jest uruchomiony.
try:
    client = ollama.Client(host=Config.OLLAMA_HOST)
    # Sprawdzenie połączenia przy starcie
    # client.list()
except Exception as e:
    print(
        f"BŁĄD: Nie można połączyć się z Ollama na {Config.OLLAMA_HOST}. Upewnij się, że usługa działa. Szczegóły: {e}"
    )
    client = None

# --- Normalizacja Nazw Produktów ---


def get_llm_suggestion(
    raw_name: str, model_name: str = Config.TEXT_MODEL
) -> str | None:
    """
    Używa modelu językowego do normalizacji "brudnej" nazwy produktu.

    Args:
        raw_name: Surowa nazwa produktu z paragonu.
        model_name: Nazwa modelu Ollama do użycia.

    Returns:
        Znormalizowana nazwa produktu jako string, lub None w przypadku błędu.
    """
    if not client:
        print("BŁĄD: Klient Ollama nie jest skonfigurowany.")
        return None

    system_prompt = (
        "Jesteś ekspertem w czyszczeniu i normalizowaniu nazw produktów z paragonów. "
        "Twoim zadaniem jest przyjąć surową, często skróconą lub z błędami, nazwę produktu "
        "i zwrócić TYLKO czystą, pełną, ludzką wersję tej nazwy. "
        "Nie dodawaj żadnych wyjaśnień, komentarzy ani znaków formatowania. "
        "Odpowiedz tylko i wyłącznie znormalizowaną nazwą."
    )

    # Przykłady few-shot uczące model oczekiwanego formatu
    user_prompt = f"""
    Przykłady:
    - Raw: "JajaL Z BIEG.M" -> Clean: "Jaja z wolnego wybiegu M"
    - Raw: "PomKroNaszSpiż240g" -> Clean: "Pomidory krojone Nasza Spiżarnia 240g"
    - Raw: "SER GOŁDA TŁ" -> Clean: "Ser Gouda tłusty"
    - Raw: "Sok Pomarańcz.1L" -> Clean: "Sok pomarańczowy 1L"
    - Raw: "Masło Polskie 82%" -> Clean: "Masło Polskie 82%"

    Zadanie:
    - Raw: "{raw_name}" -> Clean:
    """

    try:
        response = client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        suggestion = response["message"]["content"].strip()
        # Czasami model może zwrócić nazwę w cudzysłowach, usuwamy je
        return suggestion.strip("'\"")
    except Exception as e:
        print(
            f"BŁĄD: Wystąpił problem podczas komunikacji z modelem '{model_name}': {e}"
        )
        return None


# --- Parsowanie Całego Paragonu z Obrazu ---


def _extract_json_from_response(response_text: str) -> dict | None:
    """Wyszukuje i parsuje blok JSON z odpowiedzi tekstowej modelu."""
    # Wzorzec do znalezienia bloku JSON, nawet jeśli jest otoczony innym tekstem
    match = re.search(r"```json\n(\{.*?\})\n```|\{.*?\}|", response_text, re.DOTALL)
    if match:
        # Wybierz pierwszą grupę, która nie jest pusta
        json_str = next((g for g in match.groups() if g is not None), match.group(0))
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(
                f"BŁĄD: Nie udało się sparsować JSON-a z odpowiedzi LLM. Szczegóły: {e}"
            )
            print(f"Otrzymany tekst: {json_str}")
            return None
    print("BŁĄD: W odpowiedzi LLM nie znaleziono bloku JSON.")
    return None


def _convert_types(data: dict) -> dict:
    """Konwertuje stringi na obiekty Decimal i datetime w sparsowanych danych."""
    try:
        # Konwersja danych paragonu
        data["paragon_info"]["data_zakupu"] = datetime.strptime(
            data["paragon_info"]["data_zakupu"], "%Y-%m-%d"
        )
        data["paragon_info"]["suma_calkowita"] = Decimal(
            data["paragon_info"]["suma_calkowita"]
        )

        # Konwersja danych pozycji
        for item in data["pozycje"]:
            for key in ["ilosc", "cena_jedn", "cena_calk", "cena_po_rab"]:
                item[key] = Decimal(item[key])
            # Rabat może być nullem
            if item.get("rabat"):
                item["rabat"] = Decimal(item["rabat"])
            else:
                item["rabat"] = Decimal("0.00")  # Ustawiamy domyślny zerowy rabat
        return data
    except (InvalidOperation, ValueError, TypeError, KeyError) as e:
        print(
            f"BŁĄD: Problem z konwersją typów danych w JSON-ie od LLM. Klucz lub format jest niepoprawny. Szczegóły: {e}"
        )
        raise ValueError("Nie udało się przekonwertować danych z LLM.") from e


def parse_receipt_with_llm(
    image_path: str, model_name: str = Config.VISION_MODEL
) -> dict | None:
    """
    Używa modelu multimodalnego do sparsowania całego paragonu z pliku obrazu.

    Args:
        image_path: Ścieżka do pliku z obrazem paragonu.
        model_name: Nazwa modelu Ollama do użycia (np. 'llava:latest').

    Returns:
        Słownik z danymi w formacie ParsedData, lub None w przypadku błędu.
    """
    if not client:
        print("BŁĄD: Klient Ollama nie jest skonfigurowany.")
        return None

    image_p = Path(image_path)
    if not image_p.exists():
        print(f"BŁĄD: Plik obrazu nie istnieje: {image_path}")
        return None

    # Konwersja obrazu do base64
    with open(image_p, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    system_prompt = """
    Jesteś ekspertem od OCR i ekstrakcji danych. Twoją jedyną funkcją jest analiza obrazu paragonu i zwrócenie obiektu JSON.
    NIE WOLNO CI zwracać żadnego tekstu, wyjaśnień ani formatowania markdown przed lub po obiekcie JSON.
    Twoja odpowiedź musi być TYLKO I WYŁĄCZNIE poprawnym obiektem JSON.

    Struktura obiektu JSON musi być następująca:
    ```json
    {
      "sklep_info": {
        "nazwa": "string (np. 'Lidl', 'Biedronka', 'Auchan', 'Kaufland')",
        "lokalizacja": "string (adres sklepu lub miasto) or null"
      },
      "paragon_info": {
        "data_zakupu": "string w formacie YYYY-MM-DD",
        "suma_calkowita": "string reprezentujący liczbę (np. '123.45', zawsze suma końcowa po rabatach)"
      },
      "pozycje": [
        {
          "nazwa_raw": "string (nazwa produktu z paragonu)",
          "ilosc": "string (np. '1.000')",
          "jednostka": "string (np. 'szt', 'kg') or null",
          "cena_jedn": "string (cena za jednostkę)",
          "cena_calk": "string (cena całkowita PRZED rabatem, jeśli jest podany)",
          "rabat": "string (wartość rabatu np. '0.80') or null",
          "cena_po_rab": "string (cena końcowa za pozycję)"
        }
      ]
    }
    ```
    
    BARDZO WAŻNE ZASADY:
    1.  **Nazwa sklepu:** Zidentyfikuj nazwę sieci (np. "Biedronka", "Lidl", "Auchan", "Kaufland").
    2.  **Suma całkowita:** Zawsze bierz końcową sumę do zapłaty (np. "SUMA PLN", "Razem PLN", "Ogółem").
    3.  **Pozycje bez ilości (np. Kaufland):** Jeśli paragon pokazuje tylko nazwę i cenę końcową (jak "UHT bezLaktozy1,... 4,29"), ZAWSZE ustaw:
        - "ilosc": "1.0"
        - "jednostka": "szt"
        - "cena_jedn": "4.29" (taka sama jak cena całkowita)
        - "cena_calk": "4.29"
        - "rabat": null
        - "cena_po_rab": "4.29"
    4.  **Rabaty:** Jeśli rabat jest podany jako osobna linia (np. "Rabat ORZESZKI W... -0.80"), NIE twórz dla niego osobnej pozycji. Zamiast tego, znajdź oryginalną pozycję ("ORZESZKI W") i uzupełnij jej pola:
        - "cena_calk": "3.99" (oryginalna cena)
        - "rabat": "0.80" (wartość rabatu jako liczba dodatnia)
        - "cena_po_rab": "3.19" (cena po rabacie)
    5.  Zawsze używaj kropki jako separatora dziesiętnego w stringach liczbowych.
    
    Przeanalizuj obraz paragonu i zwróć dane w powyższym formacie JSON.
    """

    try:
        print(
            f"INFO: Wysyłanie obrazu do modelu '{model_name}' w celu przetworzenia..."
        )
        response = client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "Przeanalizuj ten paragon.",
                    "images": [image_base64],
                },
            ],
        )

        raw_response_text = response["message"]["content"]
        print(
            "INFO: Otrzymano odpowiedź od LLM. Próbuję wyodrębnić i sparsować JSON..."
        )

        parsed_json = _extract_json_from_response(raw_response_text)
        if not parsed_json:
            return None

        print("INFO: Konwertuję typy danych (stringi na Decimal/datetime)...")
        converted_data = _convert_types(parsed_json)

        return converted_data

    except Exception as e:
        print(
            f"BŁĄD: Wystąpił problem podczas komunikacji z modelem '{model_name}': {e}"
        )
        return None
