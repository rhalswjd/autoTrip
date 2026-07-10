import { forwardRef } from 'react';
import type { InputHTMLAttributes, ReactNode } from 'react';
import './Input.css';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'prefix'> {
  label?: string;
  helperText?: string;
  error?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', label, helperText, error, leftIcon, rightIcon, id, ...props }, ref) => {
    return (
      <div className={`input-wrapper ${className}`}>
        {label && (
          <label htmlFor={id} className="input-label">
            {label}
          </label>
        )}
        <div
          className={`input-container ${leftIcon ? 'input-has-left' : ''} ${
            rightIcon ? 'input-has-right' : ''
          } ${error ? 'input-error' : ''}`}
        >
          {leftIcon && <div className="input-icon-left">{leftIcon}</div>}
          <input ref={ref} id={id} className="input-field" {...props} />
          {rightIcon && <div className="input-icon-right">{rightIcon}</div>}
        </div>
        {helperText && (
          <span className={`input-helper ${error ? 'error' : ''}`}>
            {helperText}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
