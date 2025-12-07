"""
Shop database model.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Shop(Base):
    """Shop model representing a store where receipts were purchased."""
    
    __tablename__ = "shops"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    location = Column(String, nullable=True)
    
    # Relationships
    receipts = relationship("Receipt", back_populates="shop")

