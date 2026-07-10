import type { StationSearchResult } from '../../api/types';
import { Card, Badge } from '../ui';
import './Search.css';

export interface SearchResultItemProps {
  station: StationSearchResult;
  isSelected?: boolean;
  onClick: (station: StationSearchResult) => void;
}

export function SearchResultItem({ station, isSelected = false, onClick }: SearchResultItemProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick(station);
    }
  };

  return (
    <Card
      className="search-result-item"
      hoverable
      clickable
      selected={isSelected}
      onClick={() => onClick(station)}
      onKeyDown={handleKeyDown}
      aria-selected={isSelected}
      aria-current={isSelected ? 'true' : 'false'}
    >
      <div className="search-result-item-header">
        <span className="search-result-name">{station.english_name}</span>
        {station.has_midori_office && (
          <Badge variant="success">Midori Office</Badge>
        )}
      </div>
      <span className="search-result-jp">{station.japanese_name}</span>
    </Card>
  );
}
