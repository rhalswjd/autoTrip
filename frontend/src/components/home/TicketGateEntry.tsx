import { useEffect, useRef, useState } from 'react';
import { Shinkansen } from './Shinkansen';

interface Props { onEnter: () => void }

/** An optional, interruptible introduction. It never owns search or route state. */
export function TicketGateEntry({ onEnter }: Props) {
  const [accepting, setAccepting] = useState(false);
  const ticketRef = useRef<HTMLButtonElement>(null);
  useEffect(() => { ticketRef.current?.focus({ preventScroll: true }); }, []);
  useEffect(() => {
    if (!accepting) return;
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (motion.matches) { onEnter(); return; }
    const timer = window.setTimeout(onEnter, 2650);
    const handleMotionChange = () => { if (motion.matches) onEnter(); };
    motion.addEventListener('change', handleMotionChange);
    return () => { window.clearTimeout(timer); motion.removeEventListener('change', handleMotionChange); };
  }, [accepting, onEnter]);
  return <main className={`ticket-entry ${accepting ? 'is-accepting' : ''}`} aria-labelledby="entry-title">
    <button type="button" className="entry-skip" onClick={onEnter}>Skip intro <span aria-hidden="true">↗</span></button>
    <div className="entry-interior">
    <header className="home-header"><span className="home-wordmark"><span aria-hidden="true">↗</span> AutoTrip</span></header>
    <div className="entry-heading"><p className="home-eyebrow">日本の鉄道旅 / JAPAN BY RAIL</p>
      <h1 id="entry-title">A little ticket.<br />A new journey.</h1><p>Your next stop is up to you.</p>
    </div>
    <div className="entry-scene">
      <button type="button" ref={ticketRef} className="entry-ticket" aria-label="Insert ticket and enter route search" aria-disabled={accepting}
        onClick={() => { if (!accepting) setAccepting(true); }}>
        <span className="ticket-top"><span>旅のはじまり</span><span>AUTOTRIP</span></span>
        <span className="ticket-route"><span>京都<small>Kyoto</small></span><span aria-hidden="true">→</span><span>夕日ヶ浦木津温泉<small>Yuhigaura-Kitsuonsen</small></span></span>
        <span className="ticket-rule" />
        <span className="ticket-bottom"><span>経路検索 · ROUTE SEARCH</span><span>01 →</span></span>
        <span className="ticket-marks" aria-hidden="true">▥ ▥▥ ▥ ▥▥▥ ▥ ▥▥</span>
      </button>
      <svg className="entry-gate" viewBox="0 0 460 240" aria-hidden="true">
        <path d="M62 56 114 18H355L405 56V194L355 225H62Z" fill="#d3dce0" stroke="#9baeb8" />
        <path d="M62 56H405L355 18H114Z" fill="#edf1f0" stroke="#abbcc5" />
        <path d="M355 82 405 56V194L355 225Z" fill="#a8bbc7" />
        <path d="M62 82H355V225H62Z" fill="#e5eaeb" />
        <path d="M62 82H355V110H62Z" fill="#0759ad" />
        <path d="M355 82 405 56V84L355 110Z" fill="#03488e" />
        <rect x="135" y="42" width="174" height="18" rx="5" fill="#607581" />
        <rect x="143" y="47" width="158" height="5" rx="2" fill="#102c40" />
        <path d="M155 28H289" stroke="#0759ad" strokeWidth="3" />
        <rect x="94" y="132" width="74" height="63" rx="6" fill="#14374d" />
        <path d="M111 164H150M139 151 152 164 139 177" fill="none" stroke="#b8f5db" strokeWidth="5" />
        <circle className="gate-status" cx="320" cy="140" r="6" fill="#74a9cc" />
        <text x="195" y="161" fill="#294f69" fontSize="14" letterSpacing="2">入口 / ENTRY</text>
        <text x="195" y="183" fill="#617785" fontSize="10" letterSpacing="1">YOUR JOURNEY BEGINS</text>
        <path d="M80 214H335" stroke="#b8c6cd" />
      </svg>

    </div>
    <div className="entry-caption" aria-live="polite"><p>{accepting ? 'Welcome aboard. Let’s find your route.' : 'Tap your ticket to begin.'}</p>
      <span>{accepting ? 'Search is just ahead.' : 'Click, tap or press Enter · You can skip anytime'}</span>
    </div>
    <p className="entry-footnote">A journey planner for Japan. No ticket purchase required.</p>
    </div>
    <div className="entry-sweep"><Shinkansen className="entry-train" /></div>
  </main>;
}
