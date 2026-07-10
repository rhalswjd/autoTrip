import { useParams } from 'react-router-dom';
import { EmptyView } from '../components';

export function RouteDetailPage() {
  const { routeId } = useParams<{ routeId: string }>();

  return (
    <div className="content-inner">
      <h1 style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', marginBottom: 'var(--space-6)', letterSpacing: '-0.02em' }}>Route Detail</h1>
      <EmptyView
        title={`Route ${routeId || ''}`}
        description="Timetable and movement creation will be available here."
      />
    </div>
  );
}
