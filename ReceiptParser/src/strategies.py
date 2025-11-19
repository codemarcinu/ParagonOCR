from abc import ABC, abstractmethod
from typing import Dict, List, Any
import re


class ReceiptStrategy(ABC):
    """Interfejs bazowy dla strategii każdego sklepu."""

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Zwraca specyficzny prompt dla danego sklepu."""
        pass

    def post_process(self, data: Dict) -> Dict:
        """Domyślna implementacja: brak zmian."""
        return data


class LidlStrategy(ReceiptStrategy):
    def get_system_prompt(self) -> str:
        return """
        Jesteś ekspertem od analizy paragonów sieci Lidl.
        
        KLUCZOWE ZASADY DLA LIDLA:
        1. Struktura linii produktu: "Nazwa ... Ilość * Cena_jedn Wartość Kod_podatku".
           Przykład: "Mleko UHT 1,5% 2 * 3,29 6,58 C" -> Ilość: 2.0, Cena jedn: 3.29.
        2. RABATY (Lidl Plus): Często występują w OSOBNEJ linii pod produktem jako ujemna kwota.
           Przykład:
           "Serek Wiejski" ... 3.59
           "Lidl Plus rabat" ... -0.50
           Twoim zadaniem jest potraktować to jako OSOBNĄ pozycję w JSON z ujemną ceną całkowitą.
           Nasz system scali to w post-processingu.
        3. Ignoruj sekcje "PTU A", "Kwota A", "Rozliczenie płatności".
        
        Wymagana struktura JSON:
        Wymagana struktura JSON:
        {
          "sklep_info": { "nazwa": "Lidl", "lokalizacja": "Adres sklepu lub null" },
          "paragon_info": { "data_zakupu": "YYYY-MM-DD", "suma_calkowita": "123.45" },
          "pozycje": [
            { "nazwa_raw": "Nazwa produktu", "ilosc": "1.0", "jednostka": "szt/kg", "cena_jedn": "1.23", "cena_calk": "1.23", "rabat": "0.00", "cena_po_rab": "1.23" }
          ]
        }
        """

    def post_process(self, data: Dict) -> Dict:
        """Scalanie ujemnych pozycji (rabatów) z produktem powyżej."""
        cleaned_items = []
        if not data or "pozycje" not in data:
            return data

        # Iterujemy po kopiach, żeby móc modyfikować
        items = data["pozycje"]
        skip_indices = set()

        for i in range(len(items)):
            if i in skip_indices:
                continue

            current_item = items[i]

            # Sprawdzamy, czy następny element to rabat (ujemna cena lub nazwa sugerująca rabat)
            if i + 1 < len(items):
                next_item = items[i + 1]
                is_discount = False

                # Wykrywanie po nazwie lub ujemnej cenie
                raw_name_lower = next_item.get("nazwa_raw", "").lower()
                try:
                    price_total = float(next_item.get("cena_calk", 0))
                except (ValueError, TypeError):
                    price_total = 0

                if (
                    "rabat" in raw_name_lower
                    or "upust" in raw_name_lower
                    or price_total < 0
                ):
                    is_discount = True

                if is_discount:
                    # To jest rabat do bieżącego produktu!
                    discount_value = abs(price_total)

                    # Pobieramy obecny rabat (może być stringiem lub liczbą)
                    try:
                        current_rabat = float(current_item.get("rabat") or 0)
                    except (ValueError, TypeError):
                        current_rabat = 0.0

                    current_item["rabat"] = str(current_rabat + discount_value)

                    # Przelicz cenę po rabacie
                    try:
                        base_price = float(current_item.get("cena_calk", 0))
                        current_item["cena_po_rab"] = str(
                            round(base_price - (current_rabat + discount_value), 2)
                        )
                    except (ValueError, TypeError):
                        pass

                    skip_indices.add(i + 1)  # Pomiń ten rabat w głównej pętli

            cleaned_items.append(current_item)

        data["pozycje"] = cleaned_items
        return data


class BiedronkaStrategy(ReceiptStrategy):
    def get_system_prompt(self) -> str:
        return """
        Jesteś ekspertem od analizy paragonów sieci Biedronka (Jeronimo Martins).
        
        KLUCZOWE ZASADY DLA BIEDRONKI:
        1. Format w plikach PDF często rozbija linię na: "Nazwa", potem w nowej linii "Ilość x Cena".
           Szukaj wzorca: "1.000 x 3,29" -> to oznacza 1 sztukę po 3.29.
        2. Ignoruj linię "Sprzedaż opodatkowana".
        3. Ignoruj sekcje podsumowania podatków (PTU A, PTU B...).
        4. Czasami nazwa produktu skleja się z kodem PTU (np. "MlekoC"). Oddziel to.
        
        Wymagana struktura JSON:
        Wymagana struktura JSON:
        {
          "sklep_info": { "nazwa": "Biedronka", "lokalizacja": "Adres sklepu lub null" },
          "paragon_info": { "data_zakupu": "YYYY-MM-DD", "suma_calkowita": "123.45" },
          "pozycje": [
            { "nazwa_raw": "Nazwa produktu", "ilosc": "1.0", "jednostka": "szt/kg", "cena_jedn": "1.23", "cena_calk": "1.23", "rabat": "0.00", "cena_po_rab": "1.23" }
          ]
        }
        """


class KauflandStrategy(ReceiptStrategy):
    def get_system_prompt(self) -> str:
        return """
        Jesteś ekspertem od analizy paragonów sieci Kaufland.
        
        KLUCZOWE ZASADY DLA KAUFLANDA:
        1. Produkty często są w formacie: "Nazwa produktu" a pod spodem osobno cena.
        2. Jeśli widzisz samą nazwę i cenę, załóż ilość = 1.0.
        3. Szukaj słów kluczowych "szt" lub "kg" w nazwie, to może pomóc w jednostce.
        4. Ignoruj linie "Podsumowanie zakupów", "Ogółem".
        
        Wymagana struktura JSON:
        Wymagana struktura JSON:
        {
          "sklep_info": { "nazwa": "Kaufland", "lokalizacja": "Adres sklepu lub null" },
          "paragon_info": { "data_zakupu": "YYYY-MM-DD", "suma_calkowita": "123.45" },
          "pozycje": [
            { "nazwa_raw": "Nazwa produktu", "ilosc": "1.0", "jednostka": "szt/kg", "cena_jedn": "1.23", "cena_calk": "1.23", "rabat": "0.00", "cena_po_rab": "1.23" }
          ]
        }
        """


class AuchanStrategy(ReceiptStrategy):
    def get_system_prompt(self) -> str:
        return """
        Jesteś ekspertem od analizy paragonów sieci Auchan.
        
        KLUCZOWE ZASADY DLA AUCHAN:
        1. UWAGA NA ŚMIECI OCR: Ignoruj ciągi znaków typu "ReWtymOplRec551061" lub dziwne kody na początku paragonu.
        2. Ceny często mają przyklejony kod podatkowy na końcu, np. "19,98A". Traktuj to jako cenę 19.98.
        3. Format często wygląda tak: "Nazwa ... Ilość x Cena Wartość".
        4. Opłata recyklingowa (BDO, Recykling) nie jest towarem handlowym - pomiń ją jeśli możesz.
        
        Wymagana struktura JSON:
        Wymagana struktura JSON:
        {
          "sklep_info": { "nazwa": "Auchan", "lokalizacja": "Adres sklepu lub null" },
          "paragon_info": { "data_zakupu": "YYYY-MM-DD", "suma_calkowita": "123.45" },
          "pozycje": [
            { "nazwa_raw": "Nazwa produktu", "ilosc": "1.0", "jednostka": "szt/kg", "cena_jedn": "1.23", "cena_calk": "1.23", "rabat": "0.00", "cena_po_rab": "1.23" }
          ]
        }
        """

    def post_process(self, data: Dict) -> Dict:
        """Usuwanie pozycji, które wyglądają na błędy OCR (śmieci)."""
        if not data or "pozycje" not in data:
            return data

        valid_items = []
        for item in data["pozycje"]:
            name = item.get("nazwa_raw", "")
            # Filtr: jeśli nazwa to jeden długi ciąg bez spacji i ma cyfry w środku, to pewnie śmieć
            if len(name) > 10 and " " not in name and any(c.isdigit() for c in name):
                continue
            if "ReWtym" in name or "OplRec" in name:
                continue
            valid_items.append(item)

        data["pozycje"] = valid_items
        return data


class GenericStrategy(ReceiptStrategy):
    def get_system_prompt(self) -> str:
        return """
        Przeanalizuj ten obraz paragonu. 
        Postaraj się zidentyfikować nazwę sklepu, datę i listę pozycji (nazwa, ilość, cena).
        Sformatuj wynik ściśle według zadanego schematu JSON.
        
        Wymagana struktura JSON:
        Wymagana struktura JSON:
        {
          "sklep_info": { "nazwa": "Nazwa sklepu", "lokalizacja": "Adres sklepu lub null" },
          "paragon_info": { "data_zakupu": "YYYY-MM-DD", "suma_calkowita": "123.45" },
          "pozycje": [
            { "nazwa_raw": "Nazwa produktu", "ilosc": "1.0", "jednostka": "szt/kg", "cena_jedn": "1.23", "cena_calk": "1.23", "rabat": "0.00", "cena_po_rab": "1.23" }
          ]
        }
        """


def get_strategy_for_store(text_header: str) -> ReceiptStrategy:
    """
    Wybiera strategię parsowania na podstawie surowego tekstu z OCR (Tesseract).
    """
    text_lower = text_header.lower()

    if "lidl" in text_lower:
        return LidlStrategy()
    elif "biedronka" in text_lower or "jeronimo" in text_lower:
        return BiedronkaStrategy()
    elif "kaufland" in text_lower:
        return KauflandStrategy()
    elif "auchan" in text_lower:
        return AuchanStrategy()
    else:
        return GenericStrategy()
