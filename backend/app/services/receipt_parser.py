
import re
from typing import Optional, List, Dict, Tuple
from datetime import datetime, date
from app.schemas import ReceiptCreate, ReceiptItemCreate
from app.services.normalization import normalize_unit

class ReceiptParser:
    """
    Parses OCR text into structured Receipt data with normalization.
    """

    def __init__(self):
        # Regex patterns
        self.date_patterns = [
            r"(\d{4}-\d{2}-\d{2})",  # YYYY-MM-DD
            r"(\d{2}-\d{2}-\d{4})",  # DD-MM-YYYY
            r"(\d{2}\.\d{2}\.\d{4})", # DD.MM.YYYY
        ]
        self.nip_pattern = r"NIP[:\s]*(\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})"
        self.total_patterns = [
            r"(?:SUMA|RAZEM|DO ZAPŁATY|DO ZAPLATY)[\s:]*(\d+[.,]\d{2})",
            r"Suma PLN[\s:]*(\d+[.,]\d{2})",
        ]
        # Line item pattern: Name ... Price [Tag]
        # Heuristic: ends with a number (price) and optional tag (A/B/C)
        self.item_price_pattern = r"(\d+[.,]\d{2})\s*[A-Z]?$" 

    def parse(self, text: str, shop_id: int) -> ReceiptCreate:
        """
        Parse raw OCR text into a ReceiptCreate object.
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        purchase_date = self._extract_date(text) or date.today()
        total_amount = self._extract_total(text) or 0.0
        nip = self._extract_nip(text)
        
        items = self._extract_items(lines)
        
        # Calculate subtotal/tax if not explicitly found (simplified)
        subtotal = total_amount 
        tax = 0.0 # Placeholder, logic can be added
        
        return ReceiptCreate(
            shop_id=shop_id,
            purchase_date=purchase_date,
            total_amount=total_amount,
            subtotal=subtotal,
            tax=tax,
            items=items,
            purchase_time="", # To handle
        )

    def _extract_date(self, text: str) -> Optional[date]:
        for pattern in self.date_patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(0)
                # Normalize separators
                date_str = date_str.replace('.', '-')
                try:
                    # Try common formats
                    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
                        try:
                            return datetime.strptime(date_str, fmt).date()
                        except ValueError:
                            continue
                except Exception:
                    continue
        return None

    def _extract_nip(self, text: str) -> Optional[str]:
        match = re.search(self.nip_pattern, text)
        if match:
            return match.group(1).replace("-", "").replace(" ", "")
        return None

    def _extract_total(self, text: str) -> Optional[float]:
        for pattern in self.total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._normalize_price(match.group(1))
        return None

    def _extract_items(self, lines: List[str]) -> List[ReceiptItemCreate]:
        items = []
        for line in lines:
            # Skip likely header/footer lines based on keywords
            if any(kw in line.upper() for kw in ["NIP", "SUMA", "RAZEM", "SPRZEDAZ", "PARAGON", "FISKALNY", "PTU", "KWOTA", "NETTO", "BRUTTO", "PODATEK", "PLATNOSC", "PŁATNOŚĆ", "KARTA", "GOTÓWKA"]):
                continue

            match = re.search(self.item_price_pattern, line)
            if match:
                price_str = match.group(1)
                total_price = self._normalize_price(price_str)
                
                # Assume everything before price is product name
                name_part = line[:match.start()].strip()
                
                # Basic cleaning
                clean_name = self._clean_product_name(name_part)
                
                # Try to extract quantity and unit from name
                final_name, quantity, unit = self._extract_qty_unit(clean_name)
                
                if len(final_name) > 1: # Avoid noise
                    # Filter out unrealistic prices
                    if total_price > 5000:
                        continue
                        
                    items.append(ReceiptItemCreate(
                        raw_name=final_name,
                        quantity=quantity,
                        unit=unit,
                        total_price=total_price,
                        unit_price=total_price / quantity if quantity else total_price,
                        discount=0.0
                    ))
        
        # Post-processing
        final_total = self._extract_total('\n'.join(lines)) or 0.0
        if final_total > 0:
            items = [i for i in items if i.total_price <= final_total * 1.5]

        return items

    def _extract_qty_unit(self, name: str) -> Tuple[str, float, Optional[str]]:
        """
        Extract quantity and unit from name string if present (e.g. "MLEKO 2 SZT").
        Returns (name_without_qty, quantity, normalized_unit).
        """
        # Pattern: Name + (Number) + (Unit) + End
        # Examples: "BUŁKA 2 SZT", "SER 0.5 KG"
        # We look for number + unit at the end
        
        # Polish decimal can be comma or dot
        pattern = r"(.*)\s+(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+[.]?)$"
        match = re.search(pattern, name)
        
        if match:
            potential_name = match.group(1).strip()
            qty_str = match.group(2).replace(',', '.')
            unit_str = match.group(3)
            
            # Normalize unit
            normalized_unit = normalize_unit(unit_str)
            
            if normalized_unit:
                try:
                    qty = float(qty_str)
                    return potential_name, qty, normalized_unit
                except ValueError:
                    pass
        
        # Fallback: assume 1.0, no unit
        return name, 1.0, None

    def _normalize_price(self, price_str: str) -> float:
        try:
            # Replace comma with dot
            clean_str = price_str.replace(',', '.').replace(" ", "")
            return float(clean_str)
        except ValueError:
            return 0.0

    def _clean_product_name(self, raw: str) -> str:
        # Remove common OCR artifacts
        cleaned = re.sub(r"[~*]", "", raw)
        # Normalize whitespace
        cleaned = " ".join(cleaned.split())
        return cleaned
