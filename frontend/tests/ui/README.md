# Route and timetable UI regression fixtures

These entry points use synthetic schedules and intercept their own API requests. They never call JR/Yahoo or save to Notion. They are excluded from the production entry point and build.

- `npm run test:ui`: rendering assertions for PassengerLeg topology, through rides, walking, badges, estimated fares, platform/source semantics and unavailable departures.
- `npm run dev -- --port 5178`, then `/tests/ui/index.html`: interactive component and search-flow checks.
- `/tests/ui/responsive.html`: actual iframe viewports at 1440, 1024 and 390 CSS pixels, scaled to fit the inspection window. Diagnostics report viewport/page width and the active focus target.

Available scenarios: normal mixed-provider routes, long station/service names, the existing station-selection/search screen, route loading/empty, delayed timetable loading, unsupported, provider error, network error and empty timetable. Changing a scenario clears only fixture query/state. The Hashidate fixture has one PassengerLeg through Fukuchiyama, departure platform 31 and an independently missing arrival platform.

Manual interaction regression:

1. Tab to a route and press Enter. Tab to View timetable and press Enter.
2. Select an exact train with Enter. The next leg receives focus; its list excludes earlier departures.
3. Complete the last leg. Focus must land on `일정 확인`; Enter opens the save-confirmation flow. Use the explicit `save_success` or `save_retry` scenarios to test submission without any external write.
4. Change an earlier train. Later completed states disappear and an informational message appears.
5. Navigate independently to unsupported/error legs; verify Retry and navigation remain usable.
6. Use Show more/Show less by keyboard; daily/later alternatives remain separate.
7. At all three viewport widths inspect route cards, expansion, timetable, completion, English/Japanese wrapping, platforms and sources.

Keep screenshots and other run artifacts outside the source tree (for example `/private/tmp/autotrip-ui-step1`).

## Semantic route badges

- `badges` shows test-only same-day/next-day direct routes, a multi-transfer route and a cheapest route. `badge_search` uses the real search form with those mocked responses. Neither adds production alternatives nor forwards requests.
- `Direct` requires zero transfers and one non-walking PassengerLeg; `No transfers` independently requires a zero transfer count. Continuous through rides remain one PassengerLeg.
- `Departs tomorrow` compares the last submitted `departure_date` with the route's canonical `search_date`, using validated calendar dates and exactly one day of difference. Time strings and arrival rollover do not participate; missing/invalid dates or dates more than one day later do not receive the badge.
- Contract limitation: Route has no separate actual departure datetime. `search_date` is the existing per-route timetable calendar and must be correct in the response; unreported provider date rollovers cannot be inferred. Next-day route discovery is unchanged.
- Verified compact green/red pills and 30px ticket notches at 1440/1024/390, without horizontal overflow. Ranking badges and multi-transfer/cheapest cards remain distinct. Keyboard date selection, route expansion, timetable lookup and exact-train selection still work.
- Search integration verified: submit November 3 → November 4 route has the red badge; edit the picker to November 4 without submitting → existing badge stays; submit November 4 → badge disappears. The fixture's recorded request date matches each submission.
- `tests/routeBadges.test.ts` covers structured directness, next-day/month/year/leap boundaries, overnight arrivals, clock independence, invalid/missing dates and immutability. Rendering assertions cover independent labels and unchanged route-button callbacks/ARIA.

Use fixture pages only in hidden QA tabs; leave the actual `/` application as the user-facing page.

## Route ticket and picker refinement

- `npm test` includes calendar day/month navigation at leap-day, year and DST boundaries; `test:ui` also checks three-ride confirmation, source/platform meanings, picker labels and saved-state links.
- The mixed-route list includes a synthetic direct Nagoya → Tokyo Shinkansen, a continuous through ride and a three-ride transfer journey. No fixture schedule is real travel advice.
- `save_success` intercepts POST `/movements` and returns an in-memory success. `save_retry` returns one simulated failure, then succeeds. All other POST requests are rejected; no request is forwarded. The displayed Notion URL is a dummy presentation target, not a real saved page.
- Date: Arrow keys navigate days/weeks, Home/End move within the week, PageUp/PageDown change months (Shift changes years), Enter selects. Escape returns focus; outside clicks and leaving focus dismiss the non-modal popover.
- Time: ArrowUp/Down and Home/End adjust the focused hour/minute column, Tab moves between columns and actions. Values remain 24-hour `HH:mm` in JST.
- Verified at 1440/1024/390: separate route tickets, expansion/timeline, direct and multi-leg selection, missing/failed platform labels, confirmation and success disclosures. Mobile date/time popovers remain inside the viewport.
- Browser regression covered `2026-11-04` / `00:01` search values with canonical station IDs; fare sorting; Show more/less; invalid Notion URL; mock failure/retry; and changing the first train clearing later selections. A later second train correctly filtered out the incompatible `14:51` departure, leaving `15:51`.
- Notion URL edits clear only obsolete local validation feedback. Server validation, mutation payload, selection and chronology functions are unchanged.

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

### Shin-Osaka hero and parked train

The Home background uses original SVG train/platform art and a bilingual station sign. The parked train is a native button; it does not change query, station, route, or persistence state. Its complete five-car set departs right to left over 1.8 seconds, blocks repeated activation, reveals the platform for 450ms, then a new train enters right to left over 1.6 seconds. Reduced motion uses a brief emphasis without travel.

Additional browser checks:

- Confirm the background vending machine is revealed behind the departed train, and both streamlined ends read clearly at 1440/1024/390. Passenger windows and doors retain their original geometry.
- Click and press Enter/Space on the parked train; verify departure, reset, focus, and repeated-click handling. The fixture diagnostics record its observed phase sequence.
- Type in FROM and submit Search Routes during departure; fields and selected identities must remain usable and unchanged.
- Enable the fixture's reduced-motion simulation: the parked train should report `acknowledged → idle`, with no `departing` phase. Intro activation must enter Home directly.
- Replay the intro: confirm the large train moves right to left and reveals the mounted Home. The fixture diagnostics measure direction and rendered train width. Skip remains available throughout.
