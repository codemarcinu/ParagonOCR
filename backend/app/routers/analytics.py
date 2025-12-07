"""
API endpoints for Analytics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.analytics_service import analytics_service

router = APIRouter()


@router.get("/summary")
async def get_summary(days: int = 30, db: Session = Depends(get_db)):
    """Get high-level spending summary."""
    return analytics_service.get_spending_summary(db, days)


@router.get("/shops")
async def get_shop_spending(days: int = 30, db: Session = Depends(get_db)):
    """Get spending breakdown by shop."""
    return analytics_service.get_spending_by_shop(db, days)


@router.get("/categories")
async def get_category_spending(days: int = 30, db: Session = Depends(get_db)):
    """Get spending breakdown by category."""
    # Placeholder until categories are fully implemented
    return analytics_service.get_spending_by_category(db, days)
