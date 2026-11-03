import { useId, useRef, useState, type RefObject } from 'react';
import type { StationSearchResult } from '../../api/types';
import { useStationSearch } from '../../hooks/useStationSearch';
import { stationDisplayName } from '../../utils/stationDisplay';

interface Props {
  label: string;
  station: StationSearchResult | null;
  inputRef: RefObject<HTMLInputElement | null>;
  onChange: (station: StationSearchResult | null) => void;
  onSelected: () => void;
}

/** Keep canonical station identity separate from the editable display text. */
export function StationCombobox({ label, station, inputRef, onChange, onSelected }: Props) {
  const id = useId();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listRef = useRef<HTMLUListElement>(null);
  const { data = [], isLoading, error, refetch } = useStationSearch(open && !station ? query : '');
  const expanded = open && !station && query.length >= 2;
  const select = (value: StationSearchResult) => {
    onChange(value); setQuery(''); setOpen(false); setActive(-1); onSelected();
  };
  return <div className="home-station" onBlur={event => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
  }}>
    <label htmlFor={id}>{label}</label>
    <div className="home-station-input">
      <input id={id} ref={inputRef} role="combobox" aria-autocomplete="list" aria-expanded={expanded}
        aria-controls={expanded ? `${id}-options` : undefined} aria-describedby={`${id}-hint`}
        aria-activedescendant={expanded && active >= 0 && data[active] ? `${id}-option-${active}` : undefined}
        title={station ? stationDisplayName(station) : undefined}
        autoComplete="off" placeholder={label === 'FROM' ? 'Departure station' : 'Arrival station'}
        value={station ? stationDisplayName(station) : query}
        onFocus={() => setOpen(true)}
        onChange={event => { onChange(null); setQuery(event.target.value); setOpen(true); setActive(-1); }}
        onKeyDown={event => {
          if (event.key === 'Escape') { setOpen(false); setActive(-1); }
          if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && !station) {
            event.preventDefault(); setOpen(true);
            const next = event.key === 'ArrowDown' ? Math.min(active + 1, data.length - 1) : Math.max(active - 1, 0);
            setActive(next); listRef.current?.children[next]?.scrollIntoView({ block: 'nearest' });
          }
          if (event.key === 'Enter' && expanded && data[active]) { event.preventDefault(); select(data[active]); }
        }} />
      {(station || query) && <button type="button" className="home-clear" aria-label={`Clear ${label}`} onClick={() => {
        onChange(null); setQuery(''); setActive(-1); setOpen(true); inputRef.current?.focus();
      }}>×</button>}
    </div>
    <span id={`${id}-hint`} className="home-station-hint">{station
      ? [stationDisplayName(station).length > 28 ? stationDisplayName(station) : '', station.japanese_name, station.region || station.prefecture, station.has_midori_office ? 'Midori Office' : ''].filter(Boolean).join(' · ')
      : 'Search by station name'}</span>
    {expanded && <div className="home-suggestions">
      <div role="status" className="home-suggestion-status">{query.length < 2 ? 'Type at least 2 characters' : isLoading ? 'Finding stations…' : error ? 'Stations could not be loaded.' : `${data.length} stations found`}</div>
      {error && <button type="button" className="home-retry" onClick={() => refetch()}>Retry station search</button>}
      <ul id={`${id}-options`} role="listbox" aria-label={`${label} stations`} ref={listRef}>
        {query.length >= 2 && !error && data.map((item, index) => <li key={item.id} id={`${id}-option-${index}`}
          role="option" aria-selected={index === active} onPointerDown={event => event.preventDefault()} onClick={() => select(item)}>
          <strong>{stationDisplayName(item)}</strong>
          <span>{[item.japanese_name, item.region || item.prefecture].filter(Boolean).join(' · ')}</span>
          {item.has_midori_office && <small>Midori Office</small>}
        </li>)}
      </ul>
    </div>}
  </div>;
}
