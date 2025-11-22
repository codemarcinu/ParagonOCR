"""
Moduł do zarządzania historią ostatnio używanych plików.
"""
import json
import os
from pathlib import Path
from typing import List

# Maksymalna liczba wpisów w historii
MAX_HISTORY_ITEMS = 10

# Ścieżka do pliku historii
HISTORY_FILE = os.path.expanduser("~/.paragonocr_history.json")


def load_history() -> List[str]:
    """
    Wczytuje historię plików z dysku.
    
    Returns:
        Lista ścieżek do plików (od najnowszych do najstarszych)
    """
    if not os.path.exists(HISTORY_FILE):
        return []
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # Filtruj pliki, które nadal istnieją
        valid_history = [path for path in history if os.path.exists(path)]
        
        # Jeśli lista się zmieniła, zapisz ją z powrotem
        if len(valid_history) != len(history):
            save_history(valid_history)
        
        return valid_history
    except (json.JSONDecodeError, IOError):
        # Jeśli plik jest uszkodzony, zwróć pustą listę
        return []


def save_history(history: List[str]) -> None:
    """
    Zapisuje historię plików na dysk.
    
    Args:
        history: Lista ścieżek do plików
    """
    try:
        # Utwórz katalog jeśli nie istnieje
        history_dir = os.path.dirname(HISTORY_FILE)
        if history_dir and not os.path.exists(history_dir):
            os.makedirs(history_dir, exist_ok=True)
        
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except IOError:
        # Jeśli nie można zapisać, po prostu zignoruj błąd
        pass


def add_to_history(file_path: str) -> None:
    """
    Dodaje plik do historii (na początku listy).
    
    Args:
        file_path: Ścieżka do pliku
    """
    if not file_path or not os.path.exists(file_path):
        return
    
    # Normalizuj ścieżkę (użyj absolutnej)
    abs_path = os.path.abspath(file_path)
    
    history = load_history()
    
    # Usuń duplikaty (jeśli plik już jest w historii)
    if abs_path in history:
        history.remove(abs_path)
    
    # Dodaj na początku
    history.insert(0, abs_path)
    
    # Ogranicz do MAX_HISTORY_ITEMS
    history = history[:MAX_HISTORY_ITEMS]
    
    save_history(history)


def clear_history() -> None:
    """Czyści całą historię."""
    if os.path.exists(HISTORY_FILE):
        try:
            os.remove(HISTORY_FILE)
        except IOError:
            pass

