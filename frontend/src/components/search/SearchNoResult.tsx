import { SearchX } from 'lucide-react';
import './Search.css';

export interface SearchNoResultProps {
  query: string;
}

export function SearchNoResult({ query }: SearchNoResultProps) {
  return (
    <div className="search-state-wrapper">
      <SearchX className="search-state-icon" />
      <div>
        <div className="search-state-title">No Results Found</div>
        <div className="search-state-desc">
          No stations match "{query}". Try a different name.
        </div>
      </div>
    </div>
  );
}
