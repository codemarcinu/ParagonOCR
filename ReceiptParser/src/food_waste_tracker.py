"""
Moduł do śledzenia wygasających produktów i zarządzania marnotrawstwem żywności.

Funkcjonalności:
- Automatyczne wykrywanie wygasających produktów
- Obliczanie priorytetu konsumpcji
- Statystyki marnotrawstwa
"""

from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal

from .database import StanMagazynowy, Produkt, engine, sessionmaker


class FoodWasteTracker:
    """Klasa do śledzenia wygasających produktów i marnotrawstwa żywności."""

    # Priorytety konsumpcji
    PRIORITY_NORMAL = 0  # Normal - więcej niż 3 dni
    PRIORITY_WARNING = 1  # Warning - 3 dni lub mniej
    PRIORITY_CRITICAL = 2  # Critical - dziś wygasa
    PRIORITY_EXPIRED = 3  # Expired - już przeterminowany

    def __init__(self, session: Optional[Session] = None):
        """
        Inicjalizuje tracker.
        
        Args:
            session: Opcjonalna sesja SQLAlchemy. Jeśli None, tworzy nową.
        """
        self.session = session or sessionmaker(bind=engine)()
        self.warning_days = 3  # Domyślnie 3 dni przed wygaśnięciem

    def calculate_priority(self, expiry_date: Optional[date]) -> int:
        """
        Oblicza priorytet konsumpcji na podstawie daty ważności.
        
        Args:
            expiry_date: Data ważności produktu (może być None)
            
        Returns:
            Priorytet konsumpcji (0-3)
        """
        if expiry_date is None:
            return self.PRIORITY_NORMAL

        today = date.today()
        days_until_expiry = (expiry_date - today).days

        if days_until_expiry < 0:
            return self.PRIORITY_EXPIRED
        elif days_until_expiry == 0:
            return self.PRIORITY_CRITICAL
        elif days_until_expiry <= self.warning_days:
            return self.PRIORITY_WARNING
        else:
            return self.PRIORITY_NORMAL

    def update_priorities(self) -> int:
        """
        Aktualizuje priorytety konsumpcji dla wszystkich produktów w magazynie.
        
        Returns:
            Liczba zaktualizowanych produktów
        """
        stany = (
            self.session.query(StanMagazynowy)
            .filter(StanMagazynowy.ilosc > 0)
            .all()
        )

        updated_count = 0
        for stan in stany:
            new_priority = self.calculate_priority(stan.data_waznosci)
            if stan.priorytet_konsumpcji != new_priority:
                stan.priorytet_konsumpcji = new_priority
                updated_count += 1

        if updated_count > 0:
            self.session.commit()

        return updated_count

    def get_expiring_products(
        self, priority: Optional[int] = None, limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Pobiera produkty wygasające z magazynu.
        
        Args:
            priority: Opcjonalny priorytet do filtrowania (None = wszystkie)
            limit: Maksymalna liczba wyników
            
        Returns:
            Lista słowników z informacjami o produktach
        """
        query = (
            self.session.query(StanMagazynowy)
            .join(Produkt)
            .options(joinedload(StanMagazynowy.produkt).joinedload(Produkt.kategoria))
            .filter(StanMagazynowy.ilosc > 0)
        )

        if priority is not None:
            query = query.filter(StanMagazynowy.priorytet_konsumpcji == priority)

        # Sortuj: najpierw najwyższy priorytet, potem najbliższa data ważności
        query = query.order_by(
            StanMagazynowy.priorytet_konsumpcji.desc(),
            StanMagazynowy.data_waznosci.asc(),
        )

        if limit:
            query = query.limit(limit)

        stany = query.all()

        results = []
        for stan in stany:
            days_until = None
            if stan.data_waznosci:
                days_until = (stan.data_waznosci - date.today()).days

            results.append(
                {
                    "stan_id": stan.stan_id,
                    "produkt_id": stan.produkt_id,
                    "nazwa": stan.produkt.znormalizowana_nazwa,
                    "kategoria": (
                        stan.produkt.kategoria.nazwa_kategorii
                        if stan.produkt.kategoria
                        else "Inne"
                    ),
                    "ilosc": float(stan.ilosc),
                    "jednostka": stan.jednostka_miary or "szt",
                    "data_waznosci": (
                        stan.data_waznosci.isoformat() if stan.data_waznosci else None
                    ),
                    "days_until_expiry": days_until,
                    "priorytet": stan.priorytet_konsumpcji,
                    "zamrozone": stan.zamrozone,
                }
            )

        return results

    def get_expiry_alerts(self) -> Dict[str, List[Dict]]:
        """
        Pobiera alerty o wygasających produktach pogrupowane według priorytetu.
        
        Returns:
            Słownik z kluczami: 'expired', 'critical', 'warning', 'normal'
        """
        alerts = {
            "expired": self.get_expiring_products(priority=self.PRIORITY_EXPIRED),
            "critical": self.get_expiring_products(priority=self.PRIORITY_CRITICAL),
            "warning": self.get_expiring_products(priority=self.PRIORITY_WARNING),
            "normal": self.get_expiring_products(priority=self.PRIORITY_NORMAL),
        }

        return alerts

    def get_waste_statistics(self, days: int = 30) -> Dict:
        """
        Pobiera statystyki marnotrawstwa za ostatnie N dni.
        
        Args:
            days: Liczba dni wstecz do analizy
            
        Returns:
            Słownik ze statystykami
        """
        cutoff_date = date.today() - timedelta(days=days)

        # Produkty przeterminowane w ostatnich N dniach
        expired_products = (
            self.session.query(StanMagazynowy)
            .join(Produkt)
            .filter(StanMagazynowy.data_waznosci < cutoff_date)
            .filter(StanMagazynowy.ilosc > 0)
            .all()
        )

        total_expired_value = Decimal(0)
        expired_count = 0

        for stan in expired_products:
            # Przybliżona wartość (można rozszerzyć o rzeczywiste ceny z paragonów)
            expired_count += 1
            # TODO: Dodać rzeczywiste ceny z pozycji_paragonu jeśli dostępne

        return {
            "expired_count": expired_count,
            "expired_value": float(total_expired_value),
            "period_days": days,
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


# --- Funkcje pomocnicze ---


def get_expiring_products_summary(
    session: Optional[Session] = None,
) -> Dict[str, int]:
    """
    Pobiera podsumowanie wygasających produktów.
    
    Returns:
        Słownik z liczbami produktów według priorytetu
    """
    with FoodWasteTracker(session) as tracker:
        tracker.update_priorities()
        alerts = tracker.get_expiry_alerts()

        return {
            "expired": len(alerts["expired"]),
            "critical": len(alerts["critical"]),
            "warning": len(alerts["warning"]),
            "normal": len(alerts["normal"]),
        }

