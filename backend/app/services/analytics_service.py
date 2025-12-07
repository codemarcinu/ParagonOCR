"""
Analytics Service for processing receipt data and generating insights.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

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
        """
        start_date = datetime.now() - timedelta(days=days)

        # Join ReceiptItem -> Product -> Category
        from app.models.product import Product
        from app.models.category import Category

        results = (
            db.query(
                Category.name,
                Category.color,
                Category.icon,
                func.sum(ReceiptItem.total_price).label("total"),
            )
            .join(Product, ReceiptItem.product_id == Product.id)
            .join(Category, Product.category_id == Category.id)
            .join(Receipt, ReceiptItem.receipt_id == Receipt.id)
            .filter(Receipt.purchase_date >= start_date)
            .group_by(Category.id)
            .order_by(func.sum(ReceiptItem.total_price).desc())
            .all()
        )

        return [
            {"category": name, "amount": float(total), "color": color, "icon": icon}
            for name, color, icon, total in results
        ]

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
        """Get monthly spending trend for chart."""
        start_date = datetime.now().replace(day=1) - timedelta(days=months * 30)

        # SQLite: strftime('%Y-%m', purchase_date)
        results = (
            db.query(
                func.strftime("%Y-%m", Receipt.purchase_date).label("month"),
                func.sum(Receipt.total_amount).label("total"),
                func.count(Receipt.id).label("count"),
            )
            .filter(Receipt.purchase_date >= start_date)
            .group_by("month")
            .order_by("month")
            .all()
        )

        return [
            {"month": month, "amount": float(total), "count": count}
            for month, total, count in results
        ]

    def get_daily_trend(self, db: Session, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily spending trend for chart."""
        start_date = datetime.now() - timedelta(days=days)

        results = (
            db.query(
                func.strftime("%Y-%m-%d", Receipt.purchase_date).label("day"),
                func.sum(Receipt.total_amount).label("total"),
            )
            .filter(Receipt.purchase_date >= start_date)
            .group_by("day")
            .order_by("day")
            .all()
        )

        return [{"date": day, "amount": float(total)} for day, total in results]


analytics_service = AnalyticsService()
