"""
Database models for ParagonOCR Web Edition.

All SQLAlchemy models are imported here for Alembic migrations.
"""

from app.models.receipt import Receipt, ReceiptItem
from app.models.product import Product, ProductAlias
from app.models.category import Category
from app.models.shop import Shop
from app.models.shopping_list import ShoppingList
from app.models.chat_history import Conversation, Message
from app.models.chat_history import Conversation, Message
from app.models.webauthn_key import WebAuthnKey
from app.models.user import User
from app.models.pantry import PantryItem, PantryStatus

__all__ = [
    "Receipt",
    "ReceiptItem",
    "Product",
    "ProductAlias",
    "Category",
    "Shop",
    "ShoppingList",
    "Conversation",
    "Message",
    "WebAuthnKey",
    "User",
    "PantryItem",
    "PantryStatus",
]

