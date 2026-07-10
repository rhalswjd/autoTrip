import { Search } from 'lucide-react';
import './Search.css';

export function SearchEmptyState() {
  return (
    <div className="search-state-wrapper">
      <Search className="search-state-icon" />
      <div>
        <div className="search-state-title">Search Stations</div>
        <div className="search-state-desc">Type at least 2 characters to search.</div>
      </div>
    </div>
  );
}
