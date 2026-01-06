import { useEffect, useState, useRef, type KeyboardEvent } from 'react';
import { Link } from 'react-router-dom';
import * as ReactWindow from 'react-window';
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const VariableSizeList = (ReactWindow as any).VariableSizeList || (ReactWindow as any).default?.VariableSizeList;
import { Home } from 'lucide-react';
import { useChatStore } from '@/store/chatStore';
import { Button } from '@/components/ui';

export function Chat() {
    const {
        messages,
        conversations,
        currentConversationId,
        streaming,
        fetchConversations,
        selectConversation,
        createConversation,
        sendMessage
    } = useChatStore();

    const [input, setInput] = useState('');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const listRef = useRef<any>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        fetchConversations();
    }, [fetchConversations]);

    useEffect(() => {
        if (conversations.length > 0 && !currentConversationId) {
            selectConversation(conversations[0].id);
        }
    }, [conversations, currentConversationId, selectConversation]);

    useEffect(() => {
        // Scroll to bottom when messages change
        if (listRef.current && messages.length > 0) {
            listRef.current.scrollToItem(messages.length - 1, 'end');
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || streaming) return;

        const content = input;
        setInput('');

        // Reset height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }

        await sendMessage(content);
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            handleSend();
        }
    };

    const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value);
        // Auto-resize
        e.target.style.height = 'auto';
        e.target.style.height = `${e.target.scrollHeight} px`;
    };

    const getItemSize = (index: number) => {
        // Approximate height calculation or dynamic measurement
        // For simplicity, a base height + content length factor
        const msg = messages[index];
        const baseHeight = 60;
        const contentLength = msg.content.length;
        return baseHeight + Math.ceil(contentLength / 80) * 20;
    };

    const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
        const msg = messages[index];
        const isUser = msg.role === 'user';

        return (
            <div style={style} className={`px-4 py-2 flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                <div
                    className={`max-w-[80%] rounded-lg p-3 ${isUser
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-bl-none shadow-sm'
                        }`}
                >
                    <p className={`text-sm whitespace-pre-wrap ${isUser ? 'text-white' : 'text-gray-900 dark:text-gray-100'}`}>
                        {msg.content}
                    </p>
                    <span className={`text-xs mt-1 block ${isUser ? 'text-blue-100' : 'text-gray-500'}`}>
                        {new Date(msg.timestamp).toLocaleTimeString('pl-PL')}
                    </span>
                </div>
            </div>
        );
    };

    return (
        <div className="flex h-[calc(100vh-200px)] bg-gray-50 dark:bg-gray-900">
            {/* Sidebar */}
            <div className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                    <Button
                        onClick={createConversation}
                        className="w-full"
                    >
                        + Nowa Rozmowa
                    </Button>
                </div>
                <div className="flex-1 overflow-y-auto">
                    {conversations.map((conv) => (
                        <button
                            key={conv.id}
                            onClick={() => selectConversation(conv.id)}
                            className={`w-full text-left px-4 py-3 border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${currentConversationId === conv.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                                }`}
                            aria-label={`${conv.title || 'Nowa Rozmowa'} konwersacja`}
                            aria-current={currentConversationId === conv.id ? 'true' : undefined}
                        >
                            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                {conv.title || 'Nowa Rozmowa'}
                            </p>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                {new Date(conv.created_at).toLocaleDateString('pl-PL')}
                            </p>
                        </button>
                    ))}
                </div>
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col">
                {/* Header */}
                <div className="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-6">
                    <div className="flex items-center space-x-4">
                        <Link
                            to="/"
                            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                            title="Powrót do strony głównej"
                        >
                            <Home className="h-5 w-5" />
                        </Link>
                        <h2 className="text-lg font-medium text-gray-900 dark:text-white">
                            {conversations.find(c => c.id === currentConversationId)?.title || 'Czat'}
                        </h2>
                    </div>
                    <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                        </svg>
                    </button>
                </div>

                {/* Messages List */}
                <div className="flex-1 relative" role="log" aria-live="polite" aria-label="Wiadomości czatu">
                    {messages.length > 0 ? (
                        <VariableSizeList
                            ref={listRef}
                            height={600} // This should be dynamic based on container
                            width="100%"
                            itemCount={messages.length}
                            itemSize={getItemSize}
                            className="no-scrollbar"
                            style={{ overflowX: 'hidden' }}
                        >
                            {Row}
                        </VariableSizeList>
                    ) : (
                        <div className="h-full flex items-center justify-center text-gray-400">
                            <div className="text-center">
                                <p className="text-lg mb-2">Witaj w ParagonChat</p>
                                <p className="text-sm">Rozpocznij rozmowę, aby analizować swoje paragony.</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div className="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
                    <div className="max-w-4xl mx-auto relative">
                        <textarea
                            ref={textareaRef}
                            value={input}
                            onChange={handleInput}
                            onKeyDown={handleKeyDown}
                            placeholder="Wpisz wiadomość... (Ctrl+Enter aby wysłać)"
                            className="w-full rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:ring-blue-500 focus:border-blue-500 pr-12 resize-none min-h-[44px] max-h-[120px] py-2"
                            rows={1}
                            aria-label="Pole wiadomości"
                            aria-describedby="chat-input-help"
                        />
                        <span id="chat-input-help" className="sr-only">
                            Wpisz wiadomość i naciśnij Ctrl+Enter aby wysłać
                        </span>
                        <Button
                            onClick={handleSend}
                            disabled={!input.trim() || streaming}
                            isLoading={streaming}
                            variant="ghost"
                            size="sm"
                            className="absolute right-2 bottom-2"
                            aria-label="Wyślij wiadomość"
                            title="Wyślij wiadomość (Ctrl+Enter)"
                        >
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
