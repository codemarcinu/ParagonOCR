
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
            r"(\d{2}\s\d{2}\s\d{4})", # DD MM YYYY (OCR noise)
        ]
        self.nip_pattern = r"NIP[:\s]*(\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2})"
        self.total_patterns = [
            r"(?:SUMA|RAZEM|DO ZAPŁATY|DO ZAPLATY|PLN)[\s:]*(\d+(?:[., ]\d+){0,2})",
            r"Suma PLN[\s:]*(\d+(?:[., ]\d+){0,2})",
        ]
        
        # Line item patterns
        # 1. Lidl/Biedronka style: "Name ... 2 * 3,99 7,98 A" -> Qty * UnitPrice TotalPrice Tax
        self.qty_price_total_pattern = r"(\d+(?:[.,]\d{3})?)\s*[x*]\s*(\d+(?:[.,]\d{2})?)\s+(\d+(?:[.,]\d{2})?)\s*[A-Z]?$"
        
        # 2. Classic: "Name ... Price [Tag]"
        self.simple_price_pattern = r"(\d+(?:[., ]\d{2})?)\s*[A-Z]?$" 

    def parse(self, text: str, shop_id: int) -> ReceiptCreate:
        """
        Parse raw OCR text into a ReceiptCreate object.
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        purchase_date = self._extract_date(text) or date.today()
        total_amount = self._extract_total(text) or 0.0
        nip = self._extract_nip(text)
        
        items = self._extract_items(lines)
        
        # Calculate subtotal based on items if needed
        subtotal = sum(i.total_price for i in items) if items else total_amount
        tax = 0.0 # Placeholder
        
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
                date_str = date_str.replace('.', '-').replace(' ', '-')
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
        # Reverse search for strict total patterns first (usually at bottom)
        lines = text.split('\n')
        for line in reversed(lines):
            for pattern in self.total_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    val = self._normalize_price(match.group(1))
                    if val > 0:
                        return val
        return None

    def _extract_items(self, lines: List[str]) -> List[ReceiptItemCreate]:
        items = []
        for line in lines:
            # Skip likely header/footer lines based on keywords
            if any(kw in line.upper() for kw in ["NIP", "SUMA", "RAZEM", "SPRZEDAZ", "PARAGON", "FISKALNY", "PTU", "KWOTA", "NETTO", "BRUTTO", "PODATEK", "PLATNOSC", "PŁATNOŚĆ", "KARTA", "GOTÓWKA", "RESZTA", "DATA", "ZAKUP"]):
                continue
            
            # Skip short lines
            if len(line) < 5:
                continue

            # Try Qty * UnitPrice TotalPrice pattern first (Strong signal)
            match_qty = re.search(self.qty_price_total_pattern, line)
            if match_qty:
                qty_str = match_qty.group(1)
                unit_price_str = match_qty.group(2)
                total_price_str = match_qty.group(3)
                
                qty = self._normalize_qty(qty_str)
                unit_price = self._normalize_price(unit_price_str)
                total_price = self._normalize_price(total_price_str)
                
                name_part = line[:match_qty.start()].strip()
                clean_name = self._clean_product_name(name_part)
                
                if len(clean_name) > 1 and total_price > 0:
                     items.append(ReceiptItemCreate(
                        raw_name=clean_name,
                        quantity=qty,
                        unit="szt", # Default, hard to extract accurately from this line format usually
                        total_price=total_price,
                        unit_price=unit_price,
                        discount=0.0
                    ))
                     continue

            # Fallback to simple price pattern
            match = re.search(self.simple_price_pattern, line)
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
        
        return items

    def _extract_qty_unit(self, name: str) -> Tuple[str, float, Optional[str]]:
        """
        Extract quantity and unit from name string if present (e.g. "MLEKO 2 SZT").
        Returns (name_without_qty, quantity, normalized_unit).
        """
        pattern = r"(.*)\s+(\d+(?:[.,]\d+)?)\s*([a-zA-Z]+[.]?)$"
        match = re.search(pattern, name)
        
        if match:
            potential_name = match.group(1).strip()
            qty_str = match.group(2).replace(',', '.')
            unit_str = match.group(3)
            
            normalized_unit = normalize_unit(unit_str)
            
            if normalized_unit:
                try:
                    qty = float(qty_str)
                    return potential_name, qty, normalized_unit
                except ValueError:
                    pass
        
        return name, 1.0, None

    def _normalize_price(self, price_str: str) -> float:
        if not price_str:
            return 0.0
        try:
            # Replace common OCR errors
            # 1. Replace spaces
            clean_str = price_str.replace(" ", "")
            # 2. Replace comma with dot
            clean_str = clean_str.replace(',', '.')
            # 3. Handle double dots e.g. '45..' -> '45.00' if needed, or stripping
            clean_str = clean_str.rstrip('.') 
            
            return float(clean_str)
        except ValueError:
            return 0.0

    def _normalize_qty(self, qty_str: str) -> float:
         try:
            clean_str = qty_str.replace(" ", "").replace(',', '.')
            return float(clean_str)
         except ValueError:
            return 1.0

    def _clean_product_name(self, raw: str) -> str:
        # Remove common OCR artifacts
        cleaned = re.sub(r"[~*_]", "", raw)
        # Normalize whitespace
        cleaned = " ".join(cleaned.split())
        return cleaned
