import { Skeleton } from '../ui';
import '../../styles/railway.css';

export function RouteLoading() {
  return <div className="rail-loading rail-ui" role="status" aria-label="Searching routes" aria-busy="true">
    <span className="rail-eyebrow">FINDING YOUR ROUTE</span>
    {Array.from({ length: 3 }, (_, index) => <div key={index} className="rail-loading-row" aria-hidden="true">
      <div className="rail-loading-times"><Skeleton style={{ width: "28%", height: 30 }} /><Skeleton style={{ width: "28%", height: 30 }} /></div>
      <Skeleton style={{ width: "75%", height: 12 }} /><Skeleton style={{ width: "45%", height: 12 }} />
    </div>)}
  </div>;
}
