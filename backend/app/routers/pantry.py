from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date

from app.database import get_db
from app.models.pantry import PantryItem, PantryStatus
from app.models.product import Product
from app.models.user import User # Assuming user auth needed eventually
from app.dependencies import get_current_user

router = APIRouter(
    tags=["pantry"]
)

# Schemat odpowiedzi (prosty, inline dla szybkości, można przenieść do schemas.py)
class PantryItemResponse(BaseModel):
    id: int
    product_name: str
    quantity: float
    unit: Optional[str]
    purchase_date: Optional[date]
    expiration_date: Optional[date]
    status: PantryStatus
    days_to_expire: Optional[int]

    class Config:
        orm_mode = True

class PantryUpdate(BaseModel):
    quantity: Optional[float] = None
    status: Optional[PantryStatus] = None

@router.get("/", response_model=List[PantryItemResponse])
def get_pantry_items(
    status: Optional[PantryStatus] = PantryStatus.IN_STOCK,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user) # Uncomment for auth
):
    """
    Pobiera zawartość spiżarni (domyślnie tylko IN_STOCK).
    """
    query = db.query(PantryItem).join(Product)
    
    if status:
        query = query.filter(PantryItem.status == status)
        
    items = query.order_by(PantryItem.expiration_date.asc()).all()
    
    results = []
    today = date.today()
    
    for item in items:
        days = None
        if item.expiration_date:
            days = (item.expiration_date - today).days
            
        results.append(PantryItemResponse(
            id=item.id,
            product_name=item.product.normalized_name,
            quantity=item.quantity,
            unit=item.unit,
            purchase_date=item.purchase_date,
            expiration_date=item.expiration_date,
            status=item.status,
            days_to_expire=days
        ))
        
    return results

@router.patch("/{item_id}", response_model=PantryItemResponse)
def update_pantry_item(
    item_id: int,
    update_data: PantryUpdate,
    db: Session = Depends(get_db)
):
    """
    Aktualizuje stan elementu (np. zjedzone, wyrzucone, zmiana ilości).
    """
    item = db.query(PantryItem).filter(PantryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    if update_data.status:
        item.status = update_data.status
    if update_data.quantity is not None:
        item.quantity = update_data.quantity
        
    db.commit()
    db.refresh(item)
    
    # Return mapping
    days = None
    if item.expiration_date:
        days = (item.expiration_date - date.today()).days
        
    return PantryItemResponse(
        id=item.id,
        product_name=item.product.normalized_name,
        quantity=item.quantity,
        unit=item.unit,
        purchase_date=item.purchase_date,
        expiration_date=item.expiration_date,
        status=item.status,
        days_to_expire=days
    )
