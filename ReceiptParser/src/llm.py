import ollama
import httpx

import json
import re
import logging
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Tuple, Optional, Dict, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import threading
from rapidfuzz import fuzz
from .config import Config
from .security import sanitize_path, sanitize_log_message
from .retry_handler import retry_with_backoff
from .llm_cache import get_llm_cache

logger = logging.getLogger(__name__)

# Import sanitize_log_message dla użycia w globalnym except
def _sanitize_error(e: Exception) -> str:
    """Pomocnicza funkcja do sanityzacji błędów."""
    return sanitize_log_message(str(e))

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
    # Import tutaj, żeby uniknąć circular import
    from .security import sanitize_log_message
    print(
        f"BŁĄD: Nie można połączyć się z Ollama na {Config.OLLAMA_HOST}. Upewnij się, że usługa działa. Szczegóły: {sanitize_log_message(str(e))}"
    )
    client = None

# --- Request Queuing ---
# Queue for managing concurrent LLM requests (max 2 simultaneous)
_request_queue: Queue = Queue()
_active_requests: int = 0
_max_concurrent_requests: int = 2
_queue_lock = threading.Lock()

# --- Conversation Context ---
# Store last 10 messages per conversation
_conversation_contexts: Dict[int, List[Dict]] = {}

# --- Timeout Presets ---
TIMEOUT_QUICK = 30  # 30 seconds for quick queries
TIMEOUT_RECIPES = 120  # 120 seconds for recipe generation
TIMEOUT_ANALYSIS = 60  # 60 seconds for analysis

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


def get_learning_examples(
    raw_name: str, session, max_examples: int = 5, min_similarity: int = 30
) -> List[Tuple[str, str]]:
    """
    Pobiera przykłady uczenia z bazy danych na podstawie podobieństwa nazw.
    
    Args:
        raw_name: Surowa nazwa produktu do znalezienia podobnych przykładów
        session: Sesja SQLAlchemy do bazy danych
        max_examples: Maksymalna liczba przykładów do zwrócenia
        min_similarity: Minimalne podobieństwo (0-100) do uwzględnienia przykładu
    
    Returns:
        Lista krotek (raw_name, normalized_name) z przykładami uczenia
    """
    try:
        from .database import AliasProduktu
        from sqlalchemy.orm import joinedload
        
        # Pobierz wszystkie aliasy z bazy (z dołączonym produktem)
        all_aliases = session.query(AliasProduktu).options(
            joinedload(AliasProduktu.produkt)
        ).all()
        
        if not all_aliases:
            return []
        
        # Oblicz podobieństwo dla każdego aliasu
        scored_examples = []
        for alias in all_aliases:
            similarity = fuzz.ratio(raw_name.lower(), alias.nazwa_z_paragonu.lower())
            if similarity >= min_similarity:
                scored_examples.append((
                    similarity,
                    alias.nazwa_z_paragonu,
                    alias.produkt.znormalizowana_nazwa
                ))
        
        # Sortuj po podobieństwie (malejąco) i weź najlepsze
        scored_examples.sort(reverse=True, key=lambda x: x[0])
        
        # Zwróć tylko pary (raw, normalized) bez score
        examples = [(raw, normalized) for _, raw, normalized in scored_examples[:max_examples]]
        
        return examples
    except Exception as e:
        print(f"BŁĄD podczas pobierania przykładów uczenia: {sanitize_log_message(str(e))}")
        return []


