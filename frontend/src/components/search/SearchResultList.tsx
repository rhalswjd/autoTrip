import { useEffect, useRef, useState } from 'react';
import type { StationSearchResult } from '../../api/types';
import { SearchResultItem } from './SearchResultItem';
import { SearchEmptyState } from './SearchEmptyState';
import { SearchNoResult } from './SearchNoResult';
import { SearchLoading } from './SearchLoading';
import { SearchError } from './SearchError';
import './Search.css';

export interface SearchResultListProps {
  query: string;
  results: StationSearchResult[] | undefined;
  isLoading: boolean;
  error: Error | null;
  selectedStationId: string | null;
  onSelect: (station: StationSearchResult) => void;
  onRetry: () => void;
  onEscape: () => void;
}

export function SearchResultList({
  query,
  results,
  isLoading,
  error,
  selectedStationId,
  onSelect,
  onRetry,
  onEscape,
}: SearchResultListProps) {
  const [activeIndex, setActiveIndex] = useState(-1);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setActiveIndex(-1);
  }, [results, query]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!results || results.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((prev) => (prev < results.length - 1 ? prev + 1 : prev));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((prev) => (prev > 0 ? prev - 1 : prev));
      } else if (e.key === 'Enter' && activeIndex >= 0) {
        e.preventDefault();
        onSelect(results[activeIndex]);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onEscape();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [results, activeIndex, onSelect, onEscape]);

  useEffect(() => {
    if (activeIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('.search-result-item');
      const activeElement = items[activeIndex] as HTMLElement;
      if (activeElement) {
        activeElement.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [activeIndex]);

  if (query.length < 2) {
    return <SearchEmptyState />;
  }

  if (isLoading) {
    return <SearchLoading />;
  }

  if (error) {
    return <SearchError error={error} onRetry={onRetry} />;
  }

  if (results && results.length === 0) {
    return <SearchNoResult query={query} />;
  }

  return (
    <div className="search-list-container" role="listbox" ref={listRef}>
      {results?.map((station, index) => (
        <SearchResultItem
          key={station.id}
          station={station}
          isSelected={index === activeIndex || selectedStationId === station.id}
          onClick={onSelect}
        />
      ))}
    </div>
  );
}
