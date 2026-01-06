from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class PantryStatus(str, enum.Enum):
    IN_STOCK = "IN_STOCK"   # Dostępne do spożycia
    CONSUMED = "CONSUMED"   # Zjedzone (sukces)
    WASTED = "WASTED"       # Wyrzucone/Przeterminowane (porażka)

class PantryItem(Base):
    __tablename__ = "pantry_items"

    id = Column(Integer, primary_key=True, index=True)
    
    # Co to jest?
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Skąd to mamy? (Opcjonalne, ale zalecane dla traceability)
    receipt_item_id = Column(Integer, ForeignKey("receipt_items.id"), nullable=True)
    
    # Ilość i Stan
    quantity = Column(Float, default=1.0) # Np. 0.5 (połowa opakowania)
    unit = Column(String, nullable=True)  # Np. "szt", "kg" (znormalizowane)
    
    # Cykl życia
    purchase_date = Column(Date, default=func.current_date())
    expiration_date = Column(Date, nullable=True) # AI to oszacuje
    
    status = Column(Enum(PantryStatus), default=PantryStatus.IN_STOCK, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacje
    product = relationship("Product", back_populates="pantry_items")
    # Using string reference to avoid circular imports if possible, or assume defined in Base metadata
    receipt_item = relationship("ReceiptItem") 
