import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ArrowRightLeft } from 'lucide-react';
import { StationPlatform } from '../components/home/StationPlatform';
import { TicketGateEntry } from '../components/home/TicketGateEntry';
import { hasEnteredHome, rememberHomeEntry } from '../utils/homeEntry';
import { StationCombobox } from '../components/home/StationCombobox';
import { RouteSearchForm, RouteResultList } from '../components/route';
import { SelectedRouteDetail } from '../components/route/SelectedRouteDetail';
import { useRoutePanel } from '../hooks';
import '../styles/railway.css';
import '../styles/home.css';

export function SearchPage() {
  const fromRef = useRef<HTMLInputElement>(null);
  const toRef = useRef<HTMLInputElement>(null);
  const panel = useRoutePanel();
  const [showEntry, setShowEntry] = useState(() => !hasEnteredHome());
  const enter = useCallback(() => { rememberHomeEntry(); setShowEntry(false); }, []);
  useEffect(() => {
    if (!showEntry) { window.scrollTo(0, 0); fromRef.current?.focus({ preventScroll: true }); }
  }, [showEntry]);
  const hasResults = !!panel.routes || panel.routesLoading;
  return <div className={`home-page ${showEntry ? "home-entering" : "home-arrived"}`}>
    <div className="home-destination" inert={showEntry} aria-hidden={showEntry}>
    <StationPlatform />
    <header className="home-header">
      <Link className="home-wordmark" to="/" aria-label="AutoTrip home"><span aria-hidden="true">↗</span> AutoTrip</Link>
      <nav aria-label="Main navigation"><span aria-current="page">Plan a journey</span><Link to="/settings">Settings</Link></nav>
    </header>
    <main className={`home-main ${hasResults ? 'has-results' : ''}`}>
      <section className="home-search" aria-labelledby="home-title">
        <div className="home-heading"><p className="home-eyebrow">日本の鉄道旅 / JAPAN BY RAIL</p>
          <h1 id="home-title">Where are you going<span>?</span></h1>
          <p>From the first platform to the last stop.</p>
        </div>
        <div className="home-wayfinding"><span>01</span><span>Find your route <small>経路を探す</small></span><ArrowRight size={22} aria-hidden="true" /></div>
        <div className="home-stations">
          <StationCombobox label="FROM" inputRef={fromRef} station={panel.departureStation} onChange={panel.setDepartureStation} onSelected={() => toRef.current?.focus()} />
          <button className="home-swap" type="button" aria-label="Swap stations" disabled={!panel.departureStation && !panel.arrivalStation}
            onClick={() => { panel.setDepartureStation(panel.arrivalStation); panel.setArrivalStation(panel.departureStation); }}><ArrowRightLeft size={20} /></button>
          <StationCombobox label="TO" inputRef={toRef} station={panel.arrivalStation} onChange={panel.setArrivalStation} onSelected={() => document.getElementById('route-departure-date')?.focus()} />
        </div>
        <div className="home-search-controls">
          <RouteSearchForm departure={panel.departureStation} arrival={panel.arrivalStation}
            onDepartureChange={panel.setDepartureStation} onArrivalChange={panel.setArrivalStation} onRoutesLoaded={panel.handleRoutesLoaded} />
        </div>
        <p className="home-time-note">All departure times are Japan Standard Time · JST</p>
      </section>
      {hasResults && <section className="home-results" aria-label="Route search results">
        <RouteResultList routes={panel.routes} requestedDepartureDate={panel.requestedDepartureDate} isLoading={panel.routesLoading} selectedRoute={panel.selectedRoute}
          onSelectRoute={panel.handleRouteSelect} renderDetail={route => <SelectedRouteDetail key={route.id} route={route} />} />
      </section>}
      <footer className="home-footer"><span>YOUR NEXT STOP STARTS HERE</span><span>日本を、鉄道で。</span></footer>
      {import.meta.env.DEV && <button className="home-replay" type="button" onClick={() => setShowEntry(true)}>Replay intro · dev preview</button>}
    </main>
    </div>
    {showEntry && <TicketGateEntry onEnter={enter} />}
  </div>;
}
