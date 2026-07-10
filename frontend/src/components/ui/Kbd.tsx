import { forwardRef } from 'react';
import type { HTMLAttributes } from 'react';
import './Kbd.css';

export interface KbdProps extends HTMLAttributes<HTMLElement> {}

export const Kbd = forwardRef<HTMLElement, KbdProps>(
  ({ className = '', children, ...props }, ref) => {
    return (
      <kbd ref={ref} className={`kbd ${className}`} {...props}>
        {children}
      </kbd>
    );
  }
);

Kbd.displayName = 'Kbd';
