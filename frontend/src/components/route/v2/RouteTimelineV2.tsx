import React from 'react';
import type { Route, RouteSegment } from '../../../api/types';
import { TrainFront, BusFront, Footprints } from 'lucide-react';
import './RouteTimelineV2.css';
import { getLineColor } from './utils';

export interface RouteTimelineV2Props {
  route: Route;
}

function getPrimaryRouteIcon(segments: RouteSegment[]) {
  if (segments.some(s => s.segment_type === 'train')) return <TrainFront size={20} />;
  if (segments.some(s => s.segment_type === 'bus')) return <BusFront size={20} />;
  return <Footprints size={20} />;
}

export function RouteTimelineV2({ route }: RouteTimelineV2Props) {
  const { stations = [], segments = [] } = route;

  return (
    <div className="rt-container" role="list" aria-label="Route timeline">
      <div className="rt-header">
        {getPrimaryRouteIcon(segments)}
        <span className="rt-header-title">Route Detail</span>
      </div>
      {stations.map((station, i) => {
        const segment = segments[i]; // Segment leaving this station
        const prevSegment = i > 0 ? segments[i - 1] : null;
        const isLast = i === stations.length - 1;

        let nodeType = 'transfer';
        if (i === 0) nodeType = 'departure';
        else if (isLast) nodeType = 'arrival';
        else if (segment && segment.is_through) nodeType = 'through';

        // Colors
        const prevColor = prevSegment ? getLineColor(prevSegment.railway_name) : 'transparent';
        const nextColor = segment ? getLineColor(segment.railway_name) : 'transparent';

        const isPrevWalk = prevSegment?.segment_type === 'walk';
        const isNextWalk = segment?.segment_type === 'walk';

        return (
          <React.Fragment key={`${station.id || station.name}-${i}`}>
            {/* Station Node Row */}
            <div className="rt-row" role="listitem">
              <div className="rt-track">
                {/* Top half line (comes from previous segment) */}
                {i > 0 && (
                  <div 
                    className={`rt-line-top ${isPrevWalk ? 'rt-line-walk' : ''}`} 
                    style={{ background: isPrevWalk ? 'transparent' : prevColor }} 
                  />
                )}
                {/* Bottom half line (goes to next segment) */}
                {!isLast && (
                  <div 
                    className={`rt-line-bottom ${isNextWalk ? 'rt-line-walk' : ''}`} 
                    style={{ background: isNextWalk ? 'transparent' : nextColor }} 
                  />
                )}
                
                {/* Node Dot */}
                {nodeType === 'through' ? (
                  <div className="rt-node-through" />
                ) : (
                  <div 
                    className={`rt-node-outer rt-node-${nodeType}`} 
                    style={{ borderColor: isLast ? prevColor : nextColor }}
                  />
                )}
              </div>
              <div className="rt-content">
                <div className="rt-station-header">
                  <span className="rt-station-name">{station.name}</span>
                  {/* Time would go here if available, e.g., <span className="rt-station-time">5:35 AM</span> */}
                </div>
                {nodeType === 'through' && (
                  <div className="rt-through-text">Remain on board</div>
                )}
              </div>
            </div>

            {/* Segment Row (Train or Walk) */}
            {!isLast && segment && (
              <div className="rt-row">
                <div className="rt-track">
                  <div 
                    className={`rt-line-full ${isNextWalk ? 'rt-line-walk' : ''}`} 
                    style={{ background: isNextWalk ? 'transparent' : nextColor }} 
                  />
                  {isNextWalk && <div className="rt-walk-icon"><Footprints size={16} /></div>}
                </div>
                <div className="rt-content">
                  {isNextWalk ? (
                    <div className="rt-walk-text">
                      {segment.railway_name || 'Walk'}
                    </div>
                  ) : (
                    <div className="rt-train-segment">
                      <div className="rt-train-badge-row">
                        <span className="rt-train-badge" style={{ background: nextColor }}>
                          {segment.segment_type === 'bus' ? 'Bus' : 'Train'}
                        </span>
                        <span className="rt-train-name">{segment.railway_name}</span>
                      </div>
                      
                      {/* Optional Stops accordion UI (pseudo for now) */}
                      {/* Real stops data would be parsed or fetched if available */}
                      {route.transfer_count > 0 && i === 0 && (
                        <div className="rt-stops-accordion">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="6 9 12 15 18 9"></polyline>
                          </svg>
                          Ride
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
