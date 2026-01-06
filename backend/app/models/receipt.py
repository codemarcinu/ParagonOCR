"""
Receipt and ReceiptItem database models.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Receipt(Base):
    """Receipt model representing a processed receipt."""
    
    __tablename__ = "receipts"
    __table_args__ = (
        Index("idx_receipt_shop", "shop_id"),
        Index("idx_receipt_date", "purchase_date"),
        Index("idx_receipt_shop_date", "shop_id", "purchase_date"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    purchase_date = Column(Date, nullable=False, index=True)
    purchase_time = Column(String, nullable=True)  # HH:MM format
    total_amount = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=True)
    tax = Column(Numeric(10, 2), nullable=True)
    source_file = Column(String, nullable=False)  # Path to uploaded file
    image_path = Column(String, nullable=True)  # Path to receipt image (zgodnie z przewodnikiem)
    ocr_text = Column(String, nullable=True)  # Raw OCR text
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, error (zgodnie z przewodnikiem)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    shop = relationship("Shop", back_populates="receipts")
    items = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")


class ReceiptItem(Base):
    """Receipt item model representing a single product on a receipt."""
    
    __tablename__ = "receipt_items"
    __table_args__ = (
        Index("idx_item_receipt", "receipt_id"),
        Index("idx_item_product", "product_id"),
        Index("idx_item_receipt_product", "receipt_id", "product_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    raw_name = Column(String, nullable=False)  # Original name from receipt
    quantity = Column(Numeric(10, 2), nullable=False, default=1.0)
    unit = Column(String, nullable=True)  # e.g., "szt", "kg", "l"
    unit_price = Column(Numeric(10, 2), nullable=True)
    total_price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), nullable=True, default=0.0)
    price_after_discount = Column(Numeric(10, 2), nullable=True)
    confidence = Column(Numeric(3, 2), nullable=True, default=1.0)
    
    # Relationships
    receipt = relationship("Receipt", back_populates="items")
    product = relationship("Product", back_populates="receipt_items")

