import { Skeleton, Card } from '../ui';
import './Search.css';

export function SearchLoading() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <Card key={i} className="search-loading-item">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Skeleton variant="text" style={{ width: '40%' }} />
            <Skeleton variant="text" style={{ width: '60px' }} />
          </div>
          <Skeleton variant="text" style={{ width: '25%' }} />
        </Card>
      ))}
    </>
  );
}
