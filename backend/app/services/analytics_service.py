"""
Analytics Service for processing receipt data and generating insights.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.receipt import Receipt, ReceiptItem
from app.models.shop import Shop

logger = logging.getLogger(__name__)


class AnalyticsService:
    def get_spending_summary(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """Get spending summary for the last N days."""
        start_date = datetime.now() - timedelta(days=days)

        # Total spending
        total_spending = (
            db.query(func.sum(Receipt.total_amount))
            .filter(Receipt.purchase_date >= start_date)
            .scalar()
            or 0.0
        )

        # Receipt count
        receipt_count = (
            db.query(Receipt).filter(Receipt.purchase_date >= start_date).count()
        )

        # Average receipt value
        avg_receipt = total_spending / receipt_count if receipt_count > 0 else 0.0

        return {
            "period_days": days,
            "total_spending": float(total_spending),
            "receipt_count": receipt_count,
            "average_receipt": float(avg_receipt),
        }

    def get_spending_by_category(
        self, db: Session, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get spending breakdown by category.
        Note: Requires product categorization logic to be fully active.
        """
        start_date = datetime.now() - timedelta(days=days)

        # This is a simplified version. Real implementation needs joins with Product and Category
        # For MVP, we might group by Shop as a proxy if categories aren't fully populated

        return []

    def get_spending_by_shop(self, db: Session, days: int = 30) -> List[Dict[str, Any]]:
        """Get spending breakdown by shop."""
        start_date = datetime.now() - timedelta(days=days)

        results = (
            db.query(Shop.name, func.sum(Receipt.total_amount).label("total"))
            .join(Receipt)
            .filter(Receipt.purchase_date >= start_date)
            .group_by(Shop.name)
            .order_by(desc("total"))
            .all()
        )

        return [{"shop": name, "amount": float(total)} for name, total in results]

    def get_monthly_trend(self, db: Session, months: int = 6) -> List[Dict[str, Any]]:
        """Get monthly spending trend."""
        # SQLite specific date truncation might be needed or python-side aggregation
        # basic implementation
        pass


analytics_service = AnalyticsService()
