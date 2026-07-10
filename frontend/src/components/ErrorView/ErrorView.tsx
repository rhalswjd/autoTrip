import { Button } from '../Button/Button';
import './ErrorView.css';

interface ErrorViewProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorView({ title = 'Something went wrong', message, onRetry }: ErrorViewProps) {
  return (
    <div className="error-view">
      <div className="error-view-icon">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="2" />
          <line x1="16" y1="10" x2="16" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          <circle cx="16" cy="22" r="1.5" fill="currentColor" />
        </svg>
      </div>
      <h3 className="error-view-title">{title}</h3>
      <p className="error-view-message">{message}</p>
      {onRetry && <Button variant="secondary" onClick={onRetry}>Try Again</Button>}
    </div>
  );
}
