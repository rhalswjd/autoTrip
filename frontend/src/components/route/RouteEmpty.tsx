import { MapPin } from 'lucide-react';
import '../../styles/railway.css';

export function RouteEmpty() {
  return <div className="rail-ui" role="status"><div className="rail-state rail-empty">
    <MapPin size={22} aria-hidden="true" /><div><strong>No routes found around your requested time.</strong>
      <p>Try a different departure time, date or station.</p></div>
  </div></div>;
}
