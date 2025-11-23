"""
Moduł do logowania błędów i informacji.
Obsługuje zarówno logowanie do konsoli (callback), jak i opcjonalne logowanie do pliku.
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

# Konfiguracja logowania
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / f"paragonocr_{datetime.now().strftime('%Y%m%d')}.log"
ENABLE_FILE_LOGGING = os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true"


def setup_logging(enable_file: bool = None) -> None:
    """
    Konfiguruje system logowania.
    
    Args:
        enable_file: Jeśli True, włącza logowanie do pliku. Jeśli None, używa zmiennej środowiskowej.
    """
    global ENABLE_FILE_LOGGING
    if enable_file is not None:
        ENABLE_FILE_LOGGING = enable_file
    
    # Tworzenie katalogu na logi jeśli nie istnieje
    if ENABLE_FILE_LOGGING:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Konfiguracja loggera
        logger = logging.getLogger("ParagonOCR")
        logger.setLevel(logging.DEBUG)
        
        # Handler do pliku
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Format logów
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Dodaj handler tylko jeśli nie został już dodany
        if not logger.handlers:
            logger.addHandler(file_handler)


def log_message(message: str, level: str = "INFO", callback: Optional[Callable[[str], None]] = None) -> None:
    """
    Loguje wiadomość zarówno do callbacka (konsola/GUI), jak i opcjonalnie do pliku.
    
    Args:
        message: Wiadomość do zalogowania
        level: Poziom logowania (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        callback: Opcjonalna funkcja callback do wyświetlenia wiadomości (np. w GUI)
    """
    # Logowanie przez callback (konsola/GUI)
    if callback:
        callback(message)
    
    # Logowanie do pliku (jeśli włączone)
    if ENABLE_FILE_LOGGING:
        logger = logging.getLogger("ParagonOCR")
        level_upper = level.upper()
        
        if level_upper == "DEBUG":
            logger.debug(message)
        elif level_upper == "INFO":
            logger.info(message)
        elif level_upper == "WARNING":
            logger.warning(message)
        elif level_upper == "ERROR":
            logger.error(message)
        elif level_upper == "CRITICAL":
            logger.critical(message)
        else:
            logger.info(message)  # Domyślnie INFO


# Inicjalizacja przy imporcie (jeśli zmienna środowiskowa jest ustawiona)
if ENABLE_FILE_LOGGING:
    setup_logging()








