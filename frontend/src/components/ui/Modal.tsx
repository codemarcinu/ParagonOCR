import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const titleId = title ? `modal-title-${Math.random().toString(36).substr(2, 9)}` : undefined;
  
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      // Focus trap: focus first focusable element or close button
      setTimeout(() => {
        const firstFocusable = modalRef.current?.querySelector<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (firstFocusable) {
          firstFocusable.focus();
        } else if (closeButtonRef.current) {
          closeButtonRef.current.focus();
        }
      }, 0);
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);
  
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => {
        document.removeEventListener('keydown', handleEscape);
      };
    }
  }, [isOpen, onClose]);
  
  if (!isOpen) return null;
  
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl'
  };
  
  return (
    <div 
      className="fixed inset-0 z-50 overflow-y-auto"
      aria-modal="true"
      role="dialog"
      aria-labelledby={titleId}
    >
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">
          &#8203;
        </span>
        <div
          ref={modalRef}
          className={`inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:w-full ${sizeClasses[size]}`}
          onClick={(e) => e.stopPropagation()}
        >
          {title && (
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h3 id={titleId} className="text-lg font-medium text-gray-900 dark:text-white">
                {title}
              </h3>
              <button
                ref={closeButtonRef}
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" aria-hidden="true" />
              </button>
            </div>
          )}
          <div className="px-6 py-4">{children}</div>
        </div>
      </div>
    </div>
  );
}

