# 🗄️ Database Schema

Complete database schema documentation for ParagonOCR Web Edition.

## Overview

The application uses **SQLite** database with **SQLAlchemy ORM**. The database is configured with **WAL (Write-Ahead Logging) mode** for better concurrency.

**Database Location:** `backend/data/receipts.db`  
**Migrations:** Managed via Alembic

## Entity-Relationship Diagram

```
┌──────────┐         ┌──────────┐         ┌──────────────┐
│   User   │         │ Receipt  │         │ ReceiptItem  │
├──────────┤         ├──────────┤         ├──────────────┤
│ id (PK)  │         │ id (PK)  │◄────────│ id (PK)      │
│ email    │         │ shop_id  │         │ receipt_id   │
│ password │         │ user_id  │         │ product_id   │
│ full_name│         │ date     │         │ quantity     │
│          │         │ total    │         │ unit_price   │
└──────────┘         │ status   │         │ total_price  │
                     │ file     │         └──────────────┘
                     └──────────┘                 │
                          │                       │
                          │                       ▼
                     ┌──────────┐         ┌──────────────┐
                     │   Shop   │         │   Product    │
                     ├──────────┤         ├──────────────┤
                     │ id (PK)  │         │ id (PK)      │
                     │ name     │         │ name         │
                     │ location │         │ normalized   │
                     └──────────┘         │ category_id  │
                                          │ unit         │
                                          └──────────────┘
                                                 │
                                                 │
                                          ┌──────────────┐
                                          │  Category    │
                                          ├──────────────┤
                                          │ id (PK)      │
                                          │ name         │
                                          │ color        │
                                          │ icon         │
                                          └──────────────┘

┌──────────────┐         ┌──────────────┐
│ Conversation│         │   Message    │
├──────────────┤         ├──────────────┤
│ id (PK)     │◄────────│ id (PK)      │
│ user_id     │         │ conv_id      │
│ title       │         │ role         │
│ created_at  │         │ content      │
│ updated_at  │         │ timestamp    │
└──────────────┘         │ tokens_used  │
                         │ rag_context  │
                         └──────────────┘

┌──────────┐         ┌──────────────┐
│   User   │         │  WebAuthnKey │
├──────────┤         ├──────────────┤
│ id (PK)  │◄────────│ id (PK)      │
│ email    │         │ user_id      │
│ password │         │ credential_id│
│          │         │ public_key   │
└──────────┘         │ device_name  │
                     │ device_type  │
                     │ last_used    │
                     │ created_at   │
                     │ transports   │
                     └──────────────┘
```

## Tables

### users

User accounts and authentication.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| email | VARCHAR | UNIQUE, NOT NULL | User email (login) |
| password_hash | VARCHAR | NOT NULL | Hashed password |
| full_name | VARCHAR | | User's full name |
| is_active | BOOLEAN | DEFAULT TRUE | Account status |
| created_at | DATETIME | DEFAULT NOW | Account creation time |

**Indexes:**
- `idx_users_email` on `email`

### shops

Store information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| name | VARCHAR | UNIQUE, NOT NULL | Shop name |
| location | VARCHAR | | Shop location/address |

**Indexes:**
- `idx_shops_name` on `name`

### receipts

Receipt metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| user_id | INTEGER | FK → users.id | Owner user |
| shop_id | INTEGER | FK → shops.id | Shop where purchased |
| purchase_date | DATE | NOT NULL | Purchase date |
| total_amount | DECIMAL(10,2) | NOT NULL | Total receipt amount |
| status | VARCHAR | DEFAULT 'processing' | Processing status |
| source_file | VARCHAR | | Path to uploaded file |
| created_at | DATETIME | DEFAULT NOW | Creation timestamp |
| updated_at | DATETIME | DEFAULT NOW | Last update timestamp |

**Status Values:**
- `processing` - Currently being processed
- `completed` - Successfully processed
- `error` - Processing failed

**Indexes:**
- `idx_receipts_user_id` on `user_id`
- `idx_receipts_shop_id` on `shop_id`
- `idx_receipts_date` on `purchase_date`
- Composite: `idx_receipts_user_date` on `(user_id, purchase_date)`

### receipt_items

Individual items from receipts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| receipt_id | INTEGER | FK → receipts.id | Parent receipt |
| product_id | INTEGER | FK → products.id | Product reference |
| quantity | DECIMAL(10,3) | NOT NULL | Item quantity |
| unit_price | DECIMAL(10,2) | NOT NULL | Price per unit |
| total_price | DECIMAL(10,2) | NOT NULL | Total price (qty × unit) |
| discount | DECIMAL(10,2) | DEFAULT 0 | Discount amount |

**Indexes:**
- `idx_receipt_items_receipt` on `receipt_id`
- `idx_receipt_items_product` on `product_id`
- Composite: `idx_receipt_items_receipt_product` on `(receipt_id, product_id)`

### categories

Product categories.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| name | VARCHAR | UNIQUE, NOT NULL | Category name |
| color | VARCHAR | | Hex color code |
| icon | VARCHAR | | Emoji or icon identifier |

**Indexes:**
- `idx_categories_name` on `name`

### products

Normalized product names.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| name | VARCHAR | NOT NULL | Original product name |
| normalized_name | VARCHAR | NOT NULL | Normalized name |
| category_id | INTEGER | FK → categories.id | Product category |
| unit | VARCHAR | | Unit of measure (kg, l, szt) |
| created_at | DATETIME | DEFAULT NOW | Creation timestamp |

