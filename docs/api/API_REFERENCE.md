# 🔌 ParagonOCR Web API Reference

Complete API documentation for ParagonOCR Web Edition backend.

**Base URL:** `http://localhost:8000`  
**API Prefix:** `/api`  
**Authentication:** OAuth2 Bearer Token (JWT)

## Authentication

All endpoints (except `/health`) require authentication via Bearer token.

### POST /api/auth/token

OAuth2 compatible token login.

**Request:**
```http
POST /api/auth/token
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=password123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Rate Limit:** 5 requests/minute

### POST /api/auth/register

Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2025-12-07T10:00:00Z"
}
```

### GET /api/auth/passkey/register/options

Generate challenge for passkey registration. **No authentication required** - creates user automatically on verification.

**Request:**
```http
GET /api/auth/passkey/register/options?device_name=iPhone%2015
```

**Response:**
```json
{
  "challenge": "random-challenge-string",
  "rp": {
    "id": "localhost",
    "name": "ParagonOCR"
  },
  "user": {
    "id": "base64-encoded-user-id",
    "name": "user@example.com",
    "displayName": "user@example.com"
  },
  "pubKeyCredParams": [
    {
      "type": "public-key",
      "alg": -7
    }
  ],
  "authenticatorSelection": {
    "authenticatorAttachment": "platform",
    "userVerification": "required",
    "requireResidentKey": true
  }
}
```

**Rate Limit:** 5 requests/minute

### POST /api/auth/passkey/register/verify

Verify registration response and store credential. **No authentication required** - creates user automatically and returns JWT token for immediate login.

**Request:**
```json
{
  "credential": {
    "id": "credential-id",
    "rawId": "base64-encoded-id",
    "response": {
      "clientDataJSON": "base64-encoded-json",
      "attestationObject": "base64-encoded-object"
    },
    "type": "public-key"
  },
  "challenge": "challenge-from-options"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Passkey registered successfully",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "credential": {
    "id": "uuid-here",
    "device_name": "iPhone 15",
    "device_type": "single-device",
    "created_at": "2025-12-07T10:00:00Z"
  }
}
```

**Rate Limit:** 5 requests/minute

### POST /api/auth/passkey/authenticate/options

Generate challenge for passkey authentication. No authentication required.

**Request:**
```json
{
  "username": "user@example.com"
}
```

**Response:**
```json
{
  "challenge": "random-challenge-string",
  "rpId": "localhost",
  "allowCredentials": [
    {
      "id": "credential-id",
      "type": "public-key",
      "transports": ["internal"]
    }
  ],
  "userVerification": "required"
}
```

**Rate Limit:** 5 requests/minute

### POST /api/auth/passkey/authenticate/verify

Verify authentication response and create session/token. No authentication required.

