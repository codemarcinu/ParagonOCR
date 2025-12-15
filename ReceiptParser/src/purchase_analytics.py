"""
Moduł analityki zakupów - statystyki i wykresy dotyczące paragonów i zakupów.
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, asc, desc

from .database import (
    engine,
    Paragon,
    PozycjaParagonu,
    Produkt,
    Sklep,
    KategoriaProduktu,
    sessionmaker,
)


class PurchaseAnalytics:
    """Klasa do analizy zakupów i paragonów."""

    def __init__(self, session: Optional[Session] = None):
        """
        Inicjalizuje analitykę zakupów.
        
        Args:
            session: Opcjonalna sesja SQLAlchemy. Jeśli None, tworzy nową.
        """
        self.session = session or sessionmaker(bind=engine)()

    def get_total_statistics(self) -> Dict:
        """
        Zwraca ogólne statystyki zakupów.
        
        Returns:
            Słownik ze statystykami
        """
        total_receipts = self.session.query(Paragon).count()
        total_spent = (
            self.session.query(func.sum(Paragon.suma_paragonu)).scalar() or Decimal("0")
        )
        total_items = self.session.query(PozycjaParagonu).count()
        
        # Średnia wartość paragonu
        avg_receipt = (
            total_spent / total_receipts if total_receipts > 0 else Decimal("0")
        )
        
        # Najstarszy i najnowszy paragon
        oldest = (
            self.session.query(func.min(Paragon.data_zakupu)).scalar()
        )
        newest = (
            self.session.query(func.max(Paragon.data_zakupu)).scalar()
        )
        
        return {
            "total_receipts": total_receipts,
            "total_spent": float(total_spent),
            "total_items": total_items,
            "avg_receipt": float(avg_receipt),
            "oldest_date": oldest.isoformat() if oldest else None,
            "newest_date": newest.isoformat() if newest else None,
        }

    def get_spending_by_store(self, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Zwraca wydatki według sklepów.
        
        Args:
            limit: Maksymalna liczba sklepów do zwrócenia
            
        Returns:
            Lista krotek (nazwa_sklepu, suma_wydatków)
        """
        results = (
            self.session.query(
                Sklep.nazwa_sklepu,
                func.sum(Paragon.suma_paragonu).label("total")
            )
            .join(Paragon)
            .group_by(Sklep.nazwa_sklepu)
            .order_by(func.sum(Paragon.suma_paragonu).desc())
            .limit(limit)
            .all()
        )
        
        return [(row[0], float(row[1])) for row in results]

    def get_spending_by_category(self, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Zwraca wydatki według kategorii produktów.
        
        Args:
            limit: Maksymalna liczba kategorii do zwrócenia
            
        Returns:
            Lista krotek (nazwa_kategorii, suma_wydatków)
        """
        results = (
            self.session.query(
                KategoriaProduktu.nazwa_kategorii,
                func.sum(PozycjaParagonu.cena_po_rabacie).label("total")
            )
            .select_from(KategoriaProduktu)
            .join(Produkt)
            .join(PozycjaParagonu)
            .group_by(KategoriaProduktu.nazwa_kategorii)
            .order_by(func.sum(PozycjaParagonu.cena_po_rabacie).desc())
            .limit(limit)
            .all()
        )
        
        return [(row[0] or "Brak kategorii", float(row[1] or 0)) for row in results]

    def get_top_products(self, limit: int = 10) -> List[Tuple[str, int, float]]:
        """
        Zwraca najczęściej kupowane produkty.
        
        Args:
            limit: Maksymalna liczba produktów do zwrócenia
            
        Returns:
            Lista krotek (nazwa_produktu, liczba_zakupów, suma_wydatków)
        """
        results = (
            self.session.query(
                Produkt.znormalizowana_nazwa,
                func.count(PozycjaParagonu.pozycja_id).label("count"),
                func.sum(PozycjaParagonu.cena_po_rabacie).label("total")
            )
            .join(PozycjaParagonu)
            .group_by(Produkt.produkt_id, Produkt.znormalizowana_nazwa)
            .order_by(func.count(PozycjaParagonu.pozycja_id).desc())
            .limit(limit)
            .all()
        )
        
        return [
            (row[0], row[1], float(row[2] or 0)) for row in results
        ]

    def get_spending_over_time(
        self, days: int = 30, group_by: str = "day"
    ) -> List[Tuple[str, float]]:
        """
        Zwraca wydatki w czasie.
        
        Args:
            days: Liczba dni wstecz do analizy
            group_by: "day", "week", "month"
            
        Returns:
            Lista krotek (data, suma_wydatków)
        """
        start_date = date.today() - timedelta(days=days)
        
        query = (
            self.session.query(
                Paragon.data_zakupu,
                func.sum(Paragon.suma_paragonu).label("total")
            )
            .filter(Paragon.data_zakupu >= start_date)
            .group_by(Paragon.data_zakupu)
            .order_by(Paragon.data_zakupu)
        )
        
        results = query.all()
        
        # Formatuj daty
        formatted_results = []
        for row in results:
            date_val = row[0]
            if group_by == "day":
                date_str = date_val.strftime("%Y-%m-%d")
            elif group_by == "week":
                # Numer tygodnia
                date_str = f"{date_val.year}-W{date_val.isocalendar()[1]}"
            elif group_by == "month":
                date_str = date_val.strftime("%Y-%m")
            else:
                date_str = date_val.isoformat()
            
            formatted_results.append((date_str, float(row[1])))
        
        return formatted_results

    def get_monthly_statistics(self) -> List[Dict]:
        """
        Zwraca statystyki miesięczne.
        
        Returns:
            Lista słowników z statystykami dla każdego miesiąca
        """
        results = (
            self.session.query(
                extract("year", Paragon.data_zakupu).label("year"),
                extract("month", Paragon.data_zakupu).label("month"),
                func.count(Paragon.paragon_id).label("count"),
                func.sum(Paragon.suma_paragonu).label("total")
            )
            .group_by(
                extract("year", Paragon.data_zakupu),
                extract("month", Paragon.data_zakupu)
            )
            .order_by(
                extract("year", Paragon.data_zakupu).desc(),
                extract("month", Paragon.data_zakupu).desc()
            )
            .all()
        )
        
        stats = []
        for row in results:
            stats.append({
                "year": int(row[0]),
                "month": int(row[1]),
                "month_name": f"{int(row[1]):02d}/{int(row[0])}",
                "receipts_count": row[2],
                "total_spent": float(row[3] or 0),
            })
        
        return stats

    def get_receipts(
        self, 
        limit: int = 50, 
        sort_by: str = "date", 
        sort_desc: bool = True
    ) -> List[Dict]:
        """
        Zwraca listę paragonów z możliwością sortowania.
        
        Args:
            limit: Maksymalna liczba paragonów
            sort_by: Kolumna do sortowania ("date", "store", "total", "items")
            sort_desc: Czy sortować malejąco
            
        Returns:
            Lista słowników z informacjami o paragonach
        """
        query = self.session.query(Paragon).options(joinedload(Paragon.sklep))
        
        # Determine sorting
        order_func = desc if sort_desc else asc
        
        if sort_by == "store":
            query = query.join(Sklep).order_by(order_func(Sklep.nazwa_sklepu))
        elif sort_by == "total":
            query = query.order_by(order_func(Paragon.suma_paragonu))
        # Note: sorting by items_count is complex in SQL (needs subquery/count), 
        # so for simplicity we might do it in Python or just stick to simple cols.
        # Let's try basic date default.
        else: # date
            query = query.order_by(order_func(Paragon.data_zakupu))

        receipts = query.limit(limit).all()
        
        result = []
        for receipt in receipts:
            result.append({
                "id": receipt.paragon_id,
                "date": receipt.data_zakupu.isoformat() if receipt.data_zakupu else None,
                "store": receipt.sklep.nazwa_sklepu if receipt.sklep else "Nieznany",
                "total": float(receipt.suma_paragonu or 0),
                "items_count": len(receipt.pozycje),
            })
            
        # If sorting by items_count, do it in memory (since we have limited results anyway)
        if sort_by == "items":
            result.sort(key=lambda x: x["items_count"], reverse=sort_desc)
            
        return result

    def close(self):
        """Zamyka sesję bazy danych."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()



