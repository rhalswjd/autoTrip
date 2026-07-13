import type { Route, Station, RouteSegment } from '../../api/types';
import { RouteLeg } from './RouteLeg';
import './RouteTimeline.css';

export interface RouteTimelineProps {
  route: Route;
}

interface TimelineStop {
  station: Station;
  type: 'departure' | 'transfer' | 'arrival' | 'through';
  displayName: string;
}

function buildTimelineStops(stations: Station[], segments: RouteSegment[]): TimelineStop[] {
  if (stations.length === 0) return [];
  if (stations.length === 1) {
    return [{ station: stations[0], type: 'departure', displayName: stations[0].name }];
  }

  return stations.map((station, index) => {
    let type: TimelineStop['type'] = 'transfer';
    if (index === 0) {
      type = 'departure';
    } else if (index === stations.length - 1) {
      type = 'arrival';
    } else {
      // index corresponds to the segment departing from this station
      const segment = segments[index];
      if (segment && segment.is_through) {
        type = 'through';
      }
    }

    return { station, type, displayName: station.name };
  });
}

export function RouteTimeline({ route }: RouteTimelineProps) {
  const stops = buildTimelineStops(route.stations, route.segments || []);
  const segments = route.segments || [];

  return (
    <div className="route-timeline" role="list" aria-label="Route timeline">
      <div className="route-timeline-header">
        <span className="route-timeline-title">Route Detail</span>
      </div>

      <div className="timeline-track">
        {stops.map((stop, index) => {
          const isLast = index === stops.length - 1;
          const segment = segments[index];
          const isWalk = segment?.segment_type === 'walk';
          const railwayName = segment?.railway_name || route.railway_name;
          
          return (
            <div key={`${stop.station.id || stop.station.name}-${index}`} className="timeline-item-wrapper" role="listitem">
              {/* Segment line extending to the next node */}
              {!isLast && (
                <div className={`timeline-segment-line ${isWalk ? 'timeline-segment-line-dashed' : ''}`} aria-hidden="true" />
              )}
              
              {/* Station Node */}
              {stop.type === 'through' ? (
                <div className="timeline-node timeline-node-through">
                  <div className="timeline-dot timeline-dot-through" />
                  <div className="timeline-node-info">
                    <span className="timeline-station-name timeline-station-name-through">Through Service</span>
                    <span className="timeline-station-platform" style={{ color: 'var(--color-text-muted)' }}>
                      No transfer required at {stop.displayName}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="timeline-node">
                  <div className={`timeline-dot timeline-dot-${stop.type}`} />
                  <div className="timeline-node-info">
                    <span className="timeline-station-name">{stop.displayName}</span>
                    {stop.station.platform && (
                      <span className="timeline-station-platform">
                        Platform {stop.station.platform}
                      </span>
                    )}
                    {stop.station.has_midori_office && (
                      <span className="timeline-station-platform" style={{ color: 'var(--color-success)' }}>
                        Midori no Madoguchi
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Leg between this stop and next */}
              {!isLast && (
                <RouteLeg
                  railwayName={railwayName}
                  duration={index === 0 && route.transfer_count === 0 ? route.total_duration : undefined}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
