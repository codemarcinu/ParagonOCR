"""
ShoppingList database model (Phase 2 - zgodnie z przewodnikiem).
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime

from app.database import Base


class ShoppingList(Base):
    """Shopping list model for Phase 2 (zgodnie z przewodnikiem)."""
    
    __tablename__ = "shopping_lists"
    
    id = Column(Integer, primary_key=True, index=True)
    items_json = Column(JSON, nullable=False)  # JSON array of items
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)  # When list was completed