**Request:**
```json
{
  "credential": {
    "id": "credential-id",
    "rawId": "base64-encoded-id",
    "response": {
      "clientDataJSON": "base64-encoded-json",
      "authenticatorData": "base64-encoded-data",
      "signature": "base64-encoded-signature",
      "userHandle": "base64-encoded-user-handle"
    },
    "type": "public-key"
  },
  "challenge": "challenge-from-options"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Rate Limit:** 5 requests/minute

### GET /api/auth/passkey/credentials

List all passkeys for the current user. Requires authentication.

**Response:**
```json
[
  {
    "id": 1,
    "device_name": "iPhone 15",
    "device_type": "single-device",
    "last_used": "2025-12-07T10:00:00Z",
    "created_at": "2025-12-07T09:00:00Z",
    "transports": ["internal"]
  }
]
```

### DELETE /api/auth/passkey/credentials/{credential_id}

Delete a passkey credential. Requires authentication.

**Response:**
```json
{
  "success": true,
  "message": "Passkey deleted successfully"
}
```

## Receipts

### POST /api/receipts/upload

Upload and process a receipt file.

**Request:**
```http
POST /api/receipts/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <PDF or image file>
```

**Response:**
```json
{
  "receipt_id": 123,
  "status": "processing",
  "message": "Receipt uploaded, processing in background"
}
```

**File Types:** PDF, PNG, JPG, JPEG, TIFF  
**Max Size:** 10MB (configurable)

**Processing Flow:**
1. File saved to disk
2. Receipt record created with status "processing"
3. Background task starts:
   - OCR extraction (Tesseract)
   - LLM parsing (Ollama)
   - Product normalization
   - Database save
4. WebSocket updates sent during processing

### GET /api/receipts

List all receipts for the current user.

**Query Parameters:**
- `skip` (int, default: 0) - Pagination offset
- `limit` (int, default: 50) - Items per page
- `shop_id` (int, optional) - Filter by shop
- `start_date` (date, optional) - Filter by date range
- `end_date` (date, optional) - Filter by date range

**Response:**
```json
{
  "items": [
    {
      "id": 123,
      "shop": {
        "id": 1,
        "name": "Lidl",
        "location": null
      },
      "purchase_date": "2025-12-07",
      "total_amount": 125.50,
      "status": "completed",
      "item_count": 15,
      "created_at": "2025-12-07T10:00:00Z"
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 50
}
```

### GET /api/receipts/{receipt_id}

Get detailed receipt information.

**Response:**
```json
{
  "id": 123,
  "shop": {
    "id": 1,
    "name": "Lidl"
  },
  "purchase_date": "2025-12-07",
  "total_amount": 125.50,
  "status": "completed",
  "source_file": "/data/uploads/receipt_123.pdf",
  "items": [
    {
      "id": 456,
      "product": {
        "id": 10,
        "name": "Mleko 3.2%",
        "normalized_name": "Mleko",
        "category": {
          "id": 2,
          "name": "Nabiał"
        }
      },
      "quantity": 2.0,
      "unit_price": 3.50,
      "total_price": 7.00
    }
  ],
  "created_at": "2025-12-07T10:00:00Z"
}
```

### WebSocket /api/receipts/{receipt_id}/ws

Real-time updates for receipt processing.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/receipts/123/ws');
```

**Messages:**
```json
{
  "stage": "ocr",
  "progress": 50,
  "message": "Extracting text from image...",
  "error": null
}
```

**Stages:**
- `upload` - File uploaded
- `ocr` - OCR extraction in progress
- `parsing` - LLM parsing in progress
- `saving` - Saving to database
- `completed` - Processing complete
- `error` - Error occurred

## Products

### GET /api/products

List products with optional search and filtering.

**Query Parameters:**
- `search` (string, optional) - Search in product names
- `category_id` (int, optional) - Filter by category
- `skip` (int, default: 0) - Pagination offset
- `limit` (int, default: 50) - Items per page

**Response:**
```json
[
  {
    "id": 10,
    "name": "Mleko 3.2%",
    "normalized_name": "Mleko",
    "category": {
      "id": 2,
      "name": "Nabiał",
      "color": "#FFD700",
      "icon": "🥛"
    },
    "unit": "l",
    "created_at": "2025-12-07T10:00:00Z"
  }
]
```

### GET /api/products/categories

List all product categories.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Piekarnicze",
    "color": "#8B4513",
    "icon": "🍞"
  },
  {
    "id": 2,
    "name": "Nabiał",
    "color": "#FFD700",
    "icon": "🥛"
  }
]
```

## Chat

### GET /api/chat/conversations

List all conversations for the current user.

**Response:**
```json
[
  {
    "id": 1,
    "title": "Przepis na obiad",
    "last_message": "Jakie produkty mam w lodówce?",
    "timestamp": "2025-12-07T10:00:00Z"
  }
]
```

### POST /api/chat/conversations

Create a new conversation.

**Request:**
```json
{
  "title": "Nowa rozmowa"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Nowa rozmowa",
  "last_message": "No messages",
  "timestamp": "2025-12-07T10:00:00Z"
}
```

### POST /api/chat/messages

Send a message in a conversation.

**Request:**
```json
{
  "conversation_id": 1,
  "content": "Jakie produkty mam w lodówce?",
  "query_type": "product_info"
}
```

**Response:**
```json
{
  "id": 123,
  "conversation_id": 1,
  "role": "assistant",
  "content": "W Twojej lodówce masz: Mleko, Jajka, Ser...",
  "timestamp": "2025-12-07T10:00:00Z",
  "tokens_used": 150,
  "rag_context": {
    "products_found": 5,
    "receipts_found": 2
  }
}
```

**Query Types:**
- `product_info` - Information about products
- `recipe_suggestion` - Recipe suggestions
- `shopping_list` - Shopping list generation
- `expiry_usage` - Using expiring products
- `nutrition_analysis` - Nutrition analysis
- `storage_advice` - Storage advice
- `waste_reduction` - Waste reduction tips
- `meal_planning` - Meal planning
- `budget_optimization` - Budget optimization
- `dietary_preferences` - Dietary preferences

## Analytics

### GET /api/analytics/summary

Get high-level spending summary.

**Query Parameters:**
- `days` (int, default: 30) - Number of days to analyze

**Response:**
```json
{
  "total_spent": 1250.50,
  "receipt_count": 42,
  "average_receipt": 29.77,
  "period_days": 30,
  "daily_average": 41.68
}
```

### GET /api/analytics/shops

Get spending by shop.

**Query Parameters:**
- `days` (int, default: 30) - Number of days to analyze

**Response:**
```json
[
  {
    "shop_id": 1,
    "shop_name": "Lidl",
    "total_spent": 750.30,
    "receipt_count": 25,
    "average_receipt": 30.01
  },
  {
    "shop_id": 2,
    "shop_name": "Biedronka",
    "total_spent": 500.20,
    "receipt_count": 17,
    "average_receipt": 29.42
  }
]
```

### GET /api/analytics/categories

Get spending by category.

**Query Parameters:**
- `days` (int, default: 30) - Number of days to analyze

**Response:**
```json
[
  {
    "category_id": 1,
    "category_name": "Piekarnicze",
    "total_spent": 150.50,
    "item_count": 45
  },
  {
    "category_id": 2,
    "category_name": "Nabiał",
    "total_spent": 200.30,
    "item_count": 60
  }
]
```

## Health Check

### GET /health

Health check endpoint (no authentication required).

**Response:**
```json
{
  "status": "healthy"
}
```

## Error Responses

All endpoints may return standard HTTP error codes:

- **400 Bad Request** - Invalid input data
- **401 Unauthorized** - Missing or invalid token
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

**Error Response Format:**
```json
{
  "detail": "Error message description"
}
```

## Rate Limiting

- **Auth endpoints:** 5 requests/minute
- **Other endpoints:** To be configured

## WebSocket Protocol

WebSocket connections use JSON messages:

**Client → Server:**
```json
{
  "type": "subscribe",
  "receipt_id": 123
}
```

**Server → Client:**
```json
{
  "type": "update",
  "stage": "ocr",
  "progress": 50,
  "message": "Processing...",
  "error": null
}
```

---

**Last Updated:** 2025-12-07  
**Version:** 1.0.0-beta

