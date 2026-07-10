import { useEffect, useState, useCallback } from 'react';
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import './Toast.css';

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface ToastProps {
  id: string;
  variant: ToastVariant;
  title: string;
  description?: string;
  duration?: number;
  onClose: (id: string) => void;
}

const icons = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

export function Toast({
  id,
  variant,
  title,
  description,
  duration = 3000,
  onClose,
}: ToastProps) {
  const [isClosing, setIsClosing] = useState(false);

  const handleClose = useCallback(() => {
    setIsClosing(true);
    setTimeout(() => onClose(id), 150); // Match fade-out duration
  }, [id, onClose]);

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => handleClose(), duration);
      return () => clearTimeout(timer);
    }
  }, [duration, handleClose]);

  const Icon = icons[variant];

  return (
    <div
      className={`toast toast-${variant} ${isClosing ? 'toast-closing' : ''}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <Icon className="toast-icon" />
      <div className="toast-content">
        <span className="toast-title">{title}</span>
        {description && <span className="toast-description">{description}</span>}
      </div>
      <button
        type="button"
        className="toast-close"
        onClick={handleClose}
        aria-label="Close notification"
      >
        <X size={16} />
      </button>
    </div>
  );
}
