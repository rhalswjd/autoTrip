import { Skeleton } from '../ui';
import '../../styles/railway.css';

export function TimetableLoading() {
  return <div className="rail-loading rail-ui" role="status" aria-label="Loading train departures" aria-busy="true">
    {Array.from({ length: 3 }, (_, index) => <div key={index} className="rail-loading-row" aria-hidden="true">
      <div className="rail-loading-times"><Skeleton style={{ width: 72, height: 28 }} /><Skeleton style={{ width: 72, height: 28 }} /></div>
      <Skeleton style={{ width: "50%", height: 13 }} /><Skeleton style={{ width: "80%", height: 10 }} />
    </div>)}
  </div>;
}
