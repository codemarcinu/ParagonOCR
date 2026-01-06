// Receipt types
export interface ReceiptResponse {
  id: number;
  shop: {
    id: number;
    name: string;
    location: string | null;
  };
  purchase_date: string;
  purchase_time: string | null;
  total_amount: number;
  items_count: number;
  status: 'pending' | 'processing' | 'completed' | 'error';
  created_at: string;
}

export interface ReceiptListResponse {
  receipts: ReceiptResponse[];
  total: number;
  skip: number;
  limit: number;
}

export interface ReceiptDetailsResponse extends ReceiptResponse {
  items: ReceiptItemResponse[];
  subtotal: number | null;
  tax: number | null;
  source_file: string;
}

export interface ReceiptItemResponse {
  id: number;
  product: {
    id: number | null;
    name: string | null;
    normalized_name: string | null;
  };
  raw_name: string;
  quantity: number;
  unit: string | null;
  unit_price: number | null;
  total_price: number;
  discount: number | null;
  confidence?: number;
}

export interface IngestReceiptRequest {
  text: string;
  date?: string;
  shop_name?: string;
}

// Product types
export interface ProductResponse {
  id: number;
  name: string;
  normalized_name: string;
  category_id: number | null;
  unit: string | null;
  created_at: string;
}

export interface CategoryResponse {
  id: number;
  name: string;
  icon: string | null;
  color: string | null;
}

// Chat types
export interface ConversationResponse {
  id: string;
  title: string;
  last_message: string;
  timestamp: string;
}

export interface MessageResponse {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  tokens_used?: number;
  rag_context?: {
    products_found?: number;
    receipts_found?: number;
  };
}

// Analytics types
export interface SpendingSummaryResponse {
  total_spent: number;
  receipt_count: number;
  average_receipt: number;
  period_days: number;
  daily_average: number;
}

export interface CategorySpendingResponse {
  category_id: number;
  category_name: string;
  total_spent: number;
  item_count: number;
}

export interface ShopSpendingResponse {
  shop_id: number;
  shop_name: string;
  total_spent: number;
  receipt_count: number;
  average_receipt: number;
}

// Auth types
export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}


// Pantry types
export type PantryStatus = 'IN_STOCK' | 'CONSUMED' | 'WASTED';

export interface PantryItemResponse {
  id: number;
  product: {
    id: number;
    name: string;
    normalized_name: string;
    unit: string | null;
  };
  quantity: number;
  unit: string | null;
  purchase_date: string;
  expiration_date: string | null; // Data w formacie YYYY-MM-DD
  status: PantryStatus;
  days_until_expiration?: number; // Opcjonalnie, jeśli backend to wylicza, lub policzymy na froncie
}
