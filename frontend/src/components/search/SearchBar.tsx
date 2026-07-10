import { useRef, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import { Input, IconButton } from '../ui';
import './Search.css';

export interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onEnter?: () => void;
  placeholder?: string;
  autoFocus?: boolean;
}

export function SearchBar({
  value,
  onChange,
  onEnter,
  placeholder = 'Search stations...',
  autoFocus = false,
}: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && onEnter) {
      onEnter();
    }
  };

  const clearInput = () => {
    onChange('');
    inputRef.current?.focus();
  };

  return (
    <div className="search-header">
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        leftIcon={<Search size={16} />}
        rightIcon={
          value ? (
            <IconButton
              size="sm"
              icon={<X />}
              onClick={clearInput}
              aria-label="Clear search"
            />
          ) : null
        }
        aria-label="Search stations"
      />
    </div>
  );
}
