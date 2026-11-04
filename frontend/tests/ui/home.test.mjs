import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const server = await createServer({ cacheDir: 'node_modules/.vite-ui-tests', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' });
const storage = new Map();
const previousStorage = Object.getOwnPropertyDescriptor(globalThis, 'sessionStorage');
Object.defineProperty(globalThis, 'sessionStorage', { configurable: true, value: {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
} });
try {
  const { TicketGateEntry } = await server.ssrLoadModule('/src/components/home/TicketGateEntry.tsx');
  const { SearchPage } = await server.ssrLoadModule('/src/pages/SearchPage.tsx');
  const { hasEnteredHome, rememberHomeEntry } = await server.ssrLoadModule('/src/utils/homeEntry.ts');
  const { QueryClient, QueryClientProvider } = await import('@tanstack/react-query');
  const { MemoryRouter } = await import('react-router-dom');
  const { ToastProvider } = await server.ssrLoadModule('/src/components/ui/ToastProvider.tsx');
  const renderHome = () => renderToStaticMarkup(createElement(QueryClientProvider, { client: new QueryClient() },
    createElement(ToastProvider, null, createElement(MemoryRouter, null, createElement(SearchPage)))));
  const intro = renderToStaticMarkup(createElement(TicketGateEntry, { onEnter() {} }));
  assert.match(intro, /<button[^>]*type="button"[^>]*class="entry-skip"/);
  assert.match(intro, /aria-label="Insert ticket and enter route search"/);
  assert.match(intro, /経路検索 · ROUTE SEARCH/);
  assert.match(intro, /YOUR JOURNEY BEGINS/);
  assert.doesNotMatch(intro, /YOUR JOURNEY STARTS HERE/);
  assert.equal(hasEnteredHome(), false);
  const firstVisit = renderHome();
  assert.match(firstVisit, /A little ticket/);
  assert.match(firstVisit, /class="home-destination" inert="" aria-hidden="true"/);
  rememberHomeEntry();
  assert.equal(storage.get('autotrip.home.entered'), 'yes');
  assert.equal(hasEnteredHome(), true);
  const home = renderHome();
  assert.doesNotMatch(home, /class="entry-ticket"/);
  assert.equal((home.match(/role="combobox"/g) || []).length, 2);
  assert.match(home, />FROM<\/label>/);
  assert.match(home, />TO<\/label>/);
  assert.match(home, /aria-label="Swap stations"/);
  assert.match(home, /id="route-departure-date"/);
  assert.match(home, /id="route-departure-time"/);
  assert.match(home, /Search Routes/);
  assert.match(home, /Japan Standard Time/);
  assert.match(home, /Shin-Osaka/);
  assert.match(home, /新大阪/);
  assert.match(home, /class="platform-train"/);
  assert.match(home, /class="platform-vending"/);
  assert.ok(home.indexOf('class="platform-vending"') < home.indexOf('class="platform-train-control'));
  assert.equal((home.match(/data-car=/g) || []).length, 5);
  assert.match(home, /data-car="rear" transform="translate\(4010 0\) scale\(-1 1\)"/);
  assert.equal((home.match(/width="90" height="61" rx="15" fill="#37566e"/g) || []).length, 18);
  assert.equal((home.match(/width="66" height="211" rx="9"/g) || []).length, 5);
  assert.match(home, /aria-label="Watch the parked Shinkansen depart" aria-disabled="false"/);
  assert.match(home, /class="home-destination" aria-hidden="false"/);
  console.log('Home regressions passed: optional native-button entry/skip, session persistence, revisit bypass, two station comboboxes, existing date/time/search controls.');
} finally {
  if (previousStorage) Object.defineProperty(globalThis, 'sessionStorage', previousStorage);
  else delete globalThis.sessionStorage;
  await server.close();
}
