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
from .llm_cache_semantic import get_semantic_cache

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
        examples_lines = [
            f'    - "{raw}" -> "{normalized}"'
            for raw, normalized in learning_examples
        ]
        learning_section = "\n    PRZYKŁADY Z POPRZEDNICH WYBORÓW UŻYTKOWNIKA (użyj podobnego stylu normalizacji):\n" + "\n".join(examples_lines) + "\n"
    
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

    # Check exact cache first (fast, O(1))
    llm_cache = get_llm_cache()
    cached_response = llm_cache.get(
        prompt=user_prompt,
        model=model_name,
        temperature=None
    )
    
    if cached_response:
        suggestion = cached_response.get("message", {}).get("content", "").strip()
        if suggestion:
            cleaned = clean_llm_suggestion(suggestion)
            return cleaned if cleaned else None
    
    # Check semantic cache if enabled (finds similar prompts)
    semantic_cache = get_semantic_cache()
    if semantic_cache:
        semantic_cached = semantic_cache.get(
            prompt=user_prompt,
            model=model_name,
            temperature=None
        )
        if semantic_cached:
            suggestion = semantic_cached.get("message", {}).get("content", "").strip()
            if suggestion:
                cleaned = clean_llm_suggestion(suggestion)
                # Also cache in exact cache for faster future lookups
                llm_cache.set(
                    prompt=user_prompt,
                    model=model_name,
                    response=semantic_cached,
                    temperature=None
                )
                return cleaned if cleaned else None
    
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
        
        # Cache the response in both exact and semantic caches
        llm_cache.set(
            prompt=user_prompt,
            model=model_name,
            response=response,
            temperature=None
        )
        # Also cache in semantic cache if enabled
        if semantic_cache:
            semantic_cache.set(
                prompt=user_prompt,
                model=model_name,
                response=response,
                temperature=None
            )
        
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
        examples_lines = [
            f'    - "{raw}" -> "{normalized}"'
            for raw, normalized in learning_examples
        ]
        learning_section = "\n    PRZYKŁADY Z POPRZEDNICH WYBORÓW UŻYTKOWNIKA (użyj podobnego stylu normalizacji):\n" + "\n".join(examples_lines) + "\n"
    
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
    Normalizuje wiele produktów używając zoptymalizowanego batch processing.
    
    OPTIMIZATION: Dla małych list (< 50 produktów) przetwarza wszystko w jednym requeście.
    Dla większych list dzieli na batche, ale używa większego rozmiaru batcha (25 zamiast 5).
    
    Args:
        raw_names: Lista surowych nazw produktów do normalizacji
        session: Sesja SQLAlchemy do pobrania przykładów uczenia
        model_name: Nazwa modelu Ollama do użycia
        batch_size: Rozmiar batcha (domyślnie z Config.BATCH_SIZE, teraz 25)
        max_workers: Liczba równoległych workerów (domyślnie z Config.BATCH_MAX_WORKERS)
        log_callback: Opcjonalna funkcja callback do logowania
    
    Returns:
        Słownik mapujący raw_name -> normalized_name
    """
    if not raw_names:
        return {}
    
    batch_size = batch_size or Config.BATCH_SIZE
    max_workers = max_workers or Config.BATCH_MAX_WORKERS
    
    # OPTIMIZATION: Dla małych list (< 50 produktów) przetwarzaj wszystko w jednym requeście
    # To eliminuje overhead równoległego przetwarzania i zmniejsza liczbę requestów z N do 1
    if len(raw_names) <= 50:
        if log_callback:
            try:
                log_callback(f"INFO: Przetwarzam {len(raw_names)} produktów w jednym requeście (optimized batch)")
            except Exception:
                pass
        
        # Pobierz przykłady uczenia
        learning_examples = []
        if raw_names:
            try:
                learning_examples = get_learning_examples(
                    raw_names[0], session, max_examples=5, min_similarity=30
                )
            except Exception:
                pass
        
        # Jeden request dla wszystkich produktów
        return normalize_batch(raw_names, model_name, learning_examples)
    
    # Dla większych list, dziel na batche (ale większe batche niż wcześniej)
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
    
    # Przetwarzaj batche równolegle (ale mniej batchy dzięki większemu batch_size)
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


def _validate_json_structure(text: str) -> tuple[bool, str]:
    """
    Validates JSON structure before parsing.
    Returns: (is_valid, error_message)
    
    Checks:
    - Balanced curly braces and square brackets
    - Starts with { and ends with }
    - Basic structure integrity
    """
    if not text or not text.strip():
        return False, "Empty or whitespace-only response"
    
    text = text.strip()
    
    # Check balanced braces
    open_braces = text.count('{')
    close_braces = text.count('}')
    if open_braces != close_braces:
        return False, f"Unbalanced braces: {{ count={open_braces} }} count={close_braces}"
    
    # Check balanced brackets
    open_brackets = text.count('[')
    close_brackets = text.count(']')
    if open_brackets != close_brackets:
        return False, f"Unbalanced brackets: [ count={open_brackets} ] count={close_brackets}"
    
    # Check starts and ends
    if not text.startswith('{'):
        return False, "JSON does not start with {"
    
    if not text.endswith('}'):
        return False, "JSON does not end with }"
    
    return True, ""


def _log_json_error_position(error: json.JSONDecodeError, text: str) -> None:
    """
    Logs detailed information about JSON parsing error position.
    Shows context around the error location.
    """
    error_pos = getattr(error, 'pos', None)
    error_line = getattr(error, 'lineno', None)
    error_col = getattr(error, 'colno', None)
    
    print(f"DEBUG: JSONDecodeError details:")
    print(f"  - Position: char {error_pos}, line {error_line}, column {error_col}")
    
    if error_pos is not None and error_pos < len(text):
        # Show context around error (50 chars before and after)
        start = max(0, error_pos - 50)
        end = min(len(text), error_pos + 50)
        context = text[start:end]
        error_marker_pos = error_pos - start
        
        # Create a visual marker at error position
        marker_line = ' ' * error_marker_pos + '^'
        print(f"  - Context: ...{context}...")
        print(f"  - Marker:  ...{marker_line}")
        
        # Try to find nearby key names for context
        before_error = text[max(0, error_pos - 200):error_pos]
        key_matches = re.findall(r'"([^"]+)":', before_error)
        if key_matches:
            print(f"  - Recent keys before error: {key_matches[-3:]}")


def _repair_json(json_str: str) -> str:
    """
    Próbuje naprawić typowe błędy w JSON-ie zwracanym przez LLM.
    Obsługuje:
    - Markdown code blocks (usuwa ```json i ```)
    - Niezakończone stringi (znajduje i zamyka)
    - Obcięty JSON (znajduje ostatni kompletny obiekt)
    - Trailing commas
    - Explanatory text before JSON
    - Duplicate keys (zachowuje pierwsze wystąpienie)
    """
    if not json_str:
        return json_str
    
    original = json_str
    json_str = json_str.strip()
    
    # Remove markdown code blocks
    json_str = re.sub(r'^```json\s*\n?', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'\n?```\s*$', '', json_str, flags=re.MULTILINE)
    json_str = json_str.strip()
    
    # Remove explanatory text before JSON (find first {)
    json_start = json_str.find('{')
    if json_start > 0:
        json_str = json_str[json_start:]
    
    # Znajdź pierwszy { - początek JSON
    start_pos = json_str.find('{')
    if start_pos == -1:
        return original  # Return original if no JSON found
    
    json_str = json_str[start_pos:]
    
    # Znajdź ostatni kompletny obiekt JSON przez liczenie nawiasów
    depth = 0
    in_string = False
    escape_next = False
    last_valid_pos = -1
    
    for i, char in enumerate(json_str):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if not in_string:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    last_valid_pos = i
                elif depth < 0:
                    # Zbyt wiele zamknięć - użyj ostatniej poprawnej pozycji
                    break
    
    # Jeśli znaleźliśmy kompletny obiekt, użyj go
    if last_valid_pos > 0:
        json_str = json_str[:last_valid_pos + 1]
    elif depth > 0 or in_string:
        # Obiekt nie jest kompletny - spróbuj naprawić
        # Najpierw zamknij niezakończony string jeśli jesteśmy w stringu
        if in_string:
            # Usuń trailing whitespace i dodaj cudzysłów
            json_str = json_str.rstrip() + '"'
            in_string = False
        
        # Teraz zamknij wszystkie otwarte nawiasy klamrowe
        if depth > 0:
            json_str = json_str.rstrip()
            # Usuń trailing comma jeśli jest
            if json_str.endswith(','):
                json_str = json_str[:-1]
            # Dodaj brakujące zamknięcia
            json_str += '}' * depth
        
        # Spróbuj sparsować ponownie, aby upewnić się, że jest poprawny
        # (ale nie robimy tego tutaj, tylko zwracamy naprawiony string)
    
    # Usuń trailing commas przed } lub ]
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    # Handle duplicate keys by keeping first occurrence
    # This is a simple approach - for complex cases, we'd need a proper JSON parser
    # But since we're repairing, we'll try to fix common patterns
    # Note: Python's json.loads() will automatically keep last occurrence of duplicate keys
    # So we can't fix this at string level easily, but we log it
    
    return json_str


def _parse_json_with_repair(response_text: str) -> dict | None:
    """
    Próbuje sparsować JSON z odpowiedzi LLM, używając naprawy w razie potrzeby.
    Includes comprehensive logging and validation before parsing.
    """
    # Log raw response metadata
    print(f"DEBUG: Raw response length: {len(response_text)} chars")
    if len(response_text) > 0:
        print(f"DEBUG: First 200 chars: {response_text[:200]}")
        print(f"DEBUG: Last 200 chars: {response_text[-200:]}")
    
    # Validate structure BEFORE parsing
    is_valid, validation_error = _validate_json_structure(response_text)
    if not is_valid:
        print(f"OSTRZEŻENIE: JSON struktura niepoprawna: {validation_error}")
        # Attempt repair
        response_text = _repair_json(response_text)
        print(f"DEBUG: Attempted repair. New length={len(response_text)}")
        is_valid, validation_error = _validate_json_structure(response_text)
        if not is_valid:
            print(f"BŁĄD: Nie udało się naprawić JSON struktury mimo próby. Błąd: {validation_error}")
    
    # Check bracket balance for logging
    open_braces = response_text.count('{')
    close_braces = response_text.count('}')
    open_brackets = response_text.count('[')
    close_brackets = response_text.count(']')
    print(f"DEBUG: Bracket balance - Open {{: {open_braces}, Close }}: {close_braces}, Open [: {open_brackets}, Close ]: {close_brackets}")
    
    # Najpierw spróbuj bezpośrednio
    try:
        parsed = json.loads(response_text)
        print("DEBUG: JSON parsed successfully on first attempt")
        return parsed
    except json.JSONDecodeError as e:
        print("DEBUG: Direct JSON parsing failed, attempting repair...")
        _log_json_error_position(e, response_text)
    
    # Spróbuj naprawić i sparsować ponownie
    try:
        repaired = _repair_json(response_text)
        if repaired != response_text:
            print(f"DEBUG: JSON repaired. Original length: {len(response_text)}, Repaired length: {len(repaired)}")
        parsed = json.loads(repaired)
        print("DEBUG: JSON parsed successfully after repair")
        return parsed
    except json.JSONDecodeError as e:
        print("DEBUG: JSON parsing failed even after repair")
        _log_json_error_position(e, repaired)
    
    # Spróbuj wyodrębnić JSON z markdown code blocks
    try:
        print("DEBUG: Attempting to extract JSON from markdown code blocks...")
        parsed = _extract_json_from_response(response_text)
        if parsed:
            print("DEBUG: JSON extracted successfully from markdown")
            return parsed
    except Exception as e:
        print(f"DEBUG: Failed to extract JSON from markdown: {sanitize_log_message(str(e))}")
    
    print("BŁĄD: Wszystkie próby parsowania JSON zakończyły się niepowodzeniem")
    return None


def _extract_json_from_response(response_text: str) -> dict | None:
    """Wyszukuje i parsuje blok JSON z odpowiedzi tekstowej modelu."""
    # Najpierw spróbuj znaleźć JSON w markdown code block
    match = re.search(r"```json\n(\{.*?)\n```", response_text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # Jeśli nie ma markdown, znajdź pierwszy { i użyj całej reszty tekstu
        start_pos = response_text.find('{')
        if start_pos == -1:
            print(
                f"BŁĄD: W odpowiedzi LLM nie znaleziono bloku JSON. Otrzymany tekst (repr, obcięty): {repr(response_text[:200])}"
            )
            return None
        json_str = response_text[start_pos:]
    
    # Spróbuj sparsować bezpośrednio
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Spróbuj naprawić i sparsować ponownie
        try:
            repaired = _repair_json(json_str)
            return json.loads(repaired)
        except json.JSONDecodeError as e:
            print(
                f"BŁĄD: Nie udało się sparsować JSON-a z odpowiedzi LLM nawet po naprawie. Szczegóły: {e}"
            )
            print(f"Otrzymany tekst (repr, obcięty): {repr(json_str[:200])}")
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
            # Log error and raise exception instead of silently using today's date
            error_msg = f"Nieprawidłowy format daty: '{raw_date}'. Nie można sparsować daty."
            logger.error(error_msg)
            raise ValueError(f"Nie można sparsować daty: {raw_date}. Obsługiwane formaty: {', '.join(date_formats)}")

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
            "num_predict": 2500,  # Reduced from 4000 to prevent truncation
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

        parsed_json = _parse_json_with_repair(raw_response_text)
        if parsed_json is None:
            print(
                f"BŁĄD: Model zwrócił niepoprawny JSON mimo format='json'. Próbowano naprawić, ale nie udało się."
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
            "num_predict": 2500,  # Reduced from 4000 to prevent truncation
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

        parsed_json = _parse_json_with_repair(raw_response_text)
        if parsed_json is None:
            print(f"BŁĄD: Model zwrócił niepoprawny JSON. Próbowano naprawić, ale nie udało się.")
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
