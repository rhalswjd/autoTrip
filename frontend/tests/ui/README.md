# Route and timetable UI regression fixtures

These entry points use synthetic schedules and intercept their own API requests. They never call JR/Yahoo or save to Notion. They are excluded from the production entry point and build.

- `npm run test:ui`: rendering assertions for PassengerLeg topology, through rides, walking, badges, estimated fares, platform/source semantics and unavailable departures.
- `npm run dev -- --port 5178`, then `/tests/ui/index.html`: interactive component and search-flow checks.
- `/tests/ui/responsive.html`: actual iframe viewports at 1440, 1024 and 390 CSS pixels, scaled to fit the inspection window. Diagnostics report viewport/page width and the active focus target.

Available scenarios: normal mixed-provider routes, long station/service names, the existing station-selection/search screen, route loading/empty, delayed timetable loading, unsupported, provider error, network error and empty timetable. Changing a scenario clears only fixture query/state. The Hashidate fixture has one PassengerLeg through Fukuchiyama, departure platform 31 and an independently missing arrival platform.

Manual interaction regression:

1. Tab to a route and press Enter. Tab to View timetable and press Enter.
2. Select an exact train with Enter. The next leg receives focus; its list excludes earlier departures.
3. Complete the last leg. Focus must land on `일정 확인`; Enter opens the unchanged save-confirmation flow. Inspect save eligibility without submitting.
4. Change an earlier train. Later completed states disappear and an informational message appears.
5. Navigate independently to unsupported/error legs; verify Retry and navigation remain usable.
6. Use Show more/Show less by keyboard; daily/later alternatives remain separate.
7. At all three viewport widths inspect route cards, expansion, timetable, completion, English/Japanese wrapping, platforms and sources.

Keep screenshots and other run artifacts outside the source tree (for example `/private/tmp/autotrip-ui-step1`).

## Home entry and search

- `npm run test:home`: render/session regressions for native ticket/skip buttons, revisit bypass, station comboboxes and reuse of existing date/time/search controls.
- `/tests/ui/responsive.html?home`: opens Home at the selected real viewport width. The fixture includes Kyoto, Kii-Katsuura, Yuhigaura-Kitsuonsen and a long Kashihara name.
- `Replay intro · dev preview` is available only in development. The intro remembers completion in sessionStorage; replay does not clear search input.
- `Simulate reduced motion` is fixture-only and substitutes the media-query result used by the entry controller. It tests the direct-entry branch without changing the user's OS preference. The production CSS additionally disables motion using the real media query.

Home interaction checks (real browser, not covered by server rendering):

1. First visit: visible ticket and Skip; Enter/Space on the ticket completes entry, with FROM focused.
2. Replay and Skip, including while the ticket is being accepted; search remains immediately available.
3. Enable reduced-motion simulation, replay and activate the ticket: direct entry with no acceptance/train interval.
4. Type `kii` in FROM, ArrowDown/Enter; TO receives focus. Type `yuhi` and choose a result; Travel date receives focus.
5. Swap twice; full station identities and metadata follow their endpoints. Clear/edit an endpoint; Search Routes is disabled until a station is selected again.
6. Change date/time, search, then open a route and its timetable. Route results and exact-departure UI use the existing components.
7. Reload/revisit: no intro; repeat at 1440/1024/390, including the long station suggestion and selected value. Verify diagnostics report no horizontal overflow.
