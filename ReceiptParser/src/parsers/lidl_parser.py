
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Optional

# Importujemy klasę bazową i zdefiniowane struktury danych
from . import BaseParser, ParsedData, ParsedItem, ParsedReceiptInfo, ParsedStoreInfo

class LidlParser(BaseParser):
    """Parser dedykowany dla paragonów ze sklepów Lidl."""

    def parse(self, raw_text: str) -> ParsedData:
        """
        Implementacja logiki parsowania dla paragonów z Lidla.

        Args:
            raw_text: Surowy tekst z OCR.

        Returns:
            Ustrukturyzowane dane w formacie `ParsedData`.
        
        Raises:
            ValueError: Jeśli nie uda się sparsować kluczowych informacji (data, suma, pozycje).
        """
        # --- Krok 1: Wyciągnij informacje o sklepie ---
        # Na razie zakładamy, że to Lidl. W przyszłości można by szukać nazwy w tekście.
        store_info: ParsedStoreInfo = {
            'nazwa': 'Lidl',
            'lokalizacja': self._find_location(raw_text) # Prosta próba znalezienia adresu
        }

        # --- Krok 2: Wyciągnij datę i sumę całkowitą ---
        date_str = self._find_date(raw_text)
        total_str = self._find_total(raw_text)

        if not date_str or not total_str:
            raise ValueError("Nie udało się znaleźć daty lub sumy całkowitej na paragonie.")

        try:
            purchase_date = datetime.strptime(date_str, '%Y-%m-%d')
            total_amount = Decimal(total_str.replace(',', '.'))
        except (ValueError, InvalidOperation) as e:
            raise ValueError(f"Błąd konwersji daty lub sumy: {e}")

        receipt_info: ParsedReceiptInfo = {
            'data_zakupu': purchase_date,
            'suma_calkowita': total_amount
        }

        # --- Krok 3: Wyciągnij listę produktów ---
        items = self._find_items(raw_text)
        if not items:
            raise ValueError("Nie znaleziono żadnych pozycji produktowych na paragonie.")

        # --- Krok 4: Złóż wszystko w jedną strukturę ---
        parsed_data: ParsedData = {
            'sklep_info': store_info,
            'paragon_info': receipt_info,
            'pozycje': items
        }
        
        return parsed_data

    def _find_date(self, raw_text: str) -> Optional[str]:
        """Znajduje datę sprzedaży na paragonie."""
        # Szukamy wzorca typu 'DATA SPRZED. 2025-11-01', dopuszczając wariacje
        match = re.search(r"DATA\s+SPRZED(?:AŻY)?\.?[\s]+(\d{4}-\d{2}-\d{2})", raw_text, re.IGNORECASE)
        return match.group(1) if match else None

    def _find_total(self, raw_text: str) -> Optional[str]:
        """Znajduje sumę całkowitą na paragonie."""
        # Szukamy wzorca 'SUMA PLN 123,45', ignorując wielkość liter
        match = re.search(r"SUMA\s+PLN\s+([\d,.]+)", raw_text, re.IGNORECASE)
        return match.group(1) if match else None

    def _find_location(self, raw_text: str) -> Optional[str]:
        """Prosta próba znalezienia adresu sklepu."""
        # Szukamy linii zaczynającej się od 'ul.' 
        match = re.search(r"(ul\..+)", raw_text)
        return match.group(1).strip() if match else None

    def _find_items(self, raw_text: str) -> List[ParsedItem]:
        """Znajduje poszczególne pozycje zakupów na paragonie."""
        lines = raw_text.splitlines()
        items: List[ParsedItem] = []
        
        # Wzorzec dla linii z ilością i ceną, np.: '1,000 szt x 2,49 2,49 A' lub '0,520 kg x 9,99 5,19 A'
        # Grupy: 1-ilość, 2-jednostka, 3-cena jedn., 4-cena całk.
        item_regex = re.compile(r"^\s*([\d,]+)\s*(szt|kg)\s*x\s*([\d,]+)\s+([\d,.]+)")

        for i, line in enumerate(lines):
            match = item_regex.search(line)
            
            if match and i > 0:
                # Zakładamy, że nazwa produktu jest w linii powyżej
                raw_name = lines[i-1].strip()
                
                # Ignorujemy puste linie, które mogły zostać błędnie wzięte za nazwę
                if not raw_name or raw_name.lower() == "paragon fiskalny":
                    continue

                quantity_str, unit, price_per_unit_str, total_price_str = match.groups()

                try:
                    # Konwertujemy stringi na liczby Decimal, dbając o poprawny format (zamiana przecinka na kropkę)
                    price = Decimal(price_per_unit_str.replace(',', '.'))
                    total = Decimal(total_price_str.replace(',', '.'))

                    item: ParsedItem = {
                        'nazwa_raw': raw_name,
                        'ilosc': Decimal(quantity_str.replace(',', '.')),
                        'jednostka': unit,
                        'cena_jedn': price,
                        'cena_calk': total,
                        'rabat': None,  # Logika rabatów do implementacji w przyszłości
                        'cena_po_rab': total # Na razie zakładamy brak rabatu
                    }
                    items.append(item)
                except InvalidOperation:
                    # Jeśli konwersja się nie powiedzie, ignorujemy tę linię (prawdopodobnie błąd OCR)
                    continue
        
        return items
