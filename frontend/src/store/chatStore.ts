import { create } from 'zustand';
import apiClient from '@/lib/api';

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

    fetchConversations: () => Promise<void>;
    selectConversation: (id: string) => Promise<void>;
    createConversation: () => Promise<string>;
    sendMessage: (content: string) => Promise<void>;
    clearError: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
    messages: [],
    conversations: [],
    currentConversationId: null,
    loading: false,
    streaming: false,
    error: null,

    fetchConversations: async () => {
        set({ loading: true, error: null });
        try {
            const response = await apiClient.get('/chat/conversations');
            set({ conversations: response.data, loading: false });
        } catch (error) {
            set({ loading: false, error: 'Failed to fetch conversations' });
        }
    },

    selectConversation: async (id) => {
        set({ currentConversationId: id, loading: true, error: null });
        try {
            const response = await apiClient.get(`/chat/conversations/${id}/messages`);
            set({ messages: response.data, loading: false });
        } catch (error) {
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
            set({ loading: false, error: 'Failed to create conversation' });
            return '';
        }
    },

    sendMessage: async (content) => {
        const { currentConversationId, messages } = get();
        if (!currentConversationId) return;

        // Add user message immediately
        const userMsg: Message = {
            id: Date.now().toString(), // temp id
            role: 'user',
            content,
            timestamp: new Date().toISOString()
        };

        set({ messages: [...messages, userMsg], streaming: true });

        try {
            // Here we would ideally use fetch for streaming or WebSocket
            // For MVP, assuming non-streaming or simple streaming integration
            // If streaming is required, we need a different approach than standard axios.
            // Let's use fetch for streaming support.

            // This is a placeholder for actual streaming implementation
            // which might involve handling chunks.

            await apiClient.post(`/chat/conversations/${currentConversationId}/messages`, { content });

            // Refresh messages after response (if not properly streaming)
            // Or handle stream chunks here. 
            // For simplicity in this step, let's assume we re-fetch or backend returns full response.
            const response = await apiClient.get(`/chat/conversations/${currentConversationId}/messages`);
            set({ messages: response.data, streaming: false });

        } catch (error) {
            set({ streaming: false, error: 'Failed to send message' });
        }
    },

    clearError: () => set({ error: null })
}));
