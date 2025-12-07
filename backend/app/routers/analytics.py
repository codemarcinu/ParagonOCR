"""
API endpoints for Analytics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.services.analytics_service import analytics_service

router = APIRouter()


@router.get("/summary")
async def get_summary(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get high-level spending summary."""
    return analytics_service.get_spending_summary(db, days)


@router.get("/shops")
async def get_shop_spending(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get spending breakdown by shop."""
    return analytics_service.get_spending_by_shop(db, days)


@router.get("/categories")
async def get_category_spending(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get spending breakdown by category."""
    return analytics_service.get_spending_by_category(db, days)


@router.get("/trend")
async def get_daily_trend(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get daily spending trend."""
    return analytics_service.get_daily_trend(db, days)


@router.get("/monthly")
async def get_monthly_stats(
    months: int = 6,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get monthly spending statistics."""
    return analytics_service.get_monthly_trend(db, months)
