import { forwardRef } from 'react';
import type { HTMLAttributes } from 'react';
import './Divider.css';

export interface DividerProps extends HTMLAttributes<HTMLHRElement> {
  orientation?: 'horizontal' | 'vertical';
}

export const Divider = forwardRef<HTMLHRElement, DividerProps>(
  ({ className = '', orientation = 'horizontal', ...props }, ref) => {
    return (
      <hr
        ref={ref}
        className={`divider divider-${orientation} ${className}`}
        role="separator"
        aria-orientation={orientation}
        {...props}
      />
    );
  }
);

Divider.displayName = 'Divider';
