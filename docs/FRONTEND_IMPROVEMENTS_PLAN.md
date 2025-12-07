# 🎯 Plan Implementacji Ulepszeń Frontendu

**Data utworzenia:** 2025-12-07  
**Wersja:** 1.0.0  
**Status:** Do implementacji

---

## 📋 Spis Treści

1. [Przegląd](#przegląd)
2. [Faza 1: Priorytet Wysoki](#faza-1-priorytet-wysoki)
3. [Faza 2: Priorytet Średni](#faza-2-priorytet-średni)
4. [Faza 3: Priorytet Niski](#faza-3-priorytet-niski)
5. [Szacunki czasowe](#szacunki-czasowe)
6. [Checklist implementacji](#checklist-implementacji)

---

## 📊 Przegląd

### Cele główne:
1. ✅ **Streaming w Chat** - Real-time odpowiedzi AI
2. ✅ **Environment Variables** - Konfiguracja przez .env
3. ✅ **Error Boundary** - Globalna obsługa błędów
4. ✅ **Ujednolicone Loading States** - Spójne UX
5. ✅ **ShoppingList Implementation** - Funkcjonalność listy zakupów
6. ✅ **Global Components** - Reużywalne komponenty UI
7. ✅ **Type Safety** - Eliminacja `any`
8. ✅ **Toast Notifications** - System powiadomień

### Technologie do dodania:
- **react-hot-toast** lub **sonner** - Toast notifications
- **@tanstack/react-query** (opcjonalnie) - Lepsze zarządzanie cache i loading states

---

## 🚀 Faza 1: Priorytet Wysoki

### 1.1 Environment Variables Configuration

**Cel:** Przenieść hardcoded URL do zmiennych środowiskowych

**Pliki do modyfikacji:**
- `frontend/.env.example` (utworzyć)
- `frontend/.env.local` (sprawdzić/utworzyć)
- `frontend/src/lib/api.ts` (modyfikacja)
- `frontend/vite.config.ts` (sprawdzić proxy)

**Kroki:**

1. **Utworzyć `.env.example`:**
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

2. **Zaktualizować `api.ts`:**
```typescript
// Przed:
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  // ...
});

// Po:
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  // ...
});

export { WS_BASE_URL };
```

3. **Zaktualizować `ReceiptUploader.tsx`:**
```typescript
// Przed:
const wsUrl = `${wsProtocol}//${window.location.hostname}:8000/api/receipts/ws/processing/${receiptId}`;

// Po:
import { WS_BASE_URL } from '@/lib/api';
const wsUrl = `${WS_BASE_URL}/api/receipts/ws/processing/${receiptId}`;
```

**Szacowany czas:** 30 minut

---

### 1.2 Error Boundary Implementation

**Cel:** Globalna obsługa błędów React

**Pliki do utworzenia:**
- `frontend/src/components/ErrorBoundary.tsx`
- `frontend/src/pages/ErrorPage.tsx`

**Kroki:**

1. **Utworzyć `ErrorBoundary.tsx`:**
```typescript
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    // Można wysłać do error tracking service (Sentry, etc.)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
          <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 dark:bg-red-900 rounded-full mb-4">
              <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white text-center mb-2">
              Something went wrong
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center mb-4">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.href = '/';
              }}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Go to Home
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

2. **Zaktualizować `App.tsx`:**
```typescript
import { ErrorBoundary } from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <Router>
        {/* ... routes ... */}
      </Router>
    </ErrorBoundary>
  );
}
```

**Szacowany czas:** 1 godzina

---

### 1.3 Chat Streaming Implementation

**Cel:** Real-time streaming odpowiedzi AI przez WebSocket

**Pliki do modyfikacji:**
- `frontend/src/store/chatStore.ts`
- `frontend/src/pages/Chat.tsx`

**Kroki:**

1. **Zaktualizować `chatStore.ts` - dodać WebSocket:**
```typescript
interface ChatStore {
  // ... existing fields
  wsConnection: WebSocket | null;
  currentMessageBuffer: string; // For streaming chunks
  
  // ... existing methods
  connectWebSocket: (conversationId: string) => void;
  disconnectWebSocket: () => void;
  sendMessageStreaming: (content: string) => Promise<void>;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  // ... existing state
  wsConnection: null,
  currentMessageBuffer: '',
  
  connectWebSocket: (conversationId: string) => {
    const { wsConnection } = get();
    if (wsConnection) {
      wsConnection.close();
    }
    
    const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
    const ws = new WebSocket(`${WS_BASE_URL}/api/chat/conversations/${conversationId}/stream`);
    
    ws.onopen = () => {
      console.log('Chat WebSocket connected');
      set({ wsConnection: ws });
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'chunk') {
        // Append chunk to buffer
        set((state) => ({
          currentMessageBuffer: state.currentMessageBuffer + data.content
        }));
        
        // Update last message in real-time
        set((state) => {
          const newMessages = [...state.messages];
          const lastMsg = newMessages[newMessages.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content = state.currentMessageBuffer;
          } else {
            // Create new assistant message
            newMessages.push({
              id: Date.now().toString(),
              role: 'assistant',
              content: state.currentMessageBuffer,
              timestamp: new Date().toISOString()
            });
          }
          return { messages: newMessages };
        });
      } else if (data.type === 'done') {
        // Finalize message
        set((state) => {
          const newMessages = [...state.messages];
          const lastMsg = newMessages[newMessages.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content = state.currentMessageBuffer;
            lastMsg.id = data.message_id || lastMsg.id;
          }
          return {
            messages: newMessages,
            currentMessageBuffer: '',
            streaming: false
          };
        });
      } else if (data.type === 'error') {
        set({ streaming: false, error: data.message });
      }
    };
    
    ws.onerror = (error) => {
      console.error('Chat WebSocket error:', error);
      set({ streaming: false, error: 'WebSocket connection error' });
    };
    
    ws.onclose = () => {
      console.log('Chat WebSocket closed');
      set({ wsConnection: null, streaming: false });
    };
  },
  
  disconnectWebSocket: () => {
    const { wsConnection } = get();
    if (wsConnection) {
      wsConnection.close();
      set({ wsConnection: null });
    }
  },
  
  sendMessageStreaming: async (content: string) => {
    const { currentConversationId, messages, wsConnection } = get();
    if (!currentConversationId) return;
    
    // Add user message
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    };
    
    set({ 
      messages: [...messages, userMsg],
      streaming: true,
      currentMessageBuffer: ''
    });
    
    // Connect WebSocket if not connected
    if (!wsConnection || wsConnection.readyState !== WebSocket.OPEN) {
      get().connectWebSocket(currentConversationId);
      // Wait for connection
      await new Promise((resolve) => {
        const checkConnection = () => {
          if (get().wsConnection?.readyState === WebSocket.OPEN) {
            resolve(true);
          } else {
            setTimeout(checkConnection, 100);
          }
        };
        checkConnection();
      });
    }
    
    // Send message through WebSocket
    const ws = get().wsConnection;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ content }));
    } else {
      set({ streaming: false, error: 'WebSocket not connected' });
    }
  },
  
  // Update existing sendMessage to use streaming
  sendMessage: async (content: string) => {
    await get().sendMessageStreaming(content);
  },
  
  // Cleanup on conversation change
  selectConversation: async (id) => {
    get().disconnectWebSocket();
    // ... existing code ...
    get().connectWebSocket(id);
  }
}));
```

2. **Zaktualizować `Chat.tsx` - użyć streaming:**
```typescript
// W handleSend:
await sendMessage(content); // Automatycznie używa WebSocket streaming
```

**Backend wymagania:**
- Endpoint WebSocket: `/api/chat/conversations/{id}/stream`
- Format wiadomości:
  ```json
  {"type": "chunk", "content": "fragment tekstu"}
  {"type": "done", "message_id": "uuid"}
  {"type": "error", "message": "error text"}
  ```

**Szacowany czas:** 3-4 godziny (w tym backend WebSocket endpoint)

---

### 1.4 Unified Loading States

**Cel:** Spójne komponenty loading/skeleton

**Pliki do utworzenia:**
- `frontend/src/components/ui/LoadingSpinner.tsx`
- `frontend/src/components/ui/Skeleton.tsx`
- `frontend/src/components/ui/LoadingCard.tsx`

**Kroki:**

1. **Utworzyć `LoadingSpinner.tsx`:**
```typescript
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function LoadingSpinner({ size = 'md', className = '' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12'
  };
  
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className={`animate-spin rounded-full border-b-2 border-blue-600 ${sizeClasses[size]}`} />
    </div>
  );
}
```

2. **Utworzyć `Skeleton.tsx`:**
```typescript
interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
}

export function Skeleton({ className = '', variant = 'rectangular' }: SkeletonProps) {
  const baseClasses = 'animate-pulse bg-gray-200 dark:bg-gray-700';
  const variantClasses = {
    text: 'h-4 rounded',
    circular: 'rounded-full',
    rectangular: 'rounded'
  };
  
  return (
    <div className={`${baseClasses} ${variantClasses[variant]} ${className}`} />
  );
}
```

3. **Utworzyć `LoadingCard.tsx`:**
```typescript
export function LoadingCard() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <Skeleton className="h-6 w-1/3 mb-4" variant="text" />
      <Skeleton className="h-4 w-full mb-2" variant="text" />
      <Skeleton className="h-4 w-5/6 mb-2" variant="text" />
      <Skeleton className="h-4 w-4/6" variant="text" />
    </div>
  );
}
```

4. **Zaktualizować komponenty - użyć nowych loading states:**
   - `Dashboard.tsx` - LoadingCard dla tabeli
   - `Receipts.tsx` - Skeleton dla wierszy
   - `Products.tsx` - Skeleton dla produktów
   - `Analytics.tsx` - LoadingSpinner dla wykresów

**Szacowany czas:** 2 godziny

---

## 🎨 Faza 2: Priorytet Średni

### 2.1 ShoppingList Implementation

**Cel:** Pełna funkcjonalność listy zakupów

**Pliki do utworzenia/modyfikacji:**
- `frontend/src/store/shoppingListStore.ts` (nowy)
- `frontend/src/pages/ShoppingList.tsx` (przepisać)
- `frontend/src/components/ShoppingListItem.tsx` (nowy)
- `frontend/src/lib/api.ts` (dodać funkcje API)

**Kroki:**

1. **Utworzyć `shoppingListStore.ts`:**
```typescript
import { create } from 'zustand';
import apiClient from '@/lib/api';

export interface ShoppingListItem {
  id: number;
  product_id: number | null;
  product_name: string;
  quantity: number;
  unit: string;
  checked: boolean;
  priority: 'low' | 'medium' | 'high';
  notes?: string;
}

export interface ShoppingList {
  id: number;
  title: string;
  items: ShoppingListItem[];
  created_at: string;
  completed_at: string | null;
}

interface ShoppingListStore {
  lists: ShoppingList[];
  currentList: ShoppingList | null;
  loading: boolean;
  error: string | null;
  
  fetchLists: () => Promise<void>;
  createList: (title: string) => Promise<void>;
  selectList: (id: number) => Promise<void>;
  addItem: (item: Omit<ShoppingListItem, 'id' | 'checked'>) => Promise<void>;
  toggleItem: (itemId: number) => Promise<void>;
  removeItem: (itemId: number) => Promise<void>;
  completeList: () => Promise<void>;
  generateFromMealPlan: () => Promise<void>; // Future: AI-generated list
}

export const useShoppingListStore = create<ShoppingListStore>((set, get) => ({
  lists: [],
  currentList: null,
  loading: false,
  error: null,
  
  fetchLists: async () => {
    set({ loading: true, error: null });
    try {
      const response = await apiClient.get('/shopping-lists');
      set({ lists: response.data, loading: false });
    } catch (error) {
      set({ loading: false, error: 'Failed to fetch shopping lists' });
    }
  },
  
  createList: async (title: string) => {
    set({ loading: true });
    try {
      const response = await apiClient.post('/shopping-lists', { title, items: [] });
      const newList = response.data;
      set((state) => ({
        lists: [newList, ...state.lists],
        currentList: newList,
        loading: false
      }));
    } catch (error) {
      set({ loading: false, error: 'Failed to create list' });
    }
  },
  
  selectList: async (id: number) => {
    set({ loading: true });
    try {
      const response = await apiClient.get(`/shopping-lists/${id}`);
      set({ currentList: response.data, loading: false });
    } catch (error) {
      set({ loading: false, error: 'Failed to load list' });
    }
  },
  
  addItem: async (item) => {
    const { currentList } = get();
    if (!currentList) return;
    
    set({ loading: true });
    try {
      const response = await apiClient.post(`/shopping-lists/${currentList.id}/items`, item);
      set((state) => ({
        currentList: {
          ...state.currentList!,
          items: [...state.currentList!.items, response.data]
        },
        loading: false
      }));
    } catch (error) {
      set({ loading: false, error: 'Failed to add item' });
    }
  },
  
  toggleItem: async (itemId: number) => {
    const { currentList } = get();
    if (!currentList) return;
    
    const item = currentList.items.find(i => i.id === itemId);
    if (!item) return;
    
    try {
      await apiClient.patch(`/shopping-lists/${currentList.id}/items/${itemId}`, {
        checked: !item.checked
      });
      
      set((state) => ({
        currentList: {
          ...state.currentList!,
          items: state.currentList!.items.map(i =>
            i.id === itemId ? { ...i, checked: !i.checked } : i
          )
        }
      }));
    } catch (error) {
      set({ error: 'Failed to update item' });
    }
  },
  
  removeItem: async (itemId: number) => {
    const { currentList } = get();
    if (!currentList) return;
    
    try {
      await apiClient.delete(`/shopping-lists/${currentList.id}/items/${itemId}`);
      set((state) => ({
        currentList: {
          ...state.currentList!,
          items: state.currentList!.items.filter(i => i.id !== itemId)
        }
      }));
    } catch (error) {
      set({ error: 'Failed to remove item' });
    }
  },
  
  completeList: async () => {
    const { currentList } = get();
    if (!currentList) return;
    
    try {
      await apiClient.patch(`/shopping-lists/${currentList.id}`, {
        completed_at: new Date().toISOString()
      });
      set((state) => ({
        currentList: {
          ...state.currentList!,
          completed_at: new Date().toISOString()
        }
      }));
    } catch (error) {
      set({ error: 'Failed to complete list' });
    }
  },
  
  generateFromMealPlan: async () => {
    // Future: AI-generated shopping list from meal plan
    set({ error: 'Not implemented yet' });
  }
}));
```

2. **Przepisać `ShoppingList.tsx`:**
```typescript
import { useEffect, useState } from 'react';
import { useShoppingListStore } from '@/store/shoppingListStore';
import { Plus, CheckCircle2, Circle, Trash2, Sparkles } from 'lucide-react';
import { ShoppingListItem } from '@/components/ShoppingListItem';

export function ShoppingList() {
  const {
    lists,
    currentList,
    loading,
    error,
    fetchLists,
    createList,
    selectList,
    addItem,
    toggleItem,
    removeItem,
    completeList
  } = useShoppingListStore();
  
  const [newItemName, setNewItemName] = useState('');
  const [newItemQuantity, setNewItemQuantity] = useState('1');
  const [showNewListModal, setShowNewListModal] = useState(false);
  const [newListTitle, setNewListTitle] = useState('');
  
  useEffect(() => {
    fetchLists();
    if (lists.length > 0 && !currentList) {
      selectList(lists[0].id);
    }
  }, [fetchLists]);
  
  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemName.trim() || !currentList) return;
    
    await addItem({
      product_name: newItemName,
      quantity: parseFloat(newItemQuantity) || 1,
      unit: 'szt',
      priority: 'medium'
    });
    
    setNewItemName('');
    setNewItemQuantity('1');
  };
  
  const handleCreateList = async () => {
    if (!newListTitle.trim()) return;
    await createList(newListTitle);
    setNewListTitle('');
    setShowNewListModal(false);
  };
  
  const checkedCount = currentList?.items.filter(i => i.checked).length || 0;
  const totalCount = currentList?.items.length || 0;
  
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Shopping Lists
          </h1>
          <button
            onClick={() => setShowNewListModal(true)}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <Plus className="w-5 h-5 mr-2" />
            New List
          </button>
        </div>
        
        {/* Lists Sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-4">Your Lists</h2>
              {lists.map((list) => (
                <button
                  key={list.id}
                  onClick={() => selectList(list.id)}
                  className={`w-full text-left p-3 rounded-md mb-2 transition-colors ${
                    currentList?.id === list.id
                      ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  <p className="font-medium text-gray-900 dark:text-white">{list.title}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {list.items.length} items
                  </p>
                </button>
              ))}
            </div>
          </div>
          
          {/* Current List */}
          <div className="lg:col-span-2">
            {currentList ? (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex justify-between items-center">
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                        {currentList.title}
                      </h2>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        {checkedCount} / {totalCount} completed
                      </p>
                    </div>
                    {currentList.completed_at ? (
                      <span className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full text-sm">
                        Completed
                      </span>
                    ) : (
                      <button
                        onClick={completeList}
                        className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                      >
                        Mark Complete
                      </button>
                    )}
                  </div>
                </div>
                
                {/* Add Item Form */}
                <form onSubmit={handleAddItem} className="p-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newItemName}
                      onChange={(e) => setNewItemName(e.target.value)}
                      placeholder="Item name..."
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                    />
                    <input
                      type="number"
                      value={newItemQuantity}
                      onChange={(e) => setNewItemQuantity(e.target.value)}
                      placeholder="Qty"
                      className="w-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                    />
                    <button
                      type="submit"
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                    >
                      <Plus className="w-5 h-5" />
                    </button>
                  </div>
                </form>
                
                {/* Items List */}
                <div className="p-4">
                  {currentList.items.length === 0 ? (
                    <p className="text-center text-gray-500 dark:text-gray-400 py-8">
                      No items yet. Add your first item above!
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {currentList.items.map((item) => (
                        <ShoppingListItem
                          key={item.id}
                          item={item}
                          onToggle={() => toggleItem(item.id)}
                          onRemove={() => removeItem(item.id)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
                <p className="text-gray-500 dark:text-gray-400">
                  Select a list or create a new one to get started
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* New List Modal */}
      {showNewListModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold mb-4">Create New List</h3>
            <input
              type="text"
              value={newListTitle}
              onChange={(e) => setNewListTitle(e.target.value)}
              placeholder="List title..."
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white mb-4"
            />
            <div className="flex gap-2">
              <button
                onClick={() => setShowNewListModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateList}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

3. **Utworzyć `ShoppingListItem.tsx`:**
```typescript
import { CheckCircle2, Circle, Trash2 } from 'lucide-react';
import type { ShoppingListItem as ItemType } from '@/store/shoppingListStore';

interface Props {
  item: ItemType;
  onToggle: () => void;
  onRemove: () => void;
}

export function ShoppingListItem({ item, onToggle, onRemove }: Props) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
      <button onClick={onToggle} className="flex-shrink-0">
        {item.checked ? (
          <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
        ) : (
          <Circle className="w-5 h-5 text-gray-400" />
        )}
      </button>
      <div className="flex-1">
        <p className={`font-medium ${item.checked ? 'line-through text-gray-400' : 'text-gray-900 dark:text-white'}`}>
          {item.product_name}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {item.quantity} {item.unit}
        </p>
      </div>
      <button
        onClick={onRemove}
        className="flex-shrink-0 text-gray-400 hover:text-red-600 dark:hover:text-red-400"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  );
}
```

4. **Dodać API functions do `api.ts`:**
```typescript
export const fetchShoppingLists = async () => {
  const response = await api.get('/shopping-lists');
  return response.data;
};

export const createShoppingList = async (data: { title: string }) => {
  const response = await api.post('/shopping-lists', data);
  return response.data;
};

export const getShoppingList = async (id: number) => {
  const response = await api.get(`/shopping-lists/${id}`);
  return response.data;
};
```

**Backend wymagania:**
- Endpointy: `/api/shopping-lists`, `/api/shopping-lists/{id}`, `/api/shopping-lists/{id}/items`

**Szacowany czas:** 4-5 godzin

---

### 2.2 Global UI Components

**Cel:** Reużywalne komponenty Button, Input, Card, Modal

**Pliki do utworzenia:**
- `frontend/src/components/ui/Button.tsx`
- `frontend/src/components/ui/Input.tsx`
- `frontend/src/components/ui/Card.tsx`
- `frontend/src/components/ui/Modal.tsx`
- `frontend/src/components/ui/index.ts` (barrel export)

**Kroki:**

1. **Utworzyć `Button.tsx`:**
```typescript
import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  children,
  className = '',
  disabled,
  ...props
}: ButtonProps) {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 focus:ring-gray-500',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    ghost: 'bg-transparent text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 focus:ring-gray-500'
  };
  
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base'
  };
  
  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
      )}
      {leftIcon && !isLoading && <span className="mr-2">{leftIcon}</span>}
      {children}
      {rightIcon && <span className="ml-2">{rightIcon}</span>}
    </button>
  );
}
```

2. **Utworzyć `Input.tsx`:**
```typescript
import { InputHTMLAttributes, forwardRef } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = '', ...props }, ref) => {
    return (
      <div>
        {label && (
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white sm:text-sm ${
            error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''
          } ${className}`}
          {...props}
        />
        {error && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        {helperText && !error && (
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{helperText}</p>
        )}
      </div>
    );
  }
);
```

3. **Utworzyć `Card.tsx`:**
```typescript
import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export function Card({ children, className = '', padding = 'md' }: CardProps) {
  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  };
  
  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow ${paddingClasses[padding]} ${className}`}>
      {children}
    </div>
  );
}

interface CardHeaderProps {
  children: ReactNode;
  className?: string;
}

export function CardHeader({ children, className = '' }: CardHeaderProps) {
  return (
    <div className={`border-b border-gray-200 dark:border-gray-700 pb-4 mb-4 ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <h3 className={`text-lg font-semibold text-gray-900 dark:text-white ${className}`}>
      {children}
    </h3>
  );
}
```

4. **Utworzyć `Modal.tsx`:**
```typescript
import { ReactNode, useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);
  
  if (!isOpen) return null;
  
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl'
  };
  
  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />
        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">
          &#8203;
        </span>
        <div
          className={`inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:w-full ${sizeClasses[size]}`}
        >
          {title && (
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">{title}</h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          )}
          <div className="px-6 py-4">{children}</div>
        </div>
      </div>
    </div>
  );
}
```

5. **Utworzyć `index.ts` (barrel export):**
```typescript
export { Button } from './Button';
export { Input } from './Input';
export { Card, CardHeader, CardTitle } from './Card';
export { Modal } from './Modal';
export { LoadingSpinner } from './LoadingSpinner';
export { Skeleton } from './Skeleton';
export { LoadingCard } from './LoadingCard';
```

6. **Zaktualizować komponenty - użyć nowych UI components:**
   - Zastąpić wszystkie `<button>` przez `<Button>`
   - Zastąpić wszystkie `<input>` przez `<Input>`
   - Zastąpić divy z shadow przez `<Card>`
   - Zastąpić modale przez `<Modal>`

**Szacowany czas:** 4-5 godzin

---

### 2.3 Type Safety Improvements

**Cel:** Eliminacja wszystkich `any` i poprawa type safety

**Pliki do modyfikacji:**
- `frontend/src/pages/Products.tsx` (editingProduct: any)
- `frontend/src/store/chatStore.ts` (sprawdzić typy)
- `frontend/src/lib/api.ts` (dodać interfejsy dla wszystkich responses)

**Kroki:**

1. **Utworzyć `frontend/src/types/api.ts`:**
```typescript
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
```

2. **Zaktualizować `api.ts` - użyć typów:**
```typescript
import type {
  ReceiptListResponse,
  ReceiptDetailsResponse,
  ProductResponse,
  CategoryResponse,
  // ... etc
} from '../types/api';

export const fetchReceipts = async (params?: any): Promise<ReceiptListResponse> => {
  const response = await api.get('/receipts', { params });
  return response.data;
};

export const getReceipt = async (id: number): Promise<ReceiptDetailsResponse> => {
  const response = await api.get(`/receipts/${id}`);
  return response.data;
};
```

3. **Zaktualizować `Products.tsx`:**
```typescript
// Przed:
const [editingProduct, setEditingProduct] = useState<any>(null);

// Po:
import type { ProductResponse } from '@/types/api';
const [editingProduct, setEditingProduct] = useState<ProductResponse | null>(null);
```

**Szacowany czas:** 2-3 godziny

---

### 2.4 Toast Notifications

**Cel:** System powiadomień dla akcji użytkownika

**Kroki:**

1. **Zainstalować react-hot-toast:**
```bash
npm install react-hot-toast
```

2. **Zaktualizować `main.tsx`:**
```typescript
import { Toaster } from 'react-hot-toast';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#363636',
          color: '#fff',
        },
        success: {
          duration: 3000,
          iconTheme: {
            primary: '#10b981',
            secondary: '#fff',
          },
        },
        error: {
          duration: 4000,
          iconTheme: {
            primary: '#ef4444',
            secondary: '#fff',
          },
        },
      }}
    />
  </StrictMode>,
);
```

3. **Utworzyć helper `frontend/src/lib/toast.ts`:**
```typescript
import toast from 'react-hot-toast';

