import { useEffect, useRef, useState } from 'react';
import { Shinkansen } from './Shinkansen';

type DeparturePhase = 'idle' | 'departing' | 'away' | 'returning' | 'acknowledged';

/** A local decorative interaction; it never changes search or navigation state. */
export function ParkedTrain() {
  const [phase, setPhase] = useState<DeparturePhase>('idle');
  const busy = useRef(false);
  useEffect(() => {
    if (phase === 'idle') { busy.current = false; return; }
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const finish = () => setPhase(phase === 'departing' ? 'away' : phase === 'away' ? 'returning' : 'idle');
    const timer = window.setTimeout(finish, phase === 'departing' ? 1800 : phase === 'away' ? 450 : phase === 'returning' ? 1600 : 220);
    const reduceMotion = () => { if (motion.matches) setPhase('acknowledged'); };
    motion.addEventListener('change', reduceMotion);
    return () => { window.clearTimeout(timer); motion.removeEventListener('change', reduceMotion); };
  }, [phase]);
  return <button type="button" className={`platform-train-control is-${phase}`}
    aria-label="Watch the parked Shinkansen depart" aria-disabled={phase !== 'idle'}
    title="Watch the Shinkansen depart" onClick={() => {
      if (busy.current) return;
      busy.current = true;
      setPhase(window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'acknowledged' : 'departing');
    }}><Shinkansen className="platform-train" /></button>;
}
