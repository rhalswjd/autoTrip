# AutoTrip Architecture Document

## Project Overview
AutoTrip is a personal railway travel planner for Japan, designed for local macOS environments. The current application searches routes, displays railway timelines and exact departures, and saves verified selections into Notion. An interactive map remains a design goal, not an implemented feature of the current frontend.

## Requirements
- **MVP Focus**: Simplify domains to focus purely on the search, selection, and save flow (`SearchRequest` -> `Route` -> `Timetable` -> `Movement`).
- **Deterministic search context**: The public route search requires an explicit departure date/time and preserves it through cached Routes and exact timetable lookups. Internal legacy SearchContext modes are not a time-unspecified public search contract.
- **Data Purity**: The Domain layer (`Route`) must represent physical train paths only, devoid of any external system logic (e.g., Notion properties).
- **Testability**: Must implement Dependency Inversion (Ports & Adapters) so the core application can be tested using Fakes (without HTTP, Scraper, or Notion API).
- **UX**: Route selection, detail timeline and PassengerLeg exact selections remain synchronized. A map-based interface is planned.

## Domain Model
The Domain layer contains validated models and pure matching/chronology rules. It does not perform provider, database or Notion I/O.

- **SearchRequest (DTO)**: Carries selected station IDs/Japanese names and explicit departure date/time.
- **Route (Entity)**: Carries station identity, raw segments, derived PassengerLegs, query context, elapsed/onboard metrics, source provenance and indicative fare data.
- **Timetable / DepartureInfo**: Date-specific, bounded/paginated exact departures for a PassengerLeg. Each exact ride has independent departure/arrival platform values and provenance states. `complete`/`next_cursor` describe the fetched candidate batch; universal daily coverage is not guaranteed.
- **Movement (Entity)**: The final chosen itinerary, combining a `Route` with the user's `Search Context` (date, time). This is the entity saved to Notion.

## Architecture Decision Records (ADR)
1. **Clean Architecture & Ports/Adapters**
   - *Decision*: Decouple all external dependencies (Scrapers, Cache, Notion) via Interfaces (Ports).
   - *Reason*: Ensures business logic is testable via `FakeScraperAdapter` or `FakeNotionAdapter` without hitting real networks. Prevents external HTML/API changes from breaking the core domain.
2. **Scraper Pipeline (Scraper -> Parser -> Intermediate Model -> Builder)**
   - *Decision*: Introduce an `Intermediate Model` between the raw HTML parser and the Domain builder.
   - *Reason*: Web scraping targets change frequently. Isolating raw data extraction from Domain instantiation ensures that if a site redesigns its UI, only the Parser/Intermediate Model needs updating.
3. **Notion Mapper Responsibility**
   - *Decision*: A dedicated `NotionMapper` translates `Movement` into Notion properties.
   - *Reason*: Keeps Notion property construction outside Domain. It maps verified selections and omits unconfirmed exact fares; it does not generate weekday-checkbox properties from search modes.
4. **SQLite + Memory Cache over Redis**
   - *Decision*: A StationRepositoryPort provides the seeded SQLite station catalogue. CachePort has replaceable memory and SQLite adapters for route/timetable runtime data.
   - *Reason*: Supports local development and deterministic tests without requiring Redis.

## Clean Architecture
The dependency rule points inward:
`Infrastructure (HTTP, DB, Scraper)` -> `Application (Service, Ports)` -> `Domain (Entities)`

## Ports & Adapters
- **Ports**: Located in the Application layer (e.g., `ScraperPort`, `NotionPort`, `CachePort`).
- **Adapters**: Located in the Infrastructure layer (e.g., `YahooScraperAdapter`, `NotionAPIAdapter`, `FakeScraperAdapter`).
FastAPI's dependency injection binds Adapters to Ports at runtime.

## Directory Structure
```text
backend/
├── api/             # FastAPI Routers (HTTP logic)
├── application/     # Application Services, SearchModeResolver, Ports
├── domain/          # Pure Domain Entities & DTOs
├── infrastructure/
│   ├── adapters/    # Real Scraper, Notion, Cache implementations
│   ├── repositories/ # Seeded station/bus catalogue access
│   ├── cache/       # SQLite runtime cache
│   ├── scrapers/    # Provider HTTP and parsing
│   ├── fakes/       # Fakes for Unit Testing
│   └── notion/      # Notion API Client & Mapper
└── tests/           # unit/, integration/, regression/, opt-in e2e/

frontend/
├── src/
│   ├── api/         # Fetch client, API contracts and TypeScript types
│   ├── components/  # Search, route detail, PassengerLeg timetable and UI elements
│   ├── hooks/       # Custom React Hooks
│   └── utils/       # Chronology, display and itinerary calculations
```

## API Design
- `GET /api/v1/stations/search?q={keyword}`: Station autocomplete.
- `GET /api/v1/search`: Explicit departure date/time and selected station IDs; returns route families.
- `GET /api/v1/routes/{id}/legs/{index}/timetable`: Exact-date PassengerLeg lookup with bounded pagination and optional continuation boundary.
- `GET /api/v1/routes/{id}/timetable`: Retained route-level compatibility endpoint.
- `POST /api/v1/movements`: Server-validates cached exact selections, station topology and chronology before Notion persistence.

## Scraper Pipeline
To support future multi-scraper capabilities without polluting the domain:
1. **Scraper**: Fetches raw HTML.
2. **Parser**: Extracts data using BeautifulSoup.
3. **Intermediate Model (DTO)**: Represents the site-specific data structure.
4. **Builder (Normalizer)**: Converts the Intermediate Model into the standard pure `Route` domain.

## Cache Strategy
- **Stations**: Public CSV seeds a replaceable SQLite repository; local DB files are not source data.
- **Runtime cache**: Route search uses configured TTL (default 3600 seconds). Exact-leg timetables/options and official HTML currently use 3600 seconds.
- **Identity**: Search keys use selected station IDs/date/time; leg keys include both endpoint identities, service, lookup date, cursor and chronology boundary.
- **Provenance changes**: Leg-timetable v10 / exact-option v3 avoid trusting older missing-platform results. Expired selections require reloading.
Runtime cache is accessed through CachePort; application tests use fresh fake or temporary SQLite caches.

## Notion Integration
MovementService overwrites client-supplied train, time, platform, source and fare claims using cached exact departures. A single ride saves one parent; transfer journeys use PassengerLeg children. Only NotionMapper builds Notion properties. The existing Platform property stays numeric. Missing/text departure platforms and arrival-platform information use the existing time rich-text fields, distinguishing official omission, fallback-source omission and lookup failure without adding Notion columns.

## Frontend Architecture
- **Framework**: React + TypeScript + Vite.
- **Data fetching**: TanStack Query, fetch API client and React hooks.
- **UI**: Existing search, route timeline and exact-selection panels; no current Leaflet or Zustand dependency.

## State Management
- React state/props carry station selection, selected Route and per-leg exact departures. Query keys preserve date/identity context.
- Changing an earlier exact ride invalidates downstream selections. Full dated chronology is checked again on the server.

## Current limits
Exact operator fare calculation and arrival-time-based route search are not implemented. Some operators use Yahoo fallback. Discovery is bounded; unsupported/provider-error states are explicit. Platform data may be omitted by the source or fail extraction; it is never fabricated. Interactive mapping remains future work. Tests cover these contracts without claiming complete Japanese railway coverage or 100% code coverage.
