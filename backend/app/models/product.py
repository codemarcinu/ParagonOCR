"""
Product and ProductAlias database models.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    """Product model representing a normalized product."""
    
    __tablename__ = "products"
    __table_args__ = (
        Index("idx_product_name", "normalized_name"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    normalized_name = Column(String, nullable=False, unique=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    unit = Column(String, nullable=True)  # e.g., "szt", "kg", "l" - zgodnie z przewodnikiem
    
    # Relationships
    category = relationship("Category", back_populates="products")
    aliases = relationship("ProductAlias", back_populates="product", cascade="all, delete-orphan")
    receipt_items = relationship("ReceiptItem", back_populates="product")


class ProductAlias(Base):
    """Product alias model mapping raw receipt names to normalized products."""
    
    __tablename__ = "product_aliases"
    __table_args__ = (
        Index("idx_alias_name", "raw_name"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    raw_name = Column(String, nullable=False, unique=True, index=True)
    
    # Relationships
    product = relationship("Product", back_populates="aliases")

