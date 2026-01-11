from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, EmailStr, validator, root_validator, model_validator


# --- Shared ---
class PaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int


# --- Category ---
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = None
    icon: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True


# --- Shop ---
class ShopBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = None


class ShopCreate(ShopBase):
    pass


class ShopResponse(ShopBase):
    id: int

    class Config:
        from_attributes = True


# --- Product ---
class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category_id: Optional[int] = None
    unit: Optional[str] = Field(None, max_length=20)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductResponse(BaseModel):
    """Product response with normalized_name mapped to name."""
    id: int
    name: str = Field(..., min_length=1, max_length=200)  # Maps from normalized_name
    normalized_name: str
    category_id: Optional[int] = None
    unit: Optional[str] = Field(None, max_length=20)
    
    @model_validator(mode='before')
    @classmethod
    def map_normalized_name_to_name(cls, data):
        """Map normalized_name to name for ProductBase compatibility."""
        if isinstance(data, dict):
            if 'normalized_name' in data and 'name' not in data:
                data['name'] = data['normalized_name']
        elif hasattr(data, 'normalized_name'):
            # SQLAlchemy model
            return {
                'id': data.id,
                'name': data.normalized_name,
                'normalized_name': data.normalized_name,
                'category_id': data.category_id,
                'unit': data.unit,
            }
        return data
    
    class Config:
        from_attributes = True


# --- Receipt ---
class ReceiptItemBase(BaseModel):
    raw_name: str
    quantity: float = Field(..., gt=0)
    unit: Optional[str] = None
    unit_price: Optional[float] = Field(None, ge=0)
    total_price: float = Field(..., ge=0)
    discount: Optional[float] = Field(0.0, ge=0)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class ReceiptItemCreate(ReceiptItemBase):
    product_id: Optional[int] = None


class ReceiptItemResponse(ReceiptItemBase):
    id: int
    product: Optional[ProductResponse] = None

    class Config:
        from_attributes = True


class ReceiptBase(BaseModel):
    shop_id: int
    purchase_date: date
    purchase_time: Optional[str] = None
    total_amount: float = Field(..., ge=0)
    subtotal: Optional[float] = Field(None, ge=0)
    tax: Optional[float] = Field(None, ge=0)


class ReceiptCreate(ReceiptBase):
    items: List[ReceiptItemCreate] = []


class ReceiptResponse(ReceiptBase):
    id: int
    status: str
    shop: Optional[ShopResponse] = None
    items: List[ReceiptItemResponse] = []
    source_file: str
    created_at: datetime
    ocr_text: Optional[str] = None
    items_count: int = 0

    @model_validator(mode='before')
    @classmethod
    def calculate_items_count(cls, data):
        if hasattr(data, 'items'):
             if isinstance(data, dict):
                 data['items_count'] = len(data.get('items', []))
             else:
                 # SQLAlchemy object
                 setattr(data, 'items_count', len(data.items))
        return data

    class Config:
        from_attributes = True


class ReceiptListResponse(PaginatedResponse):
    receipts: List[ReceiptResponse]


class IngestReceiptRequest(BaseModel):
    text: str = Field(..., min_length=1)
    date: Optional[date] = None
    shop_name: Optional[str] = None


# --- Chat ---
class MessageBase(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class MessageResponse(MessageBase):
    timestamp: datetime

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    title: Optional[str] = None


class ConversationCreate(ConversationBase):
    pass


class ConversationResponse(ConversationBase):
    id: int
    last_message: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# --- Auth ---
class UserBase(BaseModel):
    email: Optional[str] = None  # Optional for passkey-only users


class UserCreate(UserBase):
    email: EmailStr  # Required and validated for traditional registration
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: int
    email: Optional[str] = None  # Optional for passkey-only users
    is_active: bool = True

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


# --- Passkey (WebAuthn) ---
class PasskeyRegistrationOptionsRequest(BaseModel):
    device_name: Optional[str] = None


class PasskeyRegistrationVerifyRequest(BaseModel):
    credential: dict = Field(..., description="Registration credential from WebAuthn API")
    challenge: str = Field(..., description="Challenge from registration options")


class PasskeyAuthenticationOptionsRequest(BaseModel):
    username: Optional[str] = None


class PasskeyAuthenticationVerifyRequest(BaseModel):
    credential: dict = Field(..., description="Authentication credential from WebAuthn API")
    challenge: str = Field(..., description="Challenge from authentication options")


class WebAuthnKeyResponse(BaseModel):
    id: int
    device_name: Optional[str]
    device_type: str
    last_used: Optional[datetime]
    created_at: datetime
    transports: Optional[List[str]]

    class Config:
        from_attributes = True
