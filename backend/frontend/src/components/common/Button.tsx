import { forwardRef, type ReactNode } from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';

type MotionButtonProps = Omit<HTMLMotionProps<'button'>, 'onDrag'>;

interface ButtonProps extends MotionButtonProps {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const variants = {
  primary: 'bg-primary hover:bg-primary-hover text-white shadow-md hover:shadow-glow',
  secondary: 'bg-surface hover:bg-surface-hover text-text-primary border border-border hover:border-border-light',
  ghost: 'bg-transparent hover:bg-surface text-text-secondary hover:text-text-primary',
  danger: 'bg-danger/10 hover:bg-danger/20 text-danger border border-danger/30',
};

const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const baseClasses =
      'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-200 ease-smooth focus:outline-none focus:ring-2 focus:ring-primary/50 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100';

    const classes = `${baseClasses} ${variants[variant]} ${sizes[size]} ${className}`;

    return (
      <motion.button
        ref={ref}
        className={classes}
        disabled={disabled || isLoading}
        whileHover={{ y: -1 }}
        whileTap={{ scale: 0.98 }}
        {...props}
      >
        {isLoading && (
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {!isLoading && leftIcon}
        {children}
        {!isLoading && rightIcon}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';
