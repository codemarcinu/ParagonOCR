
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, TypedDict, Optional

# --- Definicje Struktur Danych (TypedDicts) ---
# Użycie TypedDict pozwala na statyczną analizę kodu i lepsze podpowiadanie składni.

class ParsedItem(TypedDict):
    """Struktura dla pojedynczej pozycji na paragonie."""
    nazwa_raw: str          # Oryginalna nazwa pozycji z paragonu
    ilosc: Decimal          # Ilość, np. 1.0, 0.5 (dla wagi)
    jednostka: Optional[str]  # Jednostka, np. 'szt', 'kg' (może być None)
    cena_jedn: Decimal      # Cena za jednostkę
    cena_calk: Decimal      # Całkowita cena za pozycję (ilość * cena_jedn)
    rabat: Optional[Decimal]  # Wartość rabatu (jeśli jest, może być None)
    cena_po_rab: Decimal    # Cena po uwzględnieniu rabatu

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


# --- Abstrakcyjna Klasa Bazowa Parserów ---

class BaseParser(ABC):
    """
    Abstrakcyjna klasa bazowa (interfejs) dla wszystkich parserów paragonów.

    Każdy konkretny parser (np. dla Biedronki, Lidla) musi dziedziczyć po tej
    klasie i implementować metodę `parse`.
    """

    @abstractmethod
    def parse(self, raw_text: str) -> ParsedData:
        """
        Parsuje surowy tekst z paragonu i wyciąga z niego ustrukturyzowane dane.

        Args:
            raw_text: Surowy tekst odczytany z paragonu za pomocą OCR.

        Returns:
            Słownik zawierający sparsowane dane, zgodny ze strukturą `ParsedData`.
        
        Raises:
            NotImplementedError: Jeśli metoda nie została zaimplementowana w klasie pochodnej.
            ValueError: Jeśli parsowanie się nie powiedzie z powodu nieprawidłowego formatu tekstu.
        """
        raise NotImplementedError("Każdy parser musi implementować metodę 'parse'!")