export const showSuccess = (message: string) => {
  toast.success(message);
};

export const showError = (message: string) => {
  toast.error(message);
};

export const showInfo = (message: string) => {
  toast(message, { icon: 'ℹ️' });
};

export const showLoading = (message: string) => {
  return toast.loading(message);
};

export const updateToast = (toastId: string, message: string, type: 'success' | 'error' | 'info') => {
  toast.dismiss(toastId);
  if (type === 'success') {
    toast.success(message);
  } else if (type === 'error') {
    toast.error(message);
  } else {
    toast(message);
  }
};
```

4. **Zaktualizować stores - dodać toast notifications:**
```typescript
// W receiptStore.ts
import { showSuccess, showError } from '@/lib/toast';

uploadReceipt: async (file) => {
  // ...
  try {
    const result = await uploadReceipt(file);
    showSuccess('Receipt uploaded successfully!');
    return result;
  } catch (error) {
    showError('Failed to upload receipt');
    throw error;
  }
}
```

**Szacowany czas:** 1-2 godziny

---

## 🎯 Faza 3: Priorytet Niski

### 3.1 Testing Setup

**Cel:** Dodać testy jednostkowe i integracyjne

**Kroki:**

1. **Zainstalować zależności:**
```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

2. **Utworzyć `vitest.config.ts`:**
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

