"""
Moduł Quick Add - szybkie dodawanie produktów z autocomplete.

Funkcjonalności:
- Autocomplete na podstawie historii produktów
- Szybkie dodawanie produktu (5s zamiast 60s OCR)
"""

from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from decimal import Decimal
from rapidfuzz import fuzz

from .database import Produkt, StanMagazynowy, engine, sessionmaker


class QuickAddHelper:
    """Klasa pomocnicza do szybkiego dodawania produktów."""

    def __init__(self, session: Optional[Session] = None):
        """
        Inicjalizuje helper.
        
        Args:
            session: Opcjonalna sesja SQLAlchemy. Jeśli None, tworzy nową.
        """
        self.session = session or sessionmaker(bind=engine)()

    def get_autocomplete_suggestions(
        self, query: str, limit: int = 10, min_similarity: int = 50
    ) -> List[Dict]:
        """
        Pobiera sugestie autocomplete na podstawie zapytania.
        
        Args:
            query: Tekst zapytania użytkownika
            limit: Maksymalna liczba sugestii
            min_similarity: Minimalne podobieństwo (0-100)
            
        Returns:
            Lista słowników z sugestiami produktów
        """
        if not query or len(query) < 2:
            # Jeśli zapytanie jest zbyt krótkie, zwróć najczęściej używane produkty
            return self.get_most_used_products(limit)

        # Pobierz wszystkie produkty
        produkty = self.session.query(Produkt).all()

        if not produkty:
            return []

        # Oblicz podobieństwo dla każdego produktu
        scored_products = []
        query_lower = query.lower()

        for produkt in produkty:
            # Sprawdź podobieństwo nazwy produktu
            similarity = fuzz.partial_ratio(
                query_lower, produkt.znormalizowana_nazwa.lower()
            )

            if similarity >= min_similarity:
                # Pobierz liczbę użyć (na podstawie stanów magazynowych)
                usage_count = (
                    self.session.query(func.count(StanMagazynowy.stan_id))
                    .filter(StanMagazynowy.produkt_id == produkt.produkt_id)
                    .scalar()
                )

                scored_products.append(
                    {
                        "produkt": produkt,
                        "similarity": similarity,
                        "usage_count": usage_count,
                    }
                )

        # Sortuj po podobieństwie i liczbie użyć
        scored_products.sort(
            key=lambda x: (x["similarity"], x["usage_count"]), reverse=True
        )

        # Zwróć najlepsze wyniki
        results = []
        for item in scored_products[:limit]:
            produkt = item["produkt"]
            results.append(
                {
                    "nazwa": produkt.znormalizowana_nazwa,
                    "produkt_id": produkt.produkt_id,
                    "similarity": item["similarity"],
                    "usage_count": item["usage_count"],
                }
            )

        return results

    def get_most_used_products(self, limit: int = 10) -> List[Dict]:
        """
        Pobiera najczęściej używane produkty.
        
        Args:
            limit: Maksymalna liczba produktów
            
        Returns:
            Lista słowników z produktami
        """
        # Pobierz produkty posortowane według liczby stanów magazynowych
        produkty = (
            self.session.query(
                Produkt,
                func.count(StanMagazynowy.stan_id).label("usage_count"),
            )
            .outerjoin(StanMagazynowy)
            .group_by(Produkt.produkt_id)
            .order_by(func.count(StanMagazynowy.stan_id).desc())
            .limit(limit)
            .all()
        )

        results = []
        for produkt, usage_count in produkty:
            results.append(
                {
                    "nazwa": produkt.znormalizowana_nazwa,
                    "produkt_id": produkt.produkt_id,
                    "similarity": 100,  # Domyślnie wysoka dla najczęściej używanych
                    "usage_count": usage_count or 0,
                }
            )

        return results

    def quick_add_product(
        self,
        nazwa: str,
        ilosc: Decimal,
        jednostka: Optional[str] = None,
        data_waznosci: Optional[datetime] = None,
    ) -> Dict:
        """
        Szybko dodaje produkt do magazynu.
        
        Args:
            nazwa: Nazwa produktu (znormalizowana)
            ilosc: Ilość produktu
            jednostka: Jednostka miary (domyślnie "szt")
            data_waznosci: Data ważności (opcjonalna)
            
        Returns:
            Słownik z informacjami o dodanym produkcie
        """
        if not nazwa or not nazwa.strip():
            raise ValueError("Nazwa produktu nie może być pusta")

        if ilosc <= 0:
            raise ValueError("Ilość musi być większa od zera")

        # Znajdź lub utwórz produkt
        produkt = (
            self.session.query(Produkt)
            .filter_by(znormalizowana_nazwa=nazwa.strip())
            .first()
        )

        if not produkt:
            # Utwórz nowy produkt
            produkt = Produkt(znormalizowana_nazwa=nazwa.strip())
            self.session.add(produkt)
            self.session.flush()

        # Dodaj do magazynu
        stan = StanMagazynowy(
            produkt_id=produkt.produkt_id,
            ilosc=ilosc,
            jednostka_miary=jednostka or "szt",
            data_waznosci=data_waznosci.date() if data_waznosci else None,
        )
        self.session.add(stan)
        self.session.commit()

        return {
            "success": True,
            "produkt_id": produkt.produkt_id,
            "nazwa": produkt.znormalizowana_nazwa,
            "ilosc": float(ilosc),
            "jednostka": jednostka or "szt",
        }

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

