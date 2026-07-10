import { Badge } from '../ui';
import './RouteTimeline.css';

export interface TransferBadgeProps {
  stationName: string;
}

export function TransferBadge({ stationName }: TransferBadgeProps) {
  return (
    <div className="transfer-badge-wrapper">
      <Badge variant="warning">Transfer</Badge>
      <span className="route-leg-detail">{stationName}</span>
    </div>
  );
}