**Indexes:**
- `idx_products_normalized` on `normalized_name`
- `idx_products_category` on `category_id`
- Full-text search: `idx_products_name_fts` on `name, normalized_name`

### conversations

Chat conversation threads.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| user_id | INTEGER | FK → users.id | Owner user |
| title | VARCHAR | | Conversation title |
| created_at | DATETIME | DEFAULT NOW | Creation timestamp |
| updated_at | DATETIME | DEFAULT NOW | Last update timestamp |

**Indexes:**
- `idx_conversations_user` on `user_id`
- `idx_conversations_updated` on `updated_at`

### messages

Individual chat messages.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| conversation_id | INTEGER | FK → conversations.id | Parent conversation |
| role | VARCHAR | NOT NULL | 'user' or 'assistant' |
| content | TEXT | NOT NULL | Message content |
| timestamp | DATETIME | DEFAULT NOW | Message timestamp |
| tokens_used | INTEGER | | LLM tokens consumed |
| rag_context | JSON | | RAG search context |

**Indexes:**
- `idx_messages_conversation` on `conversation_id`
- `idx_messages_timestamp` on `timestamp`
- Composite: `idx_messages_conv_time` on `(conversation_id, timestamp)`

### shopping_lists

Shopping list items.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| user_id | INTEGER | FK → users.id | Owner user |
| items_json | JSON | NOT NULL | List items (JSON array) |
| created_at | DATETIME | DEFAULT NOW | Creation timestamp |
| completed_at | DATETIME | | Completion timestamp |

**Indexes:**
- `idx_shopping_lists_user` on `user_id`
- `idx_shopping_lists_created` on `created_at`

### webauthn_keys

FIDO2 WebAuthn passkey credentials for passwordless authentication.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | UUID primary key |
| user_id | INTEGER | FK → users.id | Owner user |
| credential_id | BLOB | UNIQUE, NOT NULL | Binary credential ID (indexed) |
| public_key | BLOB | NOT NULL | Binary public key |
| device_name | VARCHAR | | User-friendly device name (e.g., 'iPhone 15') |
| device_type | VARCHAR | DEFAULT 'single-device' | Device type: 'single-device' or 'cross-device' |
| last_used | DATETIME | | Last authentication timestamp |
| created_at | DATETIME | DEFAULT NOW | Credential creation timestamp |
| transports | JSON | | Array of transport methods: ["internal", "usb", "ble", "nfc", "hybrid"] |

**Indexes:**
- `idx_webauthn_user_credential` on `(user_id, credential_id)`
- `idx_webauthn_credential_id` on `credential_id` (unique)

## Relationships

### One-to-Many

- **User → Receipts** - One user has many receipts
- **User → WebAuthnKeys** - One user can have multiple passkey credentials
- **User → Conversations** - One user has many conversations
- **User → Shopping Lists** - One user has many shopping lists
- **Shop → Receipts** - One shop has many receipts
- **Receipt → ReceiptItems** - One receipt has many items
- **Product → ReceiptItems** - One product appears in many receipt items
- **Category → Products** - One category has many products
- **Conversation → Messages** - One conversation has many messages

### Foreign Keys

All foreign keys have `ON DELETE CASCADE` to maintain referential integrity:
- Deleting a user deletes their receipts, conversations, and shopping lists
- Deleting a receipt deletes its items
- Deleting a conversation deletes its messages

## Database Configuration

### WAL Mode

SQLite is configured with WAL (Write-Ahead Logging) mode for better concurrency:

```python
# Enabled automatically in database.py
PRAGMA journal_mode=WAL;
```

**Benefits:**
- Multiple readers can access database simultaneously
- Writers don't block readers
- Better performance for concurrent access

### Connection Pooling

SQLAlchemy connection pool settings:
- **Pool Size:** 5 connections
- **Max Overflow:** 10 connections
- **Pool Timeout:** 30 seconds

## Migrations

Database schema changes are managed via **Alembic**.

**Create Migration:**
```bash
cd backend
alembic revision --autogenerate -m "description"
```

**Apply Migrations:**
```bash
alembic upgrade head
```

**Rollback:**
```bash
alembic downgrade -1
```

## Data Integrity

### Constraints

- **NOT NULL** constraints on required fields
- **UNIQUE** constraints on email, shop names, category names
- **CHECK** constraints on status values (to be added)
- **FOREIGN KEY** constraints with CASCADE deletes

### Validation

- **Pydantic schemas** validate data before database insertion
- **SQLAlchemy validators** ensure data integrity at ORM level
- **Application-level validation** for business rules

## Performance Considerations

### Indexes

Composite indexes on frequently queried column combinations:
- `(user_id, purchase_date)` for receipt queries
- `(conversation_id, timestamp)` for message ordering
- `(receipt_id, product_id)` for receipt item lookups

### Query Optimization

- Use `joinedload()` for eager loading relationships
- Limit result sets with `offset()` and `limit()`
- Use `select_related()` for foreign key joins

### Caching

- Consider Redis caching for frequently accessed data (future enhancement)
- Application-level caching for product lookups (future enhancement)

---

**Last Updated:** 2025-12-07  
**Version:** 1.0.0-beta

