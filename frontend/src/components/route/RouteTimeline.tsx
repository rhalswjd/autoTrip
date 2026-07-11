import type { Route, Station } from '../../api/types';
import { RouteLeg } from './RouteLeg';
import './RouteTimeline.css';

export interface RouteTimelineProps {
  route: Route;
}

interface TimelineStop {
  station: Station;
  type: 'departure' | 'transfer' | 'arrival';
}

function buildTimelineStops(stations: Station[]): TimelineStop[] {
  if (stations.length === 0) return [];
  if (stations.length === 1) {
    return [{ station: stations[0], type: 'departure' }];
  }

  return stations.map((station, index) => {
    if (index === 0) return { station, type: 'departure' as const };
    if (index === stations.length - 1) return { station, type: 'arrival' as const };
    return { station, type: 'transfer' as const };
  });
}

export function RouteTimeline({ route }: RouteTimelineProps) {
  const stops = buildTimelineStops(route.stations);
  const segments = route.polyline ? route.polyline.split(' -> ') : [];

  return (
    <div className="route-timeline" role="list" aria-label="Route timeline">
      <div className="route-timeline-header">
        <span className="route-timeline-title">Route Detail</span>
      </div>

      <div className="timeline-track">
        {stops.map((stop, index) => (
          <div key={`${stop.station.name}-${index}`} role="listitem">
            {/* Station Node */}
            <div className="timeline-node">
              <div className={`timeline-dot timeline-dot-${stop.type}`} />
              <div className="timeline-node-info">
                <span className="timeline-station-name">{stop.station.name}</span>
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

            {/* Leg between this stop and next */}
            {index < stops.length - 1 && (
              <RouteLeg
                railwayName={segments[index] || route.railway_name}
                stationCount={Math.max(1, Math.floor(route.stations.length / Math.max(1, route.transfer_count + 1)))}
                duration={index === 0 && route.transfer_count === 0 ? route.total_duration : undefined}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
