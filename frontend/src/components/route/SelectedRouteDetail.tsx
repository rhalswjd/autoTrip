import { useState } from 'react';
import type { Route } from '../../api/types';
import { RouteTimelineV2 } from './v2/RouteTimelineV2';
import { RouteSummary } from './RouteSummary';
import { TransferWizard } from '../timetable/TransferWizard';

export function SelectedRouteDetail({ route }: { route: Route }) {
  const rides = route.passenger_legs.filter(leg => leg.segment_type !== 'walk').length;
  const [preview, setPreview] = useState(route);
  const [overviewOpen, setOverviewOpen] = useState(true);
  const [requestedLeg, setRequestedLeg] = useState<{ index: number; requestId: number }>();
  return <>
    <details className="rail-overview" open={overviewOpen} onToggle={event => setOverviewOpen(event.currentTarget.open)}>
      <summary>Route overview <span>{rides} {rides === 1 ? 'ride' : 'rides'} · {route.transfer_count} transfers</span></summary>
      <RouteTimelineV2 route={route} onViewTimetable={index => { setOverviewOpen(false); setRequestedLeg(previous => ({ index, requestId: (previous?.requestId || 0) + 1 })); }} />
    </details>
    <TransferWizard route={route} requestedLeg={requestedLeg} onItineraryChange={setPreview} />
    <details className="rail-overview"><summary>Journey summary <span>Updates with your selected trains</span></summary><RouteSummary route={preview} /></details>
  </>;
}