3. **Utworzyć przykładowe testy dla komponentów**

**Szacowany czas:** 6-8 godzin (setup + przykładowe testy)

---

### 3.2 Storybook Setup

**Cel:** Dokumentacja komponentów UI

**Szacowany czas:** 3-4 godziny

---

### 3.3 Bundle Optimization

**Cel:** Zmniejszyć rozmiar bundle

**Kroki:**
- Code splitting dla routów
- Lazy loading komponentów
- Tree shaking optimization

**Szacowany czas:** 2-3 godziny

---

### 3.4 Accessibility Improvements

**Cel:** Zgodność z WCAG 2.1

**Kroki:**
- Dodać ARIA labels
- Keyboard navigation
- Screen reader support

**Szacowany czas:** 4-5 godzin

---

## ⏱️ Szacunki Czasowe

### Faza 1 (Priorytet Wysoki): **6-8 godzin**
- Environment Variables: 30 min
- Error Boundary: 1 godzina
- Chat Streaming: 3-4 godziny
- Unified Loading: 2 godziny

### Faza 2 (Priorytet Średni): **12-15 godzin**
- ShoppingList: 4-5 godzin
- Global Components: 4-5 godzin
- Type Safety: 2-3 godziny
- Toast Notifications: 1-2 godziny

### Faza 3 (Priorytet Niski): **15-20 godzin**
- Testing: 6-8 godzin
- Storybook: 3-4 godziny
- Bundle Optimization: 2-3 godziny
- Accessibility: 4-5 godzin

