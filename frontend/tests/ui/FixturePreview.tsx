import { useEffect, useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { RouteResultList } from '../../src/components/route/RouteResultList';
import { SelectedRouteDetail } from '../../src/components/route/SelectedRouteDetail';
import { SearchPage } from '../../src/pages/SearchPage';
import { ToastProvider } from '../../src/components/ui/ToastProvider';
import type { MovementRequest, Route, StationSearchResult } from '../../src/api/types';
import { badgeRequestedDate, badgeRoutes, longNameRoute, routes, timetable } from './fixtures';
import '../../src/styles/global.css';
import '../../src/styles/layout.css';
import '../../src/styles/railway.css';

let scenario = 'available';
let saveAttempts = 0;
const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
const stations: StationSearchResult[] = [
  { id: 'fixture-kyoto', english_name: 'Kyoto', japanese_name: '京都', region: 'Kyoto', has_midori_office: true },
  { id: 'fixture-long', english_name: 'Kashihara-Jingumae (Kashihara Shrine)', japanese_name: '橿原神宮前', region: 'Nara', has_midori_office: false },
  { id: 'fixture-kii', english_name: 'Kii-Katsuura', japanese_name: '紀伊勝浦', has_midori_office: true },
  { id: 'fixture-yuhigaura', english_name: 'Yuhigaura-Kitsuonsen', japanese_name: '夕日ヶ浦木津温泉', has_midori_office: false },
];
// Test-only API boundary: never call live providers or write to Notion here.
window.fetch = async (input, options) => {
  const response = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
  const url = new URL(String(input), window.location.origin);
  if (options?.method === 'POST') {
    if (!url.pathname.endsWith('/movements') || !['save_success', 'save_retry'].includes(scenario)) return response({ detail: 'Persistence is disabled in this fixture scenario.' }, 400);
    const payload = JSON.parse(String(options.body)) as MovementRequest;
    saveAttempts += 1;
    window.dispatchEvent(new CustomEvent('fixture-save', { detail: `Mock save ${saveAttempts}: ${payload.route_id} · ${payload.legs?.length || 0} selected legs · ${payload.selected_departure_time} → ${payload.selected_arrival_time} · no external write` }));
    if (scenario === 'save_retry' && saveAttempts === 1) return response({ detail: '모의 저장 실패입니다. 다시 시도해 주세요.' }, 503);
    return response({ ...payload, search_mode: 'fixture', status: 'saved', notion_url: 'https://www.notion.so/00000000000000000000000000000000', child_page_ids: [] });
  }
  if (url.pathname.endsWith('/stations/search')) return response(stations.filter(station => station.english_name.toLowerCase().includes((url.searchParams.get('q') || '').toLowerCase())));
  if (url.pathname.endsWith('/search')) {
    window.dispatchEvent(new CustomEvent('fixture-search', { detail: url.searchParams.toString() }));
    return response(scenario === 'badge_search' ? badgeRoutes : routes);
  }
  const index = Number(url.pathname.match(/\/legs\/(\d+)/)?.[1] || 0);
  const routeId = url.pathname.match(/\/routes\/([^/]+)/)?.[1];
  const data = timetable(index, url.searchParams.get('date') || undefined, routeId);
  if (scenario === 'slow') await new Promise(resolve => setTimeout(resolve, 2000));
  if (scenario === 'network') return response({ detail: 'Internal fixture error must not appear in the UI' }, 503);
  if (scenario === 'unsupported') Object.assign(data, { status: 'unsupported', availability: 'UNSUPPORTED', weekday: [] });
  if (scenario === 'provider_error') Object.assign(data, { status: 'provider_error', availability: 'PROVIDER_ERROR', weekday: [] });
  if (scenario === 'empty' && index > 0) data.weekday = [];
  return response(data);
};

function ViewportStatus() {
  const [status, setStatus] = useState('Measuring viewport');
  const [request, setRequest] = useState('');
  const [save, setSave] = useState('');
  useEffect(() => {
    const capture = (event: Event) => setRequest(decodeURIComponent((event as CustomEvent<string>).detail));
    const captureSave = (event: Event) => setSave((event as CustomEvent<string>).detail);
    window.addEventListener('fixture-search', capture);
    window.addEventListener('fixture-save', captureSave);
    return () => { window.removeEventListener('fixture-search', capture); window.removeEventListener('fixture-save', captureSave); };
  }, []);
  useEffect(() => {
    let lastTrainX: number | null = null;
    let trainMotion = '';
    const parkedPhases: string[] = [];
    const observeParkedTrain = () => {
      const phase = document.querySelector('.platform-train-control')?.className.split('is-')[1];
      if (phase && parkedPhases.at(-1) !== phase) { parkedPhases.push(phase); if (parkedPhases.length > 6) parkedPhases.shift(); }
    };
    const observer = new MutationObserver(observeParkedTrain);
    observer.observe(document.documentElement, { subtree: true, attributes: true, attributeFilter: ['class'], childList: true });
    const measure = () => {
      const train = document.querySelector('.is-accepting .entry-train');
      if (train) {
        const box = train.getBoundingClientRect();
        if (lastTrainX !== null && box.x < lastTrainX - 2) trainMotion = ` · Train: RIGHT → LEFT, ${Math.round(box.width)}px wide`;
        lastTrainX = box.x;
      } else lastTrainX = null;
      const active = document.activeElement;
      setStatus(`${window.innerWidth}px · page ${document.documentElement.scrollWidth}px · ${document.documentElement.scrollWidth <= window.innerWidth ? 'no horizontal overflow' : 'OVERFLOW'} · Focus: ${active?.getAttribute('aria-label') || active?.textContent?.slice(0, 65) || active?.tagName}${trainMotion}${parkedPhases.length ? ` · Parked train: ${parkedPhases.join(' → ')}` : ''}`);
    };
    const timer = window.setInterval(measure, 250);
    measure();
    return () => { window.clearInterval(timer); observer.disconnect(); };
  }, []);
  return <output style={{ display: 'block', padding: '6px 12px', background: '#e9eef5', color: '#123c71', fontSize: 11 }} aria-label="Viewport diagnostics">{status}{request && <span style={{ display: 'block', overflowWrap: 'anywhere' }}>Last search: {request}</span>}{save && <span style={{ display: 'block' }}>{save}</span>}</output>;
}

export function FixturePreview() {
  const [selected, setSelected] = useState<Route | null>(null);
  const [revision, setRevision] = useState(0);
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const original = window.matchMedia.bind(window);
    if (reduced) window.matchMedia = query => query === '(prefers-reduced-motion: reduce)' ? { matches: true, media: query, onchange: null, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent: () => true } : original(query);
    return () => { window.matchMedia = original; };
  }, [reduced]);
  const [mode, setMode] = useState(new URLSearchParams(window.location.search).has('home') ? 'search_flow' : 'available');
  useEffect(() => { scenario = mode; }, [mode]);
  return <QueryClientProvider client={client}><ToastProvider><MemoryRouter>
    <div style={{ padding: 12, background: '#e9eef5', color: '#123c71', fontSize: 12 }}>
      <strong>UI TEST FIXTURES · Synthetic schedules · No external writes</strong>{' '}
      <label>Scenario <select aria-label="Fixture scenario" value={mode} onChange={event => { scenario = event.target.value; saveAttempts = 0; setMode(scenario); client.clear(); setRevision(value => value + 1); setSelected(null); }}>
        {['available', 'badges', 'badge_search', 'long_names', 'search_flow', 'save_success', 'save_retry', 'route_loading', 'route_empty', 'slow', 'unsupported', 'provider_error', 'network', 'empty'].map(value => <option key={value}>{value}</option>)}
      </select></label>
      <label style={{ marginLeft: 12 }}><input type="checkbox" checked={reduced} onChange={event => setReduced(event.target.checked)} /> Simulate reduced motion</label>
    </div>
    <ViewportStatus />
    {['search_flow', 'badge_search'].includes(mode) ? <SearchPage key={revision} /> : <main style={{ maxWidth: 1040, margin: '0 auto', padding: 20 }} key={revision}>
      <RouteResultList routes={mode === 'route_empty' ? [] : mode === 'long_names' ? [longNameRoute] : mode === 'badges' ? badgeRoutes : routes} requestedDepartureDate={mode === 'badges' ? badgeRequestedDate : undefined} isLoading={mode === 'route_loading'} selectedRoute={selected} onSelectRoute={route => setSelected(previous => previous?.id === route.id ? null : route)} renderDetail={route => <SelectedRouteDetail key={route.id} route={route} />} />
    </main>}
  </MemoryRouter></ToastProvider></QueryClientProvider>;
}
