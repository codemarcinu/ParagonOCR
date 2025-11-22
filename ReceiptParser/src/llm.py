import ollama
import httpx

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
    # Tworzymy timeout i przekazujemy go bezpośrednio do ollama.Client
    # ollama.Client przyjmuje **kwargs, które są przekazywane do httpx.Client
    timeout = httpx.Timeout(Config.OLLAMA_TIMEOUT, connect=10.0)
    client = ollama.Client(host=Config.OLLAMA_HOST, timeout=timeout)
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

    system_prompt = """
    Jesteś wirtualnym magazynierem. Twoim zadaniem jest zamiana nazwy z paragonu na KRÓTKĄ, GENERYCZNĄ nazwę produktu do domowej spiżarni.
    
    ZASADY KRYTYCZNE:
    1. USUWASZ marki (np. "Krakus", "Mlekovita", "Winiary" -> USUŃ).
    2. USUWASZ gramaturę i opakowania (np. "1L", "500g", "butelka", "szt" -> USUŃ).
    3. USUWASZ przymiotniki marketingowe (np. "tradycyjne", "babuni", "pyszne", "luksusowe" -> USUŃ).
    4. Zmieniasz na Mianownik Liczby Pojedynczej (np. "Bułki" -> "Bułka", "Jaja" -> "Jajka").
    5. Jeśli produkt to plastikowa torba/reklamówka, zwróć dokładnie słowo: "POMIŃ".
    """

    user_prompt = f"""
    PRZYKŁADY:
    - "Mleko UHT 3,2% Łaciate 1L" -> "Mleko"
    - "Jaja z wolnego wybiegu L 10szt" -> "Jajka"
    - "Chleb Baltonowski krojony 500g" -> "Chleb"
    - "Kajzerka pszenna duża" -> "Bułka"
    - "Szynka Konserwowa Krakus" -> "Szynka"
    - "Pomidor gałązka luz" -> "Pomidory"
    - "Coca Cola 0.5L" -> "Napój gazowany"
    - "Reklamówka mała płatna" -> "POMIŃ"
    
    Nazwa z paragonu: "{raw_name}"
    Znormalizowana nazwa:
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

        # Truncation tekstu OCR jeśli jest za długi (limit ~10000 znaków dla bezpieczeństwa)
        MAX_OCR_TEXT_LENGTH = 10000
        if ocr_text and len(ocr_text) > MAX_OCR_TEXT_LENGTH:
            print(f"OSTRZEŻENIE: Tekst OCR jest za długi ({len(ocr_text)} znaków), obcinam do {MAX_OCR_TEXT_LENGTH} znaków.")
            ocr_text = ocr_text[:MAX_OCR_TEXT_LENGTH] + "\n\n[... tekst OCR obcięty ...]"

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
    system_prompt_override: str = None,
) -> dict | None:
    """
    Używa modelu tekstowego do sparsowania paragonu na podstawie tekstu (np. z Mistral OCR).

    Args:
        text_content: Tekst paragonu (np. markdown z OCR).
        model_name: Nazwa modelu Ollama do użycia.
        system_prompt_override: Opcjonalny prompt systemowy (np. ze strategii), który nadpisuje domyślny.

    Returns:
        Słownik z danymi w formacie ParsedData, lub None w przypadku błędu.
    """
    if not client:
        print("BŁĄD: Klient Ollama nie jest skonfigurowany.")
        return None

    if system_prompt_override:
        system_prompt = system_prompt_override
    else:
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

        # Truncation tekstu jeśli jest za długi (limit ~50000 znaków dla bezpieczeństwa)
        MAX_TEXT_LENGTH = 50000
        if len(text_content) > MAX_TEXT_LENGTH:
            print(f"OSTRZEŻENIE: Tekst paragonu jest za długi ({len(text_content)} znaków), obcinam do {MAX_TEXT_LENGTH} znaków.")
            text_content = text_content[:MAX_TEXT_LENGTH] + "\n\n[... tekst obcięty ...]"
        
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