**Łączny czas:** **33-43 godziny**

---

## ✅ Checklist Implementacji

### Faza 1
- [x] Environment variables setup
- [x] Error Boundary component
- [x] Chat WebSocket streaming
- [x] Loading components (Spinner, Skeleton, Card)
- [x] Zastosowanie loading components w istniejących komponentach

### Faza 2
- [x] ShoppingList store
- [x] ShoppingList page
- [x] ShoppingListItem component
- [ ] Backend endpoints dla shopping lists (wymaga backend implementation)
- [x] Global UI components (Button, Input, Card, Modal)
- [ ] Zastosowanie UI components w całej aplikacji (opcjonalne - można stopniowo)
- [x] Type definitions (types/api.ts)
- [x] Eliminacja `any` z kodu
- [x] Toast notifications setup
- [x] Zastosowanie toast w stores

### Faza 3
- [x] Vitest setup
- [x] Przykładowe testy komponentów (Button, LoadingSpinner)
- [ ] Storybook setup (opcjonalne)
- [x] Bundle optimization (code splitting z lazy loading)
- [ ] Accessibility improvements (opcjonalne)

---

## 📝 Notatki Implementacyjne

### Kolejność implementacji (rekomendowana):
1. **Tydzień 1:** Faza 1 (wszystkie zadania)
2. **Tydzień 2:** Faza 2 (ShoppingList + Global Components)
3. **Tydzień 3:** Faza 2 (Type Safety + Toast)
4. **Tydzień 4:** Faza 3 (opcjonalnie)

### Zależności:
- Chat Streaming wymaga backend WebSocket endpoint
- ShoppingList wymaga backend API endpoints
- Global Components można implementować równolegle z innymi zadaniami

### Breaking Changes:
- Environment variables - wymaga aktualizacji `.env.local`
- Global Components - wymaga refaktoryzacji istniejących komponentów

---

**Ostatnia aktualizacja:** 2025-12-07

