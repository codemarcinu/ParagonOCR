interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  'aria-label'?: string;
}

export function LoadingSpinner({ size = 'md', className = '', 'aria-label': ariaLabel = 'Loading' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12'
  };
  
  return (
    <div 
      className={`flex items-center justify-center ${className}`}
      role="status"
      aria-live="polite"
      aria-label={ariaLabel}
    >
      <div 
        className={`animate-spin rounded-full border-b-2 border-blue-600 ${sizeClasses[size]}`}
        aria-hidden="true"
      />
      <span className="sr-only">{ariaLabel}</span>
    </div>
  );
}

