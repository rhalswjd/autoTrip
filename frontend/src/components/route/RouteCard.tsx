import { ArrowRight, ChevronDown, TriangleAlert } from 'lucide-react';
import type { Route } from '../../api/types';
import { routeEndpointDisplayName } from '../../utils/stationDisplay';
import { durationMinutes } from '../../utils/routePresentation';
import { routeBadges } from '../../utils/routeBadges';
import { TrainSilhouette } from '../railway/TrainSilhouette';
import '../../styles/railway.css';

export interface RouteCardProps {
  route: Route;
  requestedDepartureDate?: string;
  isSelected: boolean;
  onClick: (route: Route) => void;
}

const categoryLabels: Record<string, string> = {
  fastest: 'Fastest', fewest_transfers: 'Fewest transfers', 'fewest transfers': 'Fewest transfers', cheapest: 'Cheapest',
};

export function RouteCard({ route, requestedDepartureDate, isSelected, onClick }: RouteCardProps) {
  const services = [...new Set(route.passenger_legs?.filter(leg => leg.segment_type !== 'walk')
    .flatMap(leg => leg.railway_names) || [])];
  const waiting = durationMinutes(route.waiting_duration || '');
  const badges = routeBadges(route, requestedDepartureDate);
  return <button type="button" className={`rail-route-card ${isSelected ? 'is-selected' : ''}`}
    onClick={() => onClick(route)} aria-expanded={isSelected} aria-controls={`route-detail-${route.id}`}
    data-testid="route-family-card" data-route-id={route.id}>
    <span className="rail-route-main">
      <span className="rail-route-times">
        <span><strong>{route.departure_time || 'Time unconfirmed'}</strong><span>{routeEndpointDisplayName(route, 'departure')}</span></span>
        <ArrowRight size={20} aria-hidden="true" />
        <span><strong>{route.arrival_time || 'Time unconfirmed'}</strong><span>{routeEndpointDisplayName(route, 'arrival')}</span></span>
      </span>
      <span className="rail-ticket-line" aria-hidden="true"><i /><span /><TrainSilhouette size={20} /><span /><i /></span>
      <span className="rail-service-chips">{(services.length ? services : [route.railway_name]).map(service => <span key={service}>{service}</span>)}</span>
    </span>
    <span className="rail-route-metrics">
      <strong>{route.total_duration || 'Duration unconfirmed'}</strong>
      {(badges.departsTomorrow || badges.noTransfers) && <span className="rail-transfer-status">
        {badges.departsTomorrow && <span className="is-tomorrow">Departs tomorrow</span>}
        {badges.direct && <span>Direct</span>}
        {badges.noTransfers && <span>No transfers</span>}
      </span>}
      {!badges.noTransfers && <span>{route.transfer_count} transfer{route.transfer_count > 1 ? 's' : ''}</span>}
      <span className="rail-fare">{route.fare_status === 'unknown' || !route.total_fare ? 'Fare unavailable' : `Estimated fare ¥${route.total_fare.toLocaleString()}`}</span>
    </span>
    {Number.isFinite(waiting) && waiting >= 60 && <span className="rail-wait-warning"><TriangleAlert size={15} aria-hidden="true" />Long transfer wait · {route.waiting_duration} total</span>}
    {route.alternative_reason && <span className="rail-route-reason">{route.alternative_reason}</span>}
    <span className="rail-route-footer">
      <span className="rail-badges">{route.categories?.filter(category => categoryLabels[category.toLowerCase()]).map(category =>
        <span key={category}>{categoryLabels[category.toLowerCase()]}</span>)}<small>{route.search_date}</small></span>
      <span className="rail-route-action">{isSelected ? 'Configuring journey' : 'View route'}<ChevronDown size={16} aria-hidden="true" /></span>
    </span>
  </button>;
}
