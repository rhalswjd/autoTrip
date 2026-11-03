import { useEffect, useState, type ReactNode } from 'react';

/** Keep the outgoing panel mounted just long enough for its height to close. */
export function RouteExpansion({ id, expanded, children }: { id: string; expanded: boolean; children: ReactNode }) {
  const [present, setPresent] = useState(expanded);
  useEffect(() => {
    if (expanded) { setPresent(true); return; }
    const timer = window.setTimeout(() => setPresent(false), 200);
    return () => window.clearTimeout(timer);
  }, [expanded]);
  return <div id={id} className="rail-expansion" data-open={expanded} aria-hidden={!expanded} inert={!expanded}>
    <div>{(expanded || present) && <div className="rail-route-detail">{children}</div>}</div>
  </div>;
}
