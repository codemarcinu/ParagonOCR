import { create } from 'zustand';
import apiClient from '@/lib/api';
import { WS_BASE_URL } from '@/lib/api';

export interface Message {
    id: string; // uuid
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
}

export interface Conversation {
    id: string; // uuid
    title: string;
    created_at: string;
}

interface ChatStore {
    messages: Message[];
    conversations: Conversation[];
    currentConversationId: string | null;
    loading: boolean;
    streaming: boolean;
    error: string | null;
    wsConnection: WebSocket | null;
    currentMessageBuffer: string;

    fetchConversations: () => Promise<void>;
    selectConversation: (id: string) => Promise<void>;
    createConversation: () => Promise<string>;
    sendMessage: (content: string) => Promise<void>;
    connectWebSocket: (conversationId: string) => void;
    disconnectWebSocket: () => void;
    sendMessageStreaming: (content: string) => Promise<void>;
    clearError: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
    messages: [],
    conversations: [],
    currentConversationId: null,
    loading: false,
    streaming: false,
    error: null,
    wsConnection: null,
    currentMessageBuffer: '',

    fetchConversations: async () => {
        set({ loading: true, error: null });
        try {
            const response = await apiClient.get('/chat/conversations');
            set({ conversations: response.data, loading: false });
        } catch (error) {
            console.error('Failed to fetch conversations', error);
            set({ loading: false, error: 'Failed to fetch conversations' });
        }
    },

    selectConversation: async (id) => {
        get().disconnectWebSocket();
        set({ currentConversationId: id, loading: true, error: null });
        try {
            const response = await apiClient.get(`/chat/conversations/${id}/messages`);
            set({ messages: response.data, loading: false });
            get().connectWebSocket(id);
        } catch (error) {
            console.error('Failed to fetch messages', error);
            set({ loading: false, error: 'Failed to fetch messages' });
        }
    },

    createConversation: async () => {
        set({ loading: true });
        try {
            const response = await apiClient.post('/chat/conversations', { title: 'New Chat' });
            const newConv = response.data;
            set((state) => ({
                conversations: [newConv, ...state.conversations],
                currentConversationId: newConv.id,
                messages: [],
                loading: false
            }));
            return newConv.id;
        } catch (error) {
            console.error('Failed to create conversation', error);
            set({ loading: false, error: 'Failed to create conversation' });
            return '';
        }
    },

    connectWebSocket: (conversationId: string) => {
        const { wsConnection } = get();
        if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
            return; // Already connected
        }

        if (wsConnection) {
            wsConnection.close();
        }

        const ws = new WebSocket(`${WS_BASE_URL}/api/chat/conversations/${conversationId}/stream`);

        ws.onopen = () => {
            console.log('Chat WebSocket connected');
            set({ wsConnection: ws });
        };

        ws.onmessage = (event) => {
            try {
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
                    set({ streaming: false, error: data.message || 'An error occurred' });
                }
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
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
            await new Promise<void>((resolve) => {
                const checkConnection = () => {
                    const currentWs = get().wsConnection;
                    if (currentWs && currentWs.readyState === WebSocket.OPEN) {
                        resolve();
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

    sendMessage: async (content: string) => {
        await get().sendMessageStreaming(content);
    },

    clearError: () => set({ error: null })
}));
