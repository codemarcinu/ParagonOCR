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
            print(f"Otrzymany tekst (repr): {repr(json_str)}")
            return None
    print(
        f"BŁĄD: W odpowiedzi LLM nie znaleziono bloku JSON. Otrzymany tekst (repr): {repr(response_text)}"
    )
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

    # Uproszczony prompt - format='json' wymusza strukturę
    system_prompt = """
    Przeanalizuj obraz paragonu i wyodrębnij dane w formacie JSON.
    
    Wymagana struktura JSON:
    {
      "sklep_info": {
        "nazwa": "string (np. Lidl, Biedronka)",
        "lokalizacja": "string lub null"
      },
      "paragon_info": {
        "data_zakupu": "string YYYY-MM-DD",
        "suma_calkowita": "string (np. 123.45)"
      },
      "pozycje": [
        {
          "nazwa_raw": "string",
          "ilosc": "string (np. 1.0)",
          "jednostka": "string lub null",
          "cena_jedn": "string",
          "cena_calk": "string",
          "rabat": "string lub null",
          "cena_po_rab": "string"
        }
      ]
    }
    
    Zasady:
    1. Suma całkowita to kwota do zapłaty.
    2. Jeśli brak ilości, przyjmij 1.0.
    3. Ceny podawaj jako stringi z kropką.
    """

    try:
        print(f"INFO: Wysyłanie obrazu do modelu '{model_name}' (format=json)...")
        print(f"INFO: Plik: {image_path}")

        response = client.chat(
            model=model_name,
            format="json",  # WYMUSZENIE FORMATU JSON
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": "Przeanalizuj ten paragon.",
                    "images": [image_path],  # Ollama python client obsługuje ścieżki
                },
            ],
            options={
                "temperature": 0
            },  # Zmniejszamy losowość dla większej deterministyczności
        )

        raw_response_text = response["message"]["content"]
        print(
            f"INFO: Otrzymano odpowiedź od LLM. Długość: {len(raw_response_text)} znaków."
        )
        # print(f"DEBUG: Treść odpowiedzi: {raw_response_text}")

        try:
            parsed_json = json.loads(raw_response_text)
        except json.JSONDecodeError as e:
            print(
                f"BŁĄD: Model zwrócił niepoprawny JSON mimo format='json'. Szczegóły: {e}"
            )
            print(f"Treść: {raw_response_text}")
            return None

        print("INFO: Konwertuję typy danych (stringi na Decimal/datetime)...")
        converted_data = _convert_types(parsed_json)

        return converted_data

    except Exception as e:
        print(
            f"BŁĄD: Wystąpił problem podczas komunikacji z modelem '{model_name}': {e}"
        )
        return None
