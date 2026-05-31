import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      fullWidth = true,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const baseClasses =
      'flex-1 min-w-0 bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground text-sm';
    const wrapperClasses = `flex items-center gap-3 px-4 py-2.5 bg-background border border-input rounded-lg transition-all duration-200 ease-smooth focus-within:ring-2 focus-within:ring-primary/30 focus-within:border-primary ${
      error ? 'border-destructive focus-within:border-destructive focus-within:ring-destructive/30' : 'border-border hover:border-border/80'
    } ${disabled ? 'opacity-50 cursor-not-allowed bg-muted' : ''} ${
      fullWidth ? 'w-full' : ''
    } ${className}`;

    return (
      <div className={fullWidth ? 'w-full' : 'inline-block'}>
        {label && (
          <label className="block text-sm font-medium text-foreground mb-1.5">
            {label}
          </label>
        )}
        <div className={wrapperClasses}>
          {leftIcon && (
            <span className="text-muted-foreground flex-shrink-0">{leftIcon}</span>
          )}
          <input ref={ref} className={baseClasses} disabled={disabled} {...props} />
          {rightIcon && (
            <span className="text-muted-foreground flex-shrink-0">{rightIcon}</span>
          )}
        </div>
        {(error || helperText) && (
          <p
            className={`mt-1.5 text-xs ${
              error ? 'text-destructive' : 'text-muted-foreground'
            }`}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
