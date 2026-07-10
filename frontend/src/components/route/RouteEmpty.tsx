import { MapPin } from 'lucide-react';
import './RouteTimeline.css';

export function RouteEmpty() {
  return (
    <div className="route-empty-state">
      <MapPin className="route-empty-icon" />
      <div>
        <div className="route-empty-title">No Routes Found</div>
        <div className="route-empty-desc">
          Try searching with different stations.
        </div>
      </div>
    </div>
  );
}
