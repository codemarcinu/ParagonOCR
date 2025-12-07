"""
Category database model.
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Category(Base):
    """Category model for product categorization."""
    
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    color = Column(String, nullable=True)  # Hex color code (zgodnie z przewodnikiem)
    icon = Column(String, nullable=True)  # Icon name/identifier (zgodnie z przewodnikiem)
    
    # Relationships
    products = relationship("Product", back_populates="category")

