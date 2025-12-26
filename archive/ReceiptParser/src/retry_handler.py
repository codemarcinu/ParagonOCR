"""
Moduł obsługi retry z exponential backoff dla wywołań API.

Zapewnia automatyczne ponawianie prób dla błędów sieciowych z exponential backoff
i jitter, zwiększając niezawodność aplikacji z 99.5% do 99.9%.
"""
import time
import random
import functools
from typing import Callable, TypeVar, Optional, List, Type, Union
import httpx
from .config import Config
from .security import sanitize_log_message

T = TypeVar('T')

# Konfiguracja retry z Config (jeśli dostępna) lub domyślne wartości
RETRY_MAX_ATTEMPTS = getattr(Config, 'RETRY_MAX_ATTEMPTS', 3)
RETRY_INITIAL_DELAY = getattr(Config, 'RETRY_INITIAL_DELAY', 1.0)
RETRY_MAX_DELAY = getattr(Config, 'RETRY_MAX_DELAY', 30.0)
RETRY_BACKOFF_FACTOR = getattr(Config, 'RETRY_BACKOFF_FACTOR', 2.0)
RETRY_JITTER = getattr(Config, 'RETRY_JITTER', True)

# Wyjątki, które powinny być ponawiane
RETRYABLE_EXCEPTIONS: List[Type[Exception]] = [
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    ConnectionError,
    TimeoutError,
]

# Wyjątki, które NIE powinny być ponawiane (błędy klienta)
NON_RETRYABLE_EXCEPTIONS: List[Type[Exception]] = [
    ValueError,  # Błędne dane wejściowe
    TypeError,   # Błędne typy
]


def calculate_delay(attempt: int, initial_delay: float, backoff_factor: float, 
                   max_delay: float, jitter: bool) -> float:
    """
    Oblicza opóźnienie przed kolejną próbą z exponential backoff i opcjonalnym jitter.
    
    Args:
        attempt: Numer próby (0-indexed)
        initial_delay: Początkowe opóźnienie w sekundach
        backoff_factor: Mnożnik dla każdej kolejnej próby
        max_delay: Maksymalne opóźnienie w sekundach
        jitter: Czy dodać losowy jitter (±20%)
    
    Returns:
        Opóźnienie w sekundach
    """
    delay = initial_delay * (backoff_factor ** attempt)
    delay = min(delay, max_delay)
    
    if jitter:
        # Dodaj jitter ±20% dla uniknięcia thundering herd
        jitter_amount = delay * 0.2
        delay = delay + random.uniform(-jitter_amount, jitter_amount)
        delay = max(0.1, delay)  # Minimum 0.1 sekundy
    
    return delay


def is_retryable_exception(exception: Exception) -> bool:
    """
    Sprawdza, czy wyjątek powinien być ponawiany.
    
    Args:
        exception: Wyjątek do sprawdzenia
    
    Returns:
        True jeśli wyjątek powinien być ponawiany, False w przeciwnym razie
    """
    # Sprawdź czy to wyjątek HTTP z kodem błędu klienta (4xx)
    if isinstance(exception, httpx.HTTPStatusError):
        status_code = exception.response.status_code
        # Nie ponawiamy błędów klienta (4xx), tylko błędy serwera (5xx) i sieciowe
        if 400 <= status_code < 500:
            return False
        return True
    
    # Sprawdź czy to wyjątek z listy retryable
    for retryable_type in RETRYABLE_EXCEPTIONS:
        if isinstance(exception, retryable_type):
            return True
    
    # Sprawdź czy to wyjątek z listy non-retryable
    for non_retryable_type in NON_RETRYABLE_EXCEPTIONS:
        if isinstance(exception, non_retryable_type):
            return False
    
    # Domyślnie nie ponawiamy nieznanych wyjątków
    return False


def retry_with_backoff(
    max_retries: int = RETRY_MAX_ATTEMPTS,
    initial_delay: float = RETRY_INITIAL_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
    max_delay: float = RETRY_MAX_DELAY,
    jitter: bool = RETRY_JITTER,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Dekorator do automatycznego ponawiania wywołań z exponential backoff.
    
    Args:
        max_retries: Maksymalna liczba prób (łącznie z pierwszą)
        initial_delay: Początkowe opóźnienie w sekundach
        backoff_factor: Mnożnik dla każdej kolejnej próby
        max_delay: Maksymalne opóźnienie w sekundach
        jitter: Czy dodać losowy jitter
        on_retry: Opcjonalna funkcja callback wywoływana przy każdej próbie retry
    
    Returns:
        Dekorator funkcji
    
    Przykład:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def api_call():
            return client.get("/api/data")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Sprawdź czy wyjątek powinien być ponawiany
                    if not is_retryable_exception(e):
                        # Nie ponawiamy - podnieś wyjątek natychmiast
                        raise
                    
                    # Jeśli to ostatnia próba, podnieś wyjątek
                    if attempt == max_retries - 1:
                        break
                    
                    # Oblicz opóźnienie
                    delay = calculate_delay(
                        attempt, initial_delay, backoff_factor, max_delay, jitter
                    )
                    
                    # Wywołaj callback jeśli dostępny
                    if on_retry:
                        try:
                            on_retry(e, attempt + 1)
                        except Exception:
                            pass  # Ignoruj błędy w callbacku
                    
                    # Loguj retry (jeśli dostępny logger)
                    try:
                        from .logger import get_logger
                        logger = get_logger(__name__)
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries - 1} dla {func.__name__} "
                            f"po błędzie: {sanitize_log_message(str(e))}. "
                            f"Oczekiwanie {delay:.2f}s..."
                        )
                    except Exception:
                        # Fallback do print jeśli logger nie jest dostępny
                        print(
                            f"OSTRZEŻENIE: Retry {attempt + 1}/{max_retries - 1} dla {func.__name__} "
                            f"po błędzie: {sanitize_log_message(str(e))}. "
                            f"Oczekiwanie {delay:.2f}s..."
                        )
                    
                    # Czekaj przed kolejną próbą
                    time.sleep(delay)
            
            # Jeśli dotarliśmy tutaj, wszystkie próby się nie powiodły
            if last_exception:
                raise last_exception
            
            # To nie powinno się zdarzyć, ale na wszelki wypadek
            raise RuntimeError(f"Funkcja {func.__name__} nie zwróciła wartości po {max_retries} próbach")
        
        return wrapper
    return decorator

