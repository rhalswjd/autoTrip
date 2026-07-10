import { createContext } from 'react';
import type { ToastProps } from './Toast';

export type ToastInput = Omit<ToastProps, 'id' | 'onClose'>;

export interface ToastContextValue {
  toast: (input: ToastInput) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  warning: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);
