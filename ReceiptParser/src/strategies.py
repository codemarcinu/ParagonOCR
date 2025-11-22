from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from decimal import Decimal
import re
from .config import Config
from .data_models import ParsedData


class ReceiptStrategy(ABC):
    """Interfejs bazowy dla strategii każdego sklepu."""

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Zwraca specyficzny prompt dla danego sklepu."""
        pass

    def post_process(self, data: ParsedData, ocr_text: Optional[str] = None) -> ParsedData:
        """Domyślna implementacja: filtrowanie PTU/VAT i innych nieproduktów."""
        return self._filter_non_products(data)
    
    def _filter_non_products(self, data: ParsedData) -> ParsedData:
        """
        Filtruje pozycje, które nie są produktami (PTU/VAT, sumy, itp.).
        
        Args:
            data: Dane paragonu do przetworzenia
        
        Returns:
            Przetworzone dane z usuniętymi pozycjami PTU/VAT
        """
        if not data or "pozycje" not in data:
            return data
        
        filtered_items = []
        for item in data["pozycje"]:
            nazwa_raw = item.get("nazwa_raw", "").strip().lower()
            
            # Wzorce do wykrywania PTU/VAT i innych nieproduktów
            non_product_patterns = [
                r"^ptu\s*[abc]?$",  # PTU, PTU A, PTU B, PTU C
                r"^vat\s*[abc]?$",  # VAT, VAT A, VAT B, VAT C
                r"podatek\s+vat",  # Podatek VAT
                r"podatek\s+ptu",  # Podatek PTU
                r"kwota\s+[abc]$",  # Kwota A, Kwota B, Kwota C
                r"suma\s+pln",  # Suma PLN
                r"^suma\s*$",  # Suma
                r"podsumowanie",  # Podsumowanie
                r"ogółem",  # Ogółem
                r"rozliczenie\s+płatności",  # Rozliczenie płatności
                r"sprzedaż\s+opodatkowana",  # Sprzedaż opodatkowana
            ]
            
            # Sprawdź czy pozycja pasuje do wzorców nieproduktów
            is_non_product = False
            for pattern in non_product_patterns:
                if re.search(pattern, nazwa_raw):
                    is_non_product = True
                    break
            
            # Jeśli to nie jest nieprodukt, dodaj do listy
            if not is_non_product:
                filtered_items.append(item)
        
        data["pozycje"] = filtered_items
        return data
    
    def _merge_discounts(
        self, 
        data: ParsedData, 
        fix_negative_discounts: bool = False,
        strict_discount_name: bool = False
    ) -> ParsedData:
        """
        Wspólna metoda do scalania rabatów z produktami powyżej.
        
        Args:
            data: Dane paragonu do przetworzenia
            fix_negative_discounts: Jeśli True, koryguje ujemne rabaty w obecnej pozycji przed scalaniem
            strict_discount_name: Jeśli True, wymaga dokładnego dopasowania nazwy "rabat"/"upust" (bez innych słów)
        
        Returns:
            Przetworzone dane z scalonymi rabatami
        """
        if not data or "pozycje" not in data:
            return data

        cleaned_items = []
        items = data["pozycje"]
        skip_indices = set()

        for i in range(len(items)):
            if i in skip_indices:
                continue

            current_item = items[i]
            
            # Opcjonalna korekta ujemnych rabatów w obecnej pozycji (dla Biedronki)
            if fix_negative_discounts:
                try:
                    current_rabat_raw = current_item.get("rabat", 0)
                    if isinstance(current_rabat_raw, str):
                        current_rabat_raw = current_rabat_raw.replace(",", ".")
                    current_rabat_value = float(current_rabat_raw)
                    if current_rabat_value < 0:
                        # LLM zwrócił ujemny rabat - konwertuj na dodatni
                        current_item["rabat"] = f"{abs(current_rabat_value):.2f}"
                        # Przelicz cenę po rabacie
                        base_price = float(str(current_item.get("cena_calk", 0)).replace(",", "."))
                        cena_po_rab = max(0.0, base_price - abs(current_rabat_value))
                        current_item["cena_po_rab"] = f"{cena_po_rab:.2f}"
                except (ValueError, TypeError):
                    pass

            # Sprawdzamy, czy następny element to rabat
            if i + 1 < len(items):
                next_item = items[i + 1]
                is_discount = False
                
                # Wykrywanie rabatu
                raw_name_lower = next_item.get("nazwa_raw", "").lower().strip()
                try:
                    price_total = float(str(next_item.get("cena_calk", 0)).replace(",", "."))
                except (ValueError, TypeError):
                    price_total = 0.0

                # Wykrywanie po cenie (ujemna) - to jest najpewniejszy wskaźnik
                if price_total < 0:
                    is_discount = True
                elif strict_discount_name:
                    # Dla Biedronki: tylko dokładne dopasowanie "rabat" lub "upust" (bez innych słów)
                    if raw_name_lower in ["rabat", "upust"]:
                        is_discount = True
                else:
                    # Dla Lidla: sprawdzamy czy nazwa zawiera "rabat" lub "upust"
                    if "rabat" in raw_name_lower or "upust" in raw_name_lower:
                        is_discount = True

                if is_discount:
                    # To jest rabat do bieżącego produktu!
                    discount_value = abs(price_total)
                    
                    # Pobieramy obecny rabat
                    try:
                        current_rabat = float(str(current_item.get("rabat", 0)).replace(",", "."))
                    except (ValueError, TypeError):
                        current_rabat = 0.0
                    
                    new_rabat = current_rabat + discount_value
                    current_item["rabat"] = f"{new_rabat:.2f}"
                    
                    # Przelicz cenę po rabacie
                    try:
                        base_price = float(str(current_item.get("cena_calk", 0)).replace(",", "."))
                        cena_po_rab = max(0.0, base_price - new_rabat)
                        current_item["cena_po_rab"] = f"{cena_po_rab:.2f}"
                        
                        # Jeśli rabat jest większy niż cena, korygujemy
                        if new_rabat > base_price:
                            current_item["rabat"] = f"{base_price:.2f}"
                            current_item["cena_po_rab"] = "0.00"
                    except (ValueError, TypeError):
                        pass
                    
                    skip_indices.add(i + 1)  # Pomiń ten rabat w głównej pętli

            cleaned_items.append(current_item)

        data["pozycje"] = cleaned_items
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
        {
          "sklep_info": { "nazwa": "Lidl", "lokalizacja": "Adres sklepu lub null" },
          "paragon_info": { "data_zakupu": "2024-05-20", "suma_calkowita": "123.45" },
          "pozycje": [
            { "nazwa_raw": "Nazwa produktu", "ilosc": "1.0", "jednostka": "szt/kg", "cena_jedn": "1.23", "cena_calk": "1.23", "rabat": "0.00", "cena_po_rab": "1.23" }
          ]
        }
        """

    def post_process(self, data: ParsedData, ocr_text: Optional[str] = None) -> ParsedData:
        """Scalanie ujemnych pozycji (rabatów) z produktem powyżej."""
        data = self._filter_non_products(data)  # Najpierw usuń PTU/VAT
        return self._merge_discounts(data, fix_negative_discounts=False, strict_discount_name=False)


