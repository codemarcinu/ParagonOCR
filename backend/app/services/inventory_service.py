import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.receipt import Receipt, ReceiptItem
from app.models.pantry import PantryItem, PantryStatus
from app.models.product import Product
from app.services import normalization

logger = logging.getLogger(__name__)

# Heurystyka: Domyślny czas życia produktu per kategoria (w dniach)
CATEGORY_SHELF_LIFE = {
    "Nabiał": 7,            # Mleko, jogurty szybko schodzą
    "Pieczywo": 2,          # Bułki czerstewieją
    "Owoce i Warzywa": 5,   # Świeże rzeczy
    "Mięso i Wędliny": 4,   # Surowe mięso krótko
    "Napoje": 90,           # Soki, woda - długo
    "Słodycze": 180,        # Batony, czekolada
    "Chemia i Kosmetyki": 730, # 2 lata
    "Alkohol": 3650,        # 10 lat :)
    "Inne": 14              # Bezpieczny default
}

DEFAULT_SHELF_LIFE_DAYS = 3 # Gdy nic nie pasuje (fallback z reviev)

class InventoryService:
    """
    Serwis zarządzający stanem spiżarni (Inventory/Pantry).
    Odpowiada za logikę biznesową przyjmowania zakupów (PZ - Przyjęcie Zewnętrzne).
    """

    def process_receipt_items(self, db: Session, receipt: Receipt, items_data: List[Dict[str, Any]]):
        """
        Przetwarza surowe dane z paragonu na rekordy w bazie (ReceiptItem)
        oraz aktualizuje stan spiżarni (PantryItem).

        Args:
            db: Sesja bazy danych
            receipt: Obiekt paragonu (już zapisany w bazie)
            items_data: Lista słowników z danymi produktów z LLM/Parsera
                        [{'name': 'Mleko', 'quantity': 1.0, 'price': 2.99, 'category': 'Nabiał'}, ...]
        """
        logger.info(f"Processing {len(items_data)} items for receipt {receipt.id}")

        for item_data in items_data:
            raw_name = item_data.get("name", "Nieznany produkt")
            quantity = float(item_data.get("quantity", 1.0))
            price = float(item_data.get("price", 0.0))
            total_price = float(item_data.get("total_price", 0.0))
            
            # 1. Normalizacja Produktu (Core Logic)
            # Zwraca (Product, is_new)
            product, is_new = normalization.normalize_product_name(
                db, 
                raw_name, 
                shop_id=receipt.shop_id
            )

            # Jeśli produkt jest nowy, spróbujmy go od razu zaklasyfikować
            if is_new or not product.category_id:
                # Sugestia kategorii z paragonu (z LLM)
                suggested_cat = item_data.get("category")
                if suggested_cat:
                    normalization._assign_category_by_name(db, product, suggested_cat)
                else:
                    # Fallback do klasyfikacji po nazwie
                    normalization.classify_product_category(db, product)

            # 2. Utwórz ReceiptItem (Historyczny zapis transakcji)
            receipt_item = ReceiptItem(
                receipt_id=receipt.id,
                product_id=product.id,
                raw_name=raw_name,
                quantity=quantity,
                unit=item_data.get("unit"), # np. "szt"
                unit_price=price,
                total_price=total_price,
                # discount? - na razie pomijamy per item, chyba że jest w danych
            )
            db.add(receipt_item)
            db.flush() # Żeby dostać ID

            # 3. Utwórz PantryItem (Stan magazynowy)
            # Pomijamy rzeczy, których nie wkładamy do lodówki? 
            # Na razie wkładamy WSZYSTKO co jest produktem.
            
            expiration_date = self._calculate_expiration_date(product, receipt.purchase_date)

            pantry_item = PantryItem(
                product_id=product.id,
                receipt_item_id=receipt_item.id,
                quantity=quantity,
                unit=item_data.get("unit"),
                purchase_date=receipt.purchase_date,
                expiration_date=expiration_date,
                status=PantryStatus.IN_STOCK
            )
            db.add(pantry_item)
            
            logger.info(f"Added to Pantry: {product.normalized_name} (Expires: {expiration_date})")

        # Commit is handled by the caller (usually) or here if we want atomic batch?
        # Better to let caller commit whole receipt transaction
        # But flush is good.

    def _calculate_expiration_date(self, product: Product, purchase_date: date) -> date:
        """
        Oblicza szacowaną datę ważności produktu.
        Hierarchia:
        1. Product.typical_shelf_life (jeśli ustawione ręcznie/z bazy)
        2. Kategoria produktu (Product.category.name) -> MAP
        3. Default fallback
        """
        shelf_life_days = None

        # 1. Sprawdź produkt
        if product.typical_shelf_life is not None:
            shelf_life_days = product.typical_shelf_life

        # 2. Sprawdź kategorię
        if shelf_life_days is None and product.category:
            cat_name = product.category.name
            # Proste mapowanie nazw kategorii
            # (można to ulepszyć o fuzzy matching, ale normalization pilnuje nazw)
            shelf_life_days = CATEGORY_SHELF_LIFE.get(cat_name)

        # 3. Default
        if shelf_life_days is None:
            shelf_life_days = DEFAULT_SHELF_LIFE_DAYS

        return purchase_date + timedelta(days=shelf_life_days)
