import { AlertCircle } from 'lucide-react';
import { Button } from '../ui';
import './Search.css';

export interface SearchErrorProps {
  error: Error;
  onRetry: () => void;
}

export function SearchError({ error, onRetry }: SearchErrorProps) {
  return (
    <div className="search-state-wrapper">
      <AlertCircle className="search-state-icon" style={{ color: 'var(--color-error)' }} />
      <div>
        <div className="search-state-title">Search Failed</div>
        <div className="search-state-desc">{error.message || 'An error occurred while searching.'}</div>
      </div>
      <Button variant="secondary" onClick={onRetry}>
        Try Again
      </Button>
    </div>
  );
}