class BiedronkaStrategy(ReceiptStrategy):
    def get_system_prompt(self) -> str:
        return """
        Jesteś ekspertem od analizy paragonów sieci Biedronka (Jeronimo Martins).
        
        KLUCZOWE ZASADY DLA TEGO PLIKU:
        1. To jest długi obraz powstały ze sklejenia stron PDF.
        2. Wzorce linii produktów są nietypowe i wieloliniowe. Częsty schemat bloku produktu:
           Linia 1: "Nazwa produktu" (np. "Mleko UHT 3,2 1l")
           Linia 2: Cena jednostkowa (np. "3,49")
           Linia 3: Ilość (np. "1.000")
           Linia 4: znak "x"
           Linia 5: Kod podatku (np. "A", "B", "C")
           Linia 6: Wartość końcowa (np. "3,49")
        
        3. Zadanie: Musisz zrekonstruować te rozsypane bloki w jeden obiekt.
           Jeśli widzisz sekwencję: Nazwa -> Liczba -> Liczba -> "x", to wiesz, że to jeden produkt.
        
        4. Rabaty: Często występują w OSOBNEJ linii pod produktem jako:
           "Rabat"
           "-4,00" (ujemna kwota)
           Traktuj to jako pole "rabat" dla produktu powyżej (wartość dodatnia 4.00).

        5. Ignoruj techniczne linie: "Strona 1 z 2", "NIEFISKALNY", "Numer transakcji".
        
        Wymagana struktura JSON:
        {
          "sklep_info": { "nazwa": "Biedronka", "lokalizacja": "Adres sklepu lub null" },
          "paragon_info": { "data_zakupu": "RRRR-MM-DD", "suma_calkowita": "123.45" },
          "pozycje": [
            { "nazwa_raw": "Nazwa produktu", "ilosc": "1.0", "jednostka": "szt/kg", "cena_jedn": "1.23", "cena_calk": "1.23", "rabat": "0.00", "cena_po_rab": "1.23" }
          ]
        }
        """

    def post_process(self, data: ParsedData, ocr_text: Optional[str] = None) -> ParsedData:
        """
        Scalanie rabatów dla Biedronki.
        Używa wspólnej metody z korektą ujemnych rabatów i ścisłym dopasowaniem nazwy.
        """
        data = self._filter_non_products(data)  # Najpierw usuń PTU/VAT
        return self._merge_discounts(data, fix_negative_discounts=True, strict_discount_name=True)


