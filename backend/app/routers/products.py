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
from app.dependencies import get_current_user
from app.schemas import ProductCreate, ProductUpdate, ProductResponse, CategoryResponse

router = APIRouter()


@router.get("", response_model=List[ProductResponse])
async def list_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
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

    products = query.offset(skip).limit(limit).all()
    return products


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    """List all product categories."""
    categories = db.query(Category).all()
    """List all product categories."""
    categories = db.query(Category).all()
    return categories


@router.post("", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new product."""
    db_product = Product(
        normalized_name=product.name,
        category_id=product.category_id,
        unit=product.unit,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update an existing product."""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.normalized_name = product.name
    db_product.category_id = product.category_id
    db_product.unit = product.unit

    # Also update 'name' alias if it was intended? Review model structure carefully.
    # Logic in previous file seemed to assume name and normalized_name are linked.
    # We will stick to updating normalized_name which is the main name.

    db.commit()
    db.refresh(db_product)
    return db_product
