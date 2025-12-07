"""
API endpoints for product management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.product import Product
from app.models.category import Category

router = APIRouter()


@router.get("", response_model=List[dict])
async def list_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List products with optional search and filtering."""
    query = db.query(Product)

    if search:
        query = query.filter(
            or_(
                Product.normalized_name.ilike(f"%{search}%"),
                # Add descriptions or other fields if available
            )
        )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    products = query.offset(skip).limit(limit).all()

    return [
        {
            "id": p.id,
            "name": p.normalized_name,
            "category_id": p.category_id,
            "unit": p.unit or "szt",
            # Add other fields as per model
        }
        for p in products
    ]


@router.get("/categories", response_model=List[dict])
async def list_categories(db: Session = Depends(get_db)):
    """List all product categories."""
    categories = db.query(Category).all()
    return [
        {"id": c.id, "name": c.name, "icon": c.icon, "color": c.color}
        for c in categories
    ]