class KauflandStrategy(ReceiptStrategy):
    def _calculate_items_sum(self, items: List[Dict]) -> float:
        """Oblicza sumę pozycji (po rabatach)."""
        suma_pozycji = 0.0
        for item in items:
            try:
                cena_po_rab = float(str(item.get("cena_po_rab", item.get("cena_calk", 0))).replace(",", "."))
                suma_pozycji += cena_po_rab
            except (ValueError, TypeError):
                try:
                    cena_calk = float(str(item.get("cena_calk", 0)).replace(",", "."))
                    suma_pozycji += cena_calk
                except (ValueError, TypeError):
                    pass
        return suma_pozycji
    
    def _detect_card_discount_from_items(self, items: List[Dict]) -> Optional[float]:
        """Wykrywa rabat z karty Kaufland Card w pozycjach paragonu."""
        for item in items:
            name_lower = item.get("nazwa_raw", "").lower()
            # Szukamy pozycji z informacją o rabacie z karty
            if any(keyword in name_lower for keyword in ["kaufland card", "zaoszczędzono", "card", "zaoszczedzono"]):
                # Spróbuj wyciągnąć kwotę rabatu z ceny (może być ujemna)
                try:
                    cena = float(str(item.get("cena_calk", 0)).replace(",", "."))
                    if cena < 0:
                        return abs(cena)
                    elif cena > 0 and cena <= 20.0:  # Typowy rabat z karty to 5-15 PLN
                        return cena
                except (ValueError, TypeError):
                    pass
        return None
    
    def _detect_card_discount_from_ocr(self, ocr_text: str) -> Optional[float]:
        """Wykrywa rabat z karty Kaufland Card w tekście OCR."""
        if not ocr_text:
            return None
        try:
            # Szukaj wzorca: "zaoszczędzono X,XX PLN" lub "Kaufland Card ... X,XX PLN"
            pattern = r'(?:zaoszcz[ęe]dzo|kaufland\s+card).*?(\d+[.,]\d+)\s*pln'
            match = re.search(pattern, ocr_text.lower())
            if match:
                return float(match.group(1).replace(',', '.'))
        except (ValueError, TypeError, AttributeError):
            pass
        return None
    
    def _detect_card_discount_from_pattern(self, roznica: float, suma_pozycji: float) -> Optional[float]:
        """Wykrywa rabat z karty na podstawie wzorców różnic między sumą pozycji a sumą paragonu."""
        if not (50.0 <= suma_pozycji <= 200.0):
            return None
        # Sprawdź, czy różnica między sumą pozycji a sumą paragonu jest bliska typowego rabatu
        roznica_decimal = Decimal(str(roznica))
        for typical_discount in Config.KAUFLAND_TYPICAL_DISCOUNTS:
            if abs(roznica_decimal + typical_discount) < Config.KAUFLAND_DISCOUNT_TOLERANCE:
                return float(typical_discount)
        return None
    
    def _correct_total_sum(
        self, 
        data: ParsedData, 
        suma_pozycji: float, 
        suma_paragonu: float, 
        roznica: float, 
        rabat_z_karty: Optional[float]
    ) -> ParsedData:
        """Koryguje sumę całkowitą paragonu na podstawie wykrytego rabatu i różnic."""
        TOLERANCE = 0.10  # Tolerancja dla małych różnic
        
        # Jeśli suma paragonu jest bardzo duża (prawdopodobnie błąd parsowania), zawsze korygujemy
        if suma_paragonu > suma_pozycji * 2:
            # Suma paragonu jest więcej niż 2x większa od sumy pozycji - to na pewno błąd
            if rabat_z_karty is not None:
                suma_po_rabacie = max(0.0, suma_pozycji - rabat_z_karty)
                data["paragon_info"]["suma_calkowita"] = f"{suma_po_rabacie:.2f}"
            else:
                data["paragon_info"]["suma_calkowita"] = f"{suma_pozycji:.2f}"
        # Jeśli suma paragonu > suma pozycji (różnica dodatnia, ale nie bardzo duża), to prawdopodobnie błąd parsowania
        elif roznica > TOLERANCE:
            if rabat_z_karty is not None:
                suma_po_rabacie = max(0.0, suma_pozycji - rabat_z_karty)
                data["paragon_info"]["suma_calkowita"] = f"{suma_po_rabacie:.2f}"
            else:
                data["paragon_info"]["suma_calkowita"] = f"{suma_pozycji:.2f}"
        # Jeśli suma paragonu < suma pozycji (różnica ujemna), to może być rabat z karty Kaufland Card
        elif roznica < -TOLERANCE and abs(roznica) <= 20.0:
            if rabat_z_karty is not None:
                suma_po_rabacie = max(0.0, suma_pozycji - rabat_z_karty)
                # Sprawdź, czy suma paragonu jest bliska sumie po rabacie
                if abs(suma_paragonu - suma_po_rabacie) > TOLERANCE:
                    data["paragon_info"]["suma_calkowita"] = f"{suma_po_rabacie:.2f}"
        # Jeśli różnica jest mała, ale znaleźliśmy rabat z karty, sprawdzamy czy suma jest poprawna
        elif abs(roznica) < TOLERANCE and rabat_z_karty is not None:
            suma_po_rabacie = max(0.0, suma_pozycji - rabat_z_karty)
            if abs(suma_paragonu - suma_po_rabacie) > TOLERANCE:
                data["paragon_info"]["suma_calkowita"] = f"{suma_po_rabacie:.2f}"
        
        return data
    
    def get_system_prompt(self) -> str:
        return """
        Jesteś ekspertem od analizy paragonów sieci Kaufland.
        
        KLUCZOWE ZASADY DLA KAUFLANDA:
        1. Produkty często są w formacie: "Nazwa produktu" a pod spodem osobno cena.
        2. Jeśli widzisz samą nazwę i cenę, załóż ilość = 1.0.
        3. Szukaj słów kluczowych "szt" lub "kg" w nazwie, to może pomóc w jednostce.
        4. Ignoruj linie "Podsumowanie zakupów", "Ogółem", sekcje podatków VAT.
        
        5. SUMA CAŁKOWITA - BARDZO WAŻNE:
           - Suma całkowita to kwota DO ZAPŁATY (po uwzględnieniu rabatów z karty).
           - Jeśli widzisz "Z Kaufland Card zaoszczędzono X,XX PLN", to suma całkowita = suma pozycji - rabat z karty.
           - Jeśli nie ma rabatu z karty, suma całkowita = suma wszystkich pozycji.
           - NIE używaj sumy brutto z sekcji podatków VAT jako suma_calkowita!
        
        6. RABATY:
           - Rabaty z karty Kaufland Card są globalne (na cały paragon), nie na poszczególne produkty.
           - Jeśli widzisz "Z Kaufland Card zaoszczędzono X,XX PLN", to jest to rabat globalny.
           - Rabaty na pojedyncze produkty mogą być w osobnych liniach - traktuj je jako osobne pozycje z ujemną ceną.
        
        Wymagana struktura JSON:
        {
          "sklep_info": { "nazwa": "Kaufland", "lokalizacja": "Adres sklepu lub null" },
          "paragon_info": { "data_zakupu": "2024-05-20", "suma_calkowita": "123.45" },
          "pozycje": [
            { "nazwa_raw": "Nazwa produktu", "ilosc": "1.0", "jednostka": "szt/kg", "cena_jedn": "1.23", "cena_calk": "1.23", "rabat": "0.00", "cena_po_rab": "1.23" }
          ]
        }
        """
    
    def post_process(self, data: ParsedData, ocr_text: Optional[str] = None) -> ParsedData:
        """
        Post-processing dla Kaufland:
        1. Filtrowanie PTU/VAT i nieproduktów
        2. Scalanie rabatów na pojedyncze produkty (jak w Lidl/Biedronka)
        3. Weryfikacja i korekta sumy całkowitej (uwzględnienie rabatu z karty)
        """
        if not data or "pozycje" not in data:
            return data
        
        # Krok 0: Usuń PTU/VAT i inne nieprodukty
        data = self._filter_non_products(data)
        
        # Krok 1: Scalanie rabatów na pojedyncze produkty (używamy wspólnej metody)
        data = self._merge_discounts(data, fix_negative_discounts=False, strict_discount_name=False)
        
        # Krok 2: Weryfikacja i korekta sumy całkowitej
        items = data["pozycje"]
        suma_pozycji = self._calculate_items_sum(items)
        
        # Pobierz sumę z paragonu
        try:
            suma_paragonu = float(str(data["paragon_info"].get("suma_calkowita", 0)).replace(",", "."))
        except (ValueError, TypeError):
            suma_paragonu = 0.0
        
        # Weryfikacja i korekta sumy całkowitej
        roznica = suma_paragonu - suma_pozycji
        
        # Wykrywanie rabatu z karty (wieloetapowe)
        rabat_z_karty = self._detect_card_discount_from_items(items)
        if rabat_z_karty is None:
            rabat_z_karty = self._detect_card_discount_from_ocr(ocr_text) if ocr_text else None
        if rabat_z_karty is None:
            rabat_z_karty = self._detect_card_discount_from_pattern(roznica, suma_pozycji)
        
        # Korekta sumy całkowitej
        data = self._correct_total_sum(data, suma_pozycji, suma_paragonu, roznica, rabat_z_karty)
        
        return data


