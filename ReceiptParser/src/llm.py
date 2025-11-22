import ollama

import json
import re
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
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


def clean_llm_suggestion(suggestion: str) -> str:
    """
    Czyści sugestię z LLM z prefiksów typu 'Clean: "', cudzysłowów i innych artefaktów.
    
    Args:
        suggestion: Surowa sugestia z LLM
        
    Returns:
        Oczyszczona nazwa produktu
    """
    if not suggestion:
        return suggestion
    
    # Usuń prefiksy typu "Clean: " lub "Clean:"
    suggestion = re.sub(r'^Clean:\s*"?', '', suggestion, flags=re.IGNORECASE)
    suggestion = re.sub(r'^Clean\s*"?', '', suggestion, flags=re.IGNORECASE)
    
    # Usuń cudzysłowy na początku i końcu
    suggestion = suggestion.strip().strip('"').strip("'")
    
    # Usuń ewentualne dwukropki i spacje na początku
    suggestion = re.sub(r'^:\s*', '', suggestion)
    
    return suggestion.strip()


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
        "Jesteś ekspertem od kategoryzacji produktów spożywczych. "
        "Twoim celem jest sprowadzenie skomplikowanej nazwy z paragonu do OGÓLNEJ, BAZOWEJ nazwy produktu. "
        "Zasady:"
        "1. Ignoruj marki (np. 'Mlekovita', 'Coca-Cola' -> 'Napój gazowany', chyba że nazwa jest generyczna)."
        "2. Ignoruj gramaturę i opakowanie (np. '1L', 'butelka')."
        "3. Używaj nazw w mianowniku liczby pojedynczej (np. 'Jaja' -> 'Jajka', 'Bułki' -> 'Bułka')."
        "4. Zwracaj TYLKO znormalizowaną nazwę."
        "5. Dla śmieci OCR zwracaj 'POMIŃ'."
    )

    user_prompt = f"""
    Przykłady:
    - Raw: "Mleko UHT 3,2% Łaciate 1L" -> Clean: "Mleko"
    - Raw: "Jaja z wolnego wybiegu L 10szt" -> Clean: "Jajka"
    - Raw: "Chleb Baltonowski krojony" -> Clean: "Chleb"
    - Raw: "Kajzerka pszenna duża" -> Clean: "Bułka"
    - Raw: "Woda Żywiec Zdrój Niegaz." -> Clean: "Woda mineralna"
    - Raw: "Pomidor gałązka luz" -> Clean: "Pomidory"
    - Raw: "Szynka Konserwowa Krakus" -> Clean: "Szynka"

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
        # Czyścimy sugestię z prefiksów i artefaktów
        cleaned = clean_llm_suggestion(suggestion)
        return cleaned if cleaned else None
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
        raw_date = data["paragon_info"]["data_zakupu"]

        # Lista obsługiwanych formatów daty
        date_formats = [
            "%Y-%m-%d",  # 2025-11-18
            "%d.%m.%Y",  # 18.11.2025
            "%d.%m.%Y %H:%M",  # 18.11.2025 16:34 (Format Biedronki)
            "%Y-%m-%d %H:%M",  # 2025-11-18 16:34
            "%d-%m-%Y",  # 18-11-2025
        ]

        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(raw_date, fmt)
                break  # Udało się, przerywamy pętlę
            except ValueError:
                continue  # Próbujemy kolejny format

        if parsed_date:
            data["paragon_info"]["data_zakupu"] = parsed_date
        else:
            print(
                f"OSTRZEŻENIE: Nieprawidłowy format daty '{raw_date}'. Ustawiam dzisiejszą datę."
            )
            data["paragon_info"]["data_zakupu"] = datetime.now()

        try:
            data["paragon_info"]["suma_calkowita"] = Decimal(
                str(data["paragon_info"]["suma_calkowita"]).replace(",", ".")
            )
        except (InvalidOperation, TypeError):
            data["paragon_info"]["suma_calkowita"] = Decimal("0.00")

        # Konwersja danych pozycji
        for item in data["pozycje"]:
            for key in ["ilosc", "cena_jedn", "cena_calk", "cena_po_rab"]:
                try:
                    item[key] = Decimal(str(item[key]).replace(",", "."))
                except (InvalidOperation, TypeError):
                    item[key] = Decimal("0.00")

            # Rabat może być nullem
            if item.get("rabat"):
                try:
                    item["rabat"] = Decimal(str(item["rabat"]).replace(",", "."))
                except (InvalidOperation, TypeError):
                    item["rabat"] = Decimal("0.00")
            else:
                item["rabat"] = Decimal("0.00")  # Ustawiamy domyślny zerowy rabat
        return data
    except (InvalidOperation, ValueError, TypeError, KeyError) as e:
        print(
            f"BŁĄD: Problem z konwersją typów danych w JSON-ie od LLM. Klucz lub format jest niepoprawny. Szczegóły: {e}"
        )
        raise ValueError("Nie udało się przekonwertować danych z LLM.") from e


def parse_receipt_with_llm(
    image_path: str,
    model_name: str = Config.VISION_MODEL,
    system_prompt_override: str = None,
    ocr_text: str = None,
) -> dict | None:
    """
    Używa modelu multimodalnego do sparsowania całego paragonu z pliku obrazu.

    Args:
        image_path: Ścieżka do pliku z obrazem paragonu.
        model_name: Nazwa modelu Ollama do użycia (np. 'llava:latest').
        system_prompt_override: Opcjonalny prompt systemowy, który nadpisuje domyślny.

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
    if system_prompt_override:
        system_prompt = system_prompt_override
    else:
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
                    "content": (
                        f"Przeanalizuj ten paragon.\n\nWspomóż się tekstem odczytanym przez OCR (może zawierać błędy, ale układ jest zachowany):\n---\n{ocr_text}\n---"
                        if ocr_text
                        else "Przeanalizuj ten paragon."
                    ),
                    "images": [image_path],  # Ollama python client obsługuje ścieżki
                },
            ],
            options={
                "temperature": 0,
                "num_predict": 4000,  # Limit tokenów zwiększony dla długich paragonów
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


def parse_receipt_from_text(
    text_content: str,
    model_name: str = Config.TEXT_MODEL,
) -> dict | None:
    """
    Używa modelu tekstowego do sparsowania paragonu na podstawie tekstu (np. z Mistral OCR).

    Args:
        text_content: Tekst paragonu (np. markdown z OCR).
        model_name: Nazwa modelu Ollama do użycia.

    Returns:
        Słownik z danymi w formacie ParsedData, lub None w przypadku błędu.
    """
    if not client:
        print("BŁĄD: Klient Ollama nie jest skonfigurowany.")
        return None

    system_prompt = """
    Jesteś asystentem AI, który wyciąga ustrukturyzowane dane z tekstu paragonu.
    Otrzymasz treść paragonu (OCR/Markdown). Twoim zadaniem jest wyodrębnienie informacji i zwrócenie ich w formacie JSON.

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
    4. Ignoruj linie, które nie są pozycjami zakupowymi (np. sumy VAT, reklamy).
    5. RABATY: Jeśli widzisz linię z "Rabat" lub ujemną ceną, traktuj ją jako OSOBNĄ pozycję z ujemną ceną całkowitą.
       System automatycznie scali to z produktem powyżej w post-processingu.
    6. Dla produktów ważonych (kg): ilość to waga w kg (np. 0.365), jednostka to "kg".
    7. Dla produktów sztukowych: ilość to liczba sztuk (np. 2.0), jednostka może być "szt" lub null.

    Przykłady:

    Przykład 1 - Lidl z rabatem:
    {
      "sklep_info": {"nazwa": "Lidl", "lokalizacja": "Poznańska 48, Jankowice"},
      "paragon_info": {"data_zakupu": "2024-12-27", "suma_calkowita": "26.34"},
      "pozycje": [
        {"nazwa_raw": "Soczew.,HummusChipsy", "ilosc": "2.0", "cena_jedn": "3.59", "cena_calk": "7.18", "rabat": null, "cena_po_rab": "7.18"},
        {"nazwa_raw": "950_chipsy_mix", "ilosc": "1.0", "cena_jedn": "-3.58", "cena_calk": "-3.58", "rabat": null, "cena_po_rab": "-3.58"}
      ]
    }

    Przykład 2 - Biedronka z rabatami:
    {
      "sklep_info": {"nazwa": "Biedronka", "lokalizacja": "Kostrzyn, ul. Żniwna 5"},
      "paragon_info": {"data_zakupu": "2025-11-18", "suma_calkowita": "114.14"},
      "pozycje": [
        {"nazwa_raw": "KawMiel Rafiin250g", "ilosc": "1.0", "cena_jedn": "18.99", "cena_calk": "18.99", "rabat": null, "cena_po_rab": "18.99"},
        {"nazwa_raw": "Rabat", "ilosc": "1.0", "cena_jedn": "-4.00", "cena_calk": "-4.00", "rabat": null, "cena_po_rab": "-4.00"}
      ]
    }

    Przykład 3 - Produkty ważone:
    {
      "sklep_info": {"nazwa": "Biedronka", "lokalizacja": "Targowa 4, Kostrzyn"},
      "paragon_info": {"data_zakupu": "2025-01-13", "suma_calkowita": "29.76"},
      "pozycje": [
        {"nazwa_raw": "Marchew Luz", "ilosc": "0.365", "jednostka": "kg", "cena_jedn": "3.69", "cena_calk": "1.35", "rabat": null, "cena_po_rab": "1.35"},
        {"nazwa_raw": "Rabat", "ilosc": "1.0", "cena_jedn": "-0.62", "cena_calk": "-0.62", "rabat": null, "cena_po_rab": "-0.62"}
      ]
    }
    """

    try:
        print(f"INFO: Wysyłanie tekstu do modelu '{model_name}' (format=json)...")

        response = client.chat(
            model=model_name,
            format="json",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Przeanalizuj ten tekst paragonu:\n\n{text_content}",
                },
            ],
            options={
                "temperature": 0,
                "num_predict": 4000,
            },
        )

        raw_response_text = response["message"]["content"]
        print(
            f"INFO: Otrzymano odpowiedź od LLM. Długość: {len(raw_response_text)} znaków."
        )

        try:
            parsed_json = json.loads(raw_response_text)
        except json.JSONDecodeError as e:
            print(f"BŁĄD: Model zwrócił niepoprawny JSON. Szczegóły: {e}")
            return None

        print("INFO: Konwertuję typy danych...")
        converted_data = _convert_types(parsed_json)
        return converted_data

    except Exception as e:
        print(
            f"BŁĄD: Wystąpił problem podczas komunikacji z modelem '{model_name}': {e}"
        )
        return None
