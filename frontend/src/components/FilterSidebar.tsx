
import { X } from 'lucide-react';
import { Button } from './ui';

interface FilterSidebarProps {
    isOpen: boolean;
    onClose: () => void;
    children: React.ReactNode;
    headerTitle?: string;
    onReset?: () => void;
    onApply?: () => void;
}

export function FilterSidebar({
    isOpen,
    onClose,
    children,
    headerTitle = 'Filtrowanie',
    onReset,
    onApply
}: FilterSidebarProps) {
    return (
        <>
            {/* Overlay */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
                    onClick={onClose}
                />
            )}

            {/* Sidebar - Right Side */}
            <div
                className={`fixed inset-y-0 right-0 z-50 w-full md:w-96 bg-white dark:bg-gray-900 shadow-xl transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : 'translate-x-full'
                    }`}
            >
                <div className="flex flex-col h-full">
                    {/* Header */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                            {headerTitle}
                        </h2>
                        <button
                            onClick={onClose}
                            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                        >
                            <X className="w-6 h-6" />
                        </button>
                    </div>

                    {/* Body */}
                    <div className="flex-1 overflow-y-auto px-6 py-4">
                        {children}
                    </div>

                    {/* Footer */}
                    <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex justify-between space-x-4">
                        {onReset && (
                            <Button
                                variant="ghost"
                                onClick={onReset}
                                className="flex-1"
                            >
                                Wyczyść
                            </Button>
                        )}
                        <Button
                            onClick={onApply || onClose}
                            className="flex-1"
                        >
                            Pokaż Wyniki
                        </Button>
                    </div>
                </div>
            </div>
        </>
    );
}