def get_llm_suggestion(
    raw_name: str, 
    model_name: str = Config.TEXT_MODEL,
    learning_examples: Optional[List[Tuple[str, str]]] = None
) -> str | None:
    """
    Używa modelu językowego do normalizacji "brudnej" nazwy produktu.
    Może używać przykładów uczenia z poprzednich wyborów użytkownika.
    
    Funkcja jest automatycznie retry'owana przez dekorator retry_with_backoff.

    Args:
        raw_name: Surowa nazwa produktu z paragonu.
        model_name: Nazwa modelu Ollama do użycia.
        learning_examples: Opcjonalna lista przykładów uczenia (raw_name, normalized_name).

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

    # Buduj sekcję z przykładami uczenia
    learning_section = ""
    if learning_examples and len(learning_examples) > 0:
        learning_section = "\n    PRZYKŁADY Z POPRZEDNICH WYBORÓW UŻYTKOWNIKA (użyj podobnego stylu normalizacji):\n"
        for raw, normalized in learning_examples:
            learning_section += f'    - "{raw}" -> "{normalized}"\n'
        learning_section += "\n"
    
    user_prompt = f"""
    PRZYKŁADY OGÓLNE:
    - "Mleko UHT 3,2% Łaciate 1L" -> "Mleko"
    - "Jaja z wolnego wybiegu L 10szt" -> "Jajka"
    - "Chleb Baltonowski krojony 500g" -> "Chleb"
    - "Kajzerka pszenna duża" -> "Bułka"
    - "Szynka Konserwowa Krakus" -> "Szynka"
    - "Pomidor gałązka luz" -> "Pomidory"
    - "Coca Cola 0.5L" -> "Napój gazowany"
    - "Reklamówka mała płatna" -> "POMIŃ"
{learning_section}
    Nazwa z paragonu: "{raw_name}"
    Znormalizowana nazwa:
    """

    @retry_with_backoff(
        max_retries=Config.RETRY_MAX_ATTEMPTS,
        initial_delay=Config.RETRY_INITIAL_DELAY,
        backoff_factor=Config.RETRY_BACKOFF_FACTOR,
        max_delay=Config.RETRY_MAX_DELAY,
        jitter=Config.RETRY_JITTER,
    )
    def _call_llm():
        return client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    
    try:
        response = _call_llm()
        suggestion = response["message"]["content"].strip()
        # Czyścimy sugestię z prefiksów i artefaktów
        cleaned = clean_llm_suggestion(suggestion)
        return cleaned if cleaned else None
    except Exception as e:
        print(
            f"BŁĄD: Wystąpił problem podczas komunikacji z modelem '{model_name}': {sanitize_log_message(str(e))}"
        )
        return None


# --- Batch Processing dla Normalizacji Produktów ---


def normalize_batch(
    raw_names: List[str],
    model_name: str = Config.TEXT_MODEL,
    learning_examples: Optional[List[Tuple[str, str]]] = None
) -> Dict[str, Optional[str]]:
    """
    Normalizuje batch produktów jednocześnie zamiast sekwencyjnie.
    
    Args:
        raw_names: Lista surowych nazw produktów do normalizacji
        model_name: Nazwa modelu Ollama do użycia
        learning_examples: Opcjonalna lista przykładów uczenia
    
    Returns:
        Słownik mapujący raw_name -> normalized_name (lub None w przypadku błędu)
    """
    if not raw_names:
        return {}
    
    if not client:
        print("BŁĄD: Klient Ollama nie jest skonfigurowany.")
        return {name: None for name in raw_names}
    
    system_prompt = """
    Jesteś wirtualnym magazynierem. Twoim zadaniem jest zamiana nazw z paragonu na KRÓTKIE, GENERYCZNE nazwy produktów do domowej spiżarni.
    
    ZASADY KRYTYCZNE:
    1. USUWASZ marki (np. "Krakus", "Mlekovita", "Winiary" -> USUŃ).
    2. USUWASZ gramaturę i opakowania (np. "1L", "500g", "butelka", "szt" -> USUŃ).
    3. USUWASZ przymiotniki marketingowe (np. "tradycyjne", "babuni", "pyszne", "luksusowe" -> USUŃ).
    4. Zmieniasz na Mianownik Liczby Pojedynczej (np. "Bułki" -> "Bułka", "Jaja" -> "Jajka").
    5. Jeśli produkt to plastikowa torba/reklamówka, zwróć dokładnie słowo: "POMIŃ".
    
    Zwróć odpowiedź w formacie JSON, gdzie klucz to surowa nazwa, a wartość to znormalizowana nazwa.
    Przykład:
    {
      "Mleko UHT 3,2% Łaciate 1L": "Mleko",
      "Jaja z wolnego wybiegu L 10szt": "Jajka",
      "Reklamówka mała płatna": "POMIŃ"
    }
    """
    
    # Buduj sekcję z przykładami uczenia
    learning_section = ""
    if learning_examples and len(learning_examples) > 0:
        learning_section = "\n    PRZYKŁADY Z POPRZEDNICH WYBORÓW UŻYTKOWNIKA (użyj podobnego stylu normalizacji):\n"
        for raw, normalized in learning_examples:
            learning_section += f'    - "{raw}" -> "{normalized}"\n'
        learning_section += "\n"
    
    # Formatuj listę produktów do normalizacji
    products_list = "\n".join([f'    - "{name}"' for name in raw_names])
    
    user_prompt = f"""
    PRZYKŁADY OGÓLNE:
    - "Mleko UHT 3,2% Łaciate 1L" -> "Mleko"
    - "Jaja z wolnego wybiegu L 10szt" -> "Jajka"
    - "Chleb Baltonowski krojony 500g" -> "Chleb"
    - "Kajzerka pszenna duża" -> "Bułka"
    - "Szynka Konserwowa Krakus" -> "Szynka"
    - "Pomidor gałązka luz" -> "Pomidory"
    - "Coca Cola 0.5L" -> "Napój gazowany"
    - "Reklamówka mała płatna" -> "POMIŃ"
{learning_section}
    Znormalizuj następujące produkty (zwróć JSON z mapowaniem):
{products_list}
    
    Zwróć TYLKO JSON, bez dodatkowego tekstu.
    """
    
    @retry_with_backoff(
        max_retries=Config.RETRY_MAX_ATTEMPTS,
        initial_delay=Config.RETRY_INITIAL_DELAY,
        backoff_factor=Config.RETRY_BACKOFF_FACTOR,
        max_delay=Config.RETRY_MAX_DELAY,
        jitter=Config.RETRY_JITTER,
    )
    def _call_batch_llm():
        return client.chat(
            model=model_name,
            format="json",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    
    try:
        response = _call_batch_llm()
        response_text = response["message"]["content"].strip()
        
        # Parsuj JSON odpowiedź
        try:
            # Usuń markdown code blocks jeśli są
            if response_text.startswith("```"):
                response_text = re.sub(r"```json\n?", "", response_text)
                response_text = re.sub(r"```\n?$", "", response_text)
            
            batch_results = json.loads(response_text)
            
            # Waliduj i czyść wyniki
            result_dict = {}
            for raw_name in raw_names:
                normalized = batch_results.get(raw_name)
                if normalized:
                    normalized = clean_llm_suggestion(normalized)
                result_dict[raw_name] = normalized if normalized else None
            
            return result_dict
        except json.JSONDecodeError as e:
            print(
                f"BŁĄD: Nie udało się sparsować JSON-a z batch LLM. Szczegóły: {sanitize_log_message(str(e))}"
            )
            print(f"Otrzymany tekst (obcięty): {sanitize_log_message(response_text, max_length=500)}")
            # Fallback: zwróć None dla wszystkich produktów
            return {name: None for name in raw_names}
    except Exception as e:
        print(
            f"BŁĄD: Wystąpił problem podczas batch normalizacji: {sanitize_log_message(str(e))}"
        )
        return {name: None for name in raw_names}


def normalize_products_batch(
    raw_names: List[str],
    session,
    model_name: str = Config.TEXT_MODEL,
    batch_size: int = None,
    max_workers: int = None,
    log_callback: Optional[Callable] = None
) -> Dict[str, Optional[str]]:
    """
    Normalizuje wiele produktów używając batch processing z równoległym przetwarzaniem.
    
    Args:
        raw_names: Lista surowych nazw produktów do normalizacji
        session: Sesja SQLAlchemy do pobrania przykładów uczenia
        model_name: Nazwa modelu Ollama do użycia
        batch_size: Rozmiar batcha (domyślnie z Config.BATCH_SIZE)
        max_workers: Liczba równoległych workerów (domyślnie z Config.BATCH_MAX_WORKERS)
        log_callback: Opcjonalna funkcja callback do logowania
    
    Returns:
        Słownik mapujący raw_name -> normalized_name
    """
    if not raw_names:
        return {}
    
    batch_size = batch_size or Config.BATCH_SIZE
    max_workers = max_workers or Config.BATCH_MAX_WORKERS
    
    # Podziel produkty na batche
    batches = [raw_names[i:i + batch_size] for i in range(0, len(raw_names), batch_size)]
    
    if log_callback:
        try:
            log_callback(f"INFO: Przetwarzam {len(raw_names)} produktów w {len(batches)} batchach (rozmiar batcha: {batch_size})")
        except Exception:
            pass
    
    # Pobierz przykłady uczenia (używamy pierwszego produktu jako referencji)
    learning_examples = []
    if raw_names:
        try:
            learning_examples = get_learning_examples(
                raw_names[0], session, max_examples=5, min_similarity=30
            )
        except Exception:
            pass  # Ignoruj błędy przy pobieraniu przykładów
    
    # Przetwarzaj batche równolegle
    all_results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submituj wszystkie batche
        future_to_batch = {
            executor.submit(normalize_batch, batch, model_name, learning_examples): batch
            for batch in batches
        }
        
        # Zbierz wyniki gdy są gotowe
        for future in as_completed(future_to_batch):
            batch = future_to_batch[future]
            try:
                batch_results = future.result()
                all_results.update(batch_results)
            except Exception as e:
                if log_callback:
                    try:
                        log_callback(f"OSTRZEŻENIE: Błąd podczas przetwarzania batcha: {sanitize_log_message(str(e))}")
                    except Exception:
                        pass
                # W przypadku błędu, zwróć None dla wszystkich produktów w batchu
                for name in batch:
                    all_results[name] = None
    
    return all_results


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


@retry_with_backoff(
    max_retries=Config.RETRY_MAX_ATTEMPTS,
    initial_delay=Config.RETRY_INITIAL_DELAY,
    backoff_factor=Config.RETRY_BACKOFF_FACTOR,
    max_delay=Config.RETRY_MAX_DELAY,
    jitter=Config.RETRY_JITTER,
)
def _call_vision_llm(model_name: str, system_prompt: str, image_path: str, ocr_text: Optional[str] = None):
    """Pomocnicza funkcja do wywołania vision LLM z retry."""
    return client.chat(
        model=model_name,
        format="json",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Przeanalizuj ten paragon.\n\nWspomóż się tekstem odczytanym przez OCR (może zawierać błędy, ale układ jest zachowany):\n---\n{ocr_text}\n---"
                    if ocr_text
                    else "Przeanalizuj ten paragon."
                ),
                "images": [image_path],
            },
        ],
        options={
            "temperature": 0,
            "num_predict": 4000,
        },
    )


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
        print(f"INFO: Plik: {sanitize_path(image_path)}")  # Tylko nazwa pliku, nie pełna ścieżka

        # Truncation tekstu OCR jeśli jest za długi (limit ~10000 znaków dla bezpieczeństwa)
        MAX_OCR_TEXT_LENGTH = 10000
        if ocr_text and len(ocr_text) > MAX_OCR_TEXT_LENGTH:
            print(f"OSTRZEŻENIE: Tekst OCR jest za długi ({len(ocr_text)} znaków), obcinam do {MAX_OCR_TEXT_LENGTH} znaków.")
            ocr_text = ocr_text[:MAX_OCR_TEXT_LENGTH] + "\n\n[... tekst OCR obcięty ...]"

        response = _call_vision_llm(model_name, system_prompt, image_path, ocr_text)

        raw_response_text = response["message"]["content"]
        print(
            f"INFO: Otrzymano odpowiedź od LLM. Długość: {len(raw_response_text)} znaków."
        )
        # Sanityzuj odpowiedź przed logowaniem (jeśli potrzeba debug)
        # print(f"DEBUG: Treść odpowiedzi: {sanitize_log_message(raw_response_text, max_length=500)}")

        try:
            parsed_json = json.loads(raw_response_text)
        except json.JSONDecodeError as e:
            print(
                f"BŁĄD: Model zwrócił niepoprawny JSON mimo format='json'. Szczegóły: {sanitize_log_message(str(e))}"
            )
            print(f"Treść (obcięta): {sanitize_log_message(raw_response_text, max_length=500)}")
            return None

        print("INFO: Konwertuję typy danych (stringi na Decimal/datetime)...")
        converted_data = _convert_types(parsed_json)

        return converted_data

    except Exception as e:
        print(
            f"BŁĄD: Wystąpił problem podczas komunikacji z modelem '{model_name}': {e}"
        )
        return None


@retry_with_backoff(
    max_retries=Config.RETRY_MAX_ATTEMPTS,
    initial_delay=Config.RETRY_INITIAL_DELAY,
    backoff_factor=Config.RETRY_BACKOFF_FACTOR,
    max_delay=Config.RETRY_MAX_DELAY,
    jitter=Config.RETRY_JITTER,
)
def _call_text_llm(model_name: str, system_prompt: str, text_content: str):
    """Pomocnicza funkcja do wywołania text LLM z retry."""
    return client.chat(
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
        
        response = _call_text_llm(model_name, system_prompt, text_content)

        raw_response_text = response["message"]["content"]
        print(
            f"INFO: Otrzymano odpowiedź od LLM. Długość: {len(raw_response_text)} znaków."
        )

        try:
            parsed_json = json.loads(raw_response_text)
        except json.JSONDecodeError as e:
            print(f"BŁĄD: Model zwrócił niepoprawny JSON. Szczegóły: {sanitize_log_message(str(e))}")
            print(f"Treść (obcięta): {sanitize_log_message(raw_response_text, max_length=500)}")
            return None

        print("INFO: Konwertuję typy danych...")
        converted_data = _convert_types(parsed_json)
        return converted_data

    except Exception as e:
        print(
            f"BŁĄD: Wystąpił problem podczas komunikacji z modelem '{model_name}': {sanitize_log_message(str(e))}"
        )
        return None
