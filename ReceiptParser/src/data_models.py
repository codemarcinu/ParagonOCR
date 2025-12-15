from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, TypedDict, Optional

# --- Definicje Struktur Danych (TypedDicts) ---
# Użycie TypedDict pozwala na statyczną analizę kodu i lepsze podpowiadanie składni.

class ParsedItem(TypedDict, total=False):
    """Struktura dla pojedynczej pozycji na paragonie."""
    nazwa_raw: str          # Oryginalna nazwa pozycji z paragonu
    ilosc: Decimal          # Ilość, np. 1.0, 0.5 (dla wagi)
    jednostka: Optional[str]  # Jednostka, np. 'szt', 'kg' (może być None)
    cena_jedn: Decimal      # Cena za jednostkę
    cena_calk: Decimal      # Całkowita cena za pozycję (ilość * cena_jedn)
    rabat: Optional[Decimal]  # Wartość rabatu (jeśli jest, może być None)
    cena_po_rab: Decimal    # Cena po uwzględnieniu rabatu
    data_waznosci: Optional[date]  # Data ważności produktu (opcjonalna)

class ParsedReceiptInfo(TypedDict):
    """Struktura dla ogólnych informacji o paragonie."""
    data_zakupu: datetime
    suma_calkowita: Decimal

class ParsedStoreInfo(TypedDict):
    """Struktura dla informacji o sklepie."""
    nazwa: str
    lokalizacja: Optional[str] # Lokalizacja może nie być zawsze dostępna

class ParsedData(TypedDict):
    """Kompletna struktura danych zwracana przez parser."""
    sklep_info: ParsedStoreInfo
    paragon_info: ParsedReceiptInfo
    pozycje: List[ParsedItem]
    file_path: Optional[str]  # Ścieżka do pliku (obrazu) paragonu
