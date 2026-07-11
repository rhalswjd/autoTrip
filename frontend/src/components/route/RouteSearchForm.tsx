import { useEffect } from 'react';
import type { StationSearchResult } from '../../api/types';
import { RouteStationField } from './RouteStationField';
import { SwapButton } from './SwapButton';
import { Button } from '../ui';
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

export function RouteSearchForm({
  departure,
  arrival,
  onDepartureChange,
  onArrivalChange,
  onRoutesLoaded,
}: RouteSearchFormProps) {
  const { error: toastError } = useToast();

  const isReady = !!departure && !!arrival;

  const { data, refetch, isError, error, isFetching } = useRouteSearch(
    isReady
      ? {
          departure_station: departure.japanese_name,
          arrival_station: arrival.japanese_name,
        }
      : null
  );

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
      refetch();
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