class AuchanStrategy(ReceiptStrategy):
    def get_system_prompt(self) -> str:
        return """
        Jesteś ekspertem od analizy paragonów sieci Auchan.
        
        KLUCZOWE ZASADY DLA AUCHAN - BARDZO WAŻNE:
        
        1. FORMAT POZYCJI - CZYTANIE OD LEWEJ DO PRAWEJ:
           Format: "NazwaProduktu KodProduktu Ilość xCena_jedn Cena_calkKodPodatkowy"
           
           Przykład 1: "ReWtymOplRec551061 1 x3,25 3,25A"
           - Nazwa: "ReWtymOplRec551061" (opłata recyklingowa - UWZGLĘDNIJ!)
           - Ilość: 1
           - Cena jednostkowa: 3.25
           - Cena całkowita: 3.25
           
           Przykład 2: "NAPOJ GAZ. 86851A 1 x4,48 4,48A"
           - Nazwa: "NAPOJ GAZ. 86851A"
           - Ilość: 1
           - Cena jednostkowa: 4.48
           - Cena całkowita: 4.48
           
           Przykład 3: "PAPIER TOAL 34663A 1 x19,98 19,98A"
           - Nazwa: "PAPIER TOAL 34663A"
           - Ilość: 1
           - Cena jednostkowa: 19.98
           - Cena całkowita: 19.98
           
           UWAGA: Każda pozycja ma SWOJĄ własną cenę. Nie mieszaj cen między pozycjami!
        
        2. CENY Z KODAMI PODATKOWYMI:
           Jeśli widzisz "19,98A" lub "3,25A", to cena to 19.98 lub 3.25.
           Kod podatkowy (A, B, C) na końcu ceny należy zignorować przy wyciąganiu wartości.
           Użyj przecinka jako separatora dziesiętnego (zamień na kropkę w JSON).
        
        3. OPLATY RECYKLINGOWE - OBOWIĄZKOWE:
           Pozycje typu "ReWtymOplRec551061" to opłaty recyklingowe - MUSISZ je uwzględnić jako normalne pozycje!
           Są one częścią sumy paragonu i muszą być zapisane jako pozycje z ceną.
           Nie pomijaj ich!
        
        4. PRODUKTY WAŻONE:
           Format "SER MOZZAR 751976C 0,304 x33,89 10,30C" oznacza:
           - Nazwa: "SER MOZZAR 751976C"
           - Ilość: 0.304 kg
           - Cena jednostkowa: 33.89 PLN/kg
           - Cena całkowita: 10.30 PLN
           - Jednostka: "kg"
        
        5. RABATY:
           Rabaty są zapisane jako osobne linie, np. "Rabat ORZESZKI W 492359C -0,80C"
           Traktuj to jako osobną pozycję z ujemną ceną całkowitą. System automatycznie scali to z produktem powyżej.
        
        6. KODY PRODUKTÓW:
           Kody produktów (np. "86851A", "34663A") są częścią nazwy produktu - zachowaj je w nazwa_raw.
        
        7. KOLEJNOŚĆ POZYCJI:
           Parsuj pozycje w kolejności, w jakiej występują na paragonie. Każda pozycja ma swoją unikalną cenę.
           Nie przypisuj ceny z jednej pozycji do innej!
        
        Wymagana struktura JSON:
        {
          "sklep_info": { "nazwa": "Auchan", "lokalizacja": "Adres sklepu lub null" },
          "paragon_info": { "data_zakupu": "2024-05-20", "suma_calkowita": "123.45" },
          "pozycje": [
            { "nazwa_raw": "Nazwa produktu z kodem", "ilosc": "1.0", "jednostka": "szt/kg", "cena_jedn": "1.23", "cena_calk": "1.23", "rabat": "0.00", "cena_po_rab": "1.23" }
          ]
        }
        """

    def post_process(self, data: ParsedData, ocr_text: Optional[str] = None) -> ParsedData:
        """
        Usuwanie pozycji, które wyglądają na błędy OCR (śmieci).
        UWAGA: Opłaty recyklingowe (ReWtymOplRec) są zachowywane, bo są częścią sumy paragonu.
        """
        if not data or "pozycje" not in data:
            return data

        # Najpierw usuń PTU/VAT
        data = self._filter_non_products(data)

        valid_items = []
        for item in data["pozycje"]:
            name = item.get("nazwa_raw", "")
            
            # Opłaty recyklingowe są ważne - zachowujemy je
            if "ReWtym" in name or "OplRec" in name:
                valid_items.append(item)
                continue
            
            # Filtr: jeśli nazwa to jeden długi ciąg bez spacji i ma cyfry w środku, to pewnie śmieć
            # ALE: jeśli ma sensowną cenę, to może być ważne (np. kody produktów)
            if len(name) > 15 and " " not in name and any(c.isdigit() for c in name):
                # Sprawdź czy ma sensowną cenę - jeśli tak, to może być ważne
                cena_calk = item.get("cena_calk", 0)
                try:
                    cena_float = float(str(cena_calk).replace(",", "."))
                    # Jeśli cena jest większa niż minimalna, to może być ważna pozycja
                    if cena_float > float(Config.MIN_PRODUCT_PRICE):
                        valid_items.append(item)
                        continue
                except (ValueError, TypeError):
                    pass
                # Jeśli nie ma sensownej ceny, to śmieć
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
        {
          "sklep_info": { "nazwa": "Nazwa sklepu", "lokalizacja": "Adres sklepu lub null" },
          "paragon_info": { "data_zakupu": "2024-05-20", "suma_calkowita": "123.45" },
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
