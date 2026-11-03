import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const server = await createServer({ cacheDir: 'node_modules/.vite-ui-tests', server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' });
try {
  const { RouteTimelineV2 } = await server.ssrLoadModule('/src/components/route/v2/RouteTimelineV2.tsx');
  const { RouteCard } = await server.ssrLoadModule('/src/components/route/RouteCard.tsx');
  const { TimetableCard } = await server.ssrLoadModule('/src/components/timetable/TimetableCard.tsx');
  const { route, throughRoute, walkingRoute, departure } = await server.ssrLoadModule('/tests/ui/fixtures.ts');
  const render = (component, props) => renderToStaticMarkup(createElement(component, props));
  const through = render(RouteTimelineV2, { route: throughRoute, onViewTimetable() {} });
  assert.equal((through.match(/View timetable/g) || []).length, 1);
  assert.match(through, /Remain onboard/);
  assert.doesNotMatch(through, /Transfer ·/);
  const walk = render(RouteTimelineV2, { route: walkingRoute, onViewTimetable() {} });
  assert.equal((walk.match(/View timetable/g) || []).length, 2);
  assert.match(walk, /is-walk/);
  const card = render(RouteCard, { route: { ...route, fare_status: 'exact' }, isSelected: true, onClick() {} });
  assert.match(card, /Estimated fare/);
  assert.match(card, /Long transfer wait/);
  assert.match(card, /aria-expanded="true"/);
  assert.match(render(RouteCard, { route: throughRoute, isSelected: false, onClick() {} }), /Fewest transfers/);
  const official = render(TimetableCard, { departure: departure(1, '12:11', '14:43'), isSelected: true, onClick() {} });
  assert.match(official, /JR Odekake · Official/);
  assert.match(official, /공식 정보 미제공/);
  assert.match(official, /aria-pressed="true"/);
  const fallback = render(TimetableCard, { departure: departure(2, '14:51', '15:24'), onClick() {} });
  assert.match(fallback, /Yahoo · Timetable/);
  assert.doesNotMatch(fallback, /Official/);
  assert.match(fallback, /조회 실패/);
  const missingArrival = render(TimetableCard, { departure: departure(0, '06:45', ''), onClick() {} });
  assert.match(missingArrival, /disabled/);
  assert.match(missingArrival, /Arrival time is not confirmed/);
  console.log('UI rendering regressions passed: through ride, walking, estimated fare, long waits, source/platform states, selection and unavailable departure.');
} finally {
  await server.close();
}
