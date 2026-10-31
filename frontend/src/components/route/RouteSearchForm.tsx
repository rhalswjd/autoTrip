import { useEffect, useState } from 'react';
import type { StationSearchResult, SearchParams } from '../../api/types';
import { RouteStationField } from './RouteStationField';
import { SwapButton } from './SwapButton';
import { Button, Input } from '../ui';
import { useToast } from '../../hooks/useToast';
import { useRouteSearch } from '../../hooks/useRouteSearch';
import type { Route } from '../../api/types';
import './Route.css';

export interface RouteSearchFormProps {
  departure: StationSearchResult | null;
  arrival: StationSearchResult | null;
  onDepartureChange: (station: StationSearchResult | null) => void;
  onArrivalChange: (station: StationSearchResult | null) => void;
  onRoutesLoaded?: (routes: Route[] | undefined, isLoading: boolean) => void;
}

function currentJstDateTime(): { date: string; time: string } {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date());
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? '';
  return {
    date: `${value('year')}-${value('month')}-${value('day')}`,
    time: `${value('hour')}:${value('minute')}`,
  };
}

export function RouteSearchForm({
  departure,
  arrival,
  onDepartureChange,
  onArrivalChange,
  onRoutesLoaded,
}: RouteSearchFormProps) {
  const { error: toastError } = useToast();
  const [initialDateTime] = useState(currentJstDateTime);
  const [departureDate, setDepartureDate] = useState(initialDateTime.date);
  const [departureTime, setDepartureTime] = useState(initialDateTime.time);
  const [submittedParams, setSubmittedParams] = useState<SearchParams | null>(null);

  const isReady = !!departure && !!arrival && !!departureDate && !!departureTime;

  const { data, refetch, isError, error, isFetching } = useRouteSearch(submittedParams);

  useEffect(() => {
    if (isError && error) {
      toastError('Route Search Failed', error.message || 'Unable to find routes.');
    }
  }, [isError, error, toastError]);

  useEffect(() => {
    onRoutesLoaded?.(data, isFetching);
  }, [data, isFetching, onRoutesLoaded]);

  const handleSwap = () => {
    const temp = departure;
    onDepartureChange(arrival);
    onArrivalChange(temp);
  };

  const handleSearch = () => {
    if (isReady) {
      const params = {
        departure_station: departure.japanese_name,
        arrival_station: arrival.japanese_name,
        departure_date: departureDate,
        departure_time: departureTime,
      };
      if (JSON.stringify(params) === JSON.stringify(submittedParams)) refetch();
      else setSubmittedParams(params);
    }
  };

  return (
    <div className="route-form-container">
      <h2 className="route-form-title">Route Search</h2>

      <div className="route-form-section">
        <div className="route-fields-wrapper">
          <RouteStationField
            label="Departure"
            station={departure}
            onClear={() => onDepartureChange(null)}
          />
          <SwapButton
            onClick={handleSwap}
            disabled={!departure && !arrival}
          />
          <RouteStationField
            label="Arrival"
            station={arrival}
            onClear={() => onArrivalChange(null)}
          />
        </div>
        <div className="route-datetime-fields">
          <Input
            id="route-departure-date"
            label="Travel date"
            type="date"
            value={departureDate}
            onChange={(event) => setDepartureDate(event.target.value)}
            required
          />
          <Input
            id="route-departure-time"
            label="Departure time"
            type="time"
            value={departureTime}
            onChange={(event) => setDepartureTime(event.target.value)}
            required
          />
        </div>
      </div>

      <div className="route-actions">
        <Button
          variant="primary"
          disabled={!isReady || isFetching}
          onClick={handleSearch}
          loading={isFetching}
          aria-expanded={isReady ? 'true' : 'false'}
          aria-controls="route-results"
        >
          {isFetching ? 'Searching...' : 'Search Routes'}
        </Button>
      </div>
    </div>
  );
}
