# AutoTrip Architecture Document

## Project Overview
AutoTrip is a personal railway travel planner for Japan, designed for local macOS environments. The system automates searching for train routes, visualizing them on an interactive map, and saving the final selected journeys directly into Notion as an itinerary management database.

## Requirements
- **MVP Focus**: Simplify domains to focus purely on the search, selection, and save flow (`SearchRequest` -> `Route` -> `Timetable` -> `Movement`).
- **Auto SearchMode Resolution**: The backend must automatically determine the search workflow (Case 1, 2, or 3) based on the presence of optional `time` and `date` parameters.
- **Data Purity**: The Domain layer (`Route`) must represent physical train paths only, devoid of any external system logic (e.g., Notion properties).
- **Testability**: Must implement Dependency Inversion (Ports & Adapters) so the core application can be tested using Fakes (without HTTP, Scraper, or Notion API).
- **UX**: Google Maps-like interactive UX with a synchronized Map, Route List, Detail Panel, and Journey Timeline.

## Domain Model
The Domain layer contains pure business objects with no dependencies on infrastructure or frameworks.

- **SearchRequest (DTO)**: Represents user input (`departure`, `arrival`, `time`, `date`). Contains no logic.
- **Route (Entity)**: Represents a physical train path. Contains a unique `id`, line names, durations, fares, transfer counts, and `polyline` coordinates. 
- **Timetable (Entity)**: Contains the full schedule (first to last train) bound to a specific `Route` ID.
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
   - *Reason*: Keeps the `Route` domain pure. The Mapper dynamically generates Notion's `Checkbox` (for general weekdays) or `Select` (for specific dates) based on the `Search Context`.
4. **SQLite + Memory Cache over Redis**
   - *Decision*: Use SQLite for persistent cache (Stations) and In-Memory for ephemeral cache.
   - *Reason*: Avoids the operational overhead of running Docker/Redis for a local personal project. 

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
│   ├── database/    # SQLite integration
│   ├── fakes/       # Fakes for Unit Testing
│   └── notion/      # Notion API Client & Mapper
└── tests/           # Unit and Integration Tests

frontend/
├── src/
│   ├── api/         # Axios clients
│   ├── components/  # Map, RouteList, JourneyTimeline, DetailPanel
│   ├── domain/      # Frontend Types/Interfaces
│   ├── hooks/       # Custom React Hooks
│   └── store/       # Zustand State Management
```

## API Design
- `GET /api/v1/stations/search?q={keyword}`: Station autocomplete.
- `GET /api/v1/search`: Accepts `SearchRequest` DTO. Automatically resolves mode. Returns `List[Route]`.
- `GET /api/v1/routes/{id}/timetable`: Fetches timetable for a specific route.
- `POST /api/v1/notion/movements`: Accepts Route ID & context, saves to Notion.

## Scraper Pipeline
To support future multi-scraper capabilities without polluting the domain:
1. **Scraper**: Fetches raw HTML.
2. **Parser**: Extracts data using BeautifulSoup.
3. **Intermediate Model (DTO)**: Represents the site-specific data structure.
4. **Builder (Normalizer)**: Converts the Intermediate Model into the standard pure `Route` domain.

## Cache Strategy
- **Stations**: Infinite/Long TTL (backed by SQLite).
- **Timetables**: 7-day TTL (backed by SQLite/Memory).
- **Route Search**: 1-day or 1-hour TTL (In-Memory).
Cache is accessed strictly via `CachePort`.

## Notion Integration
The Application Service passes a `Movement` entity to the `NotionPort`. The concrete `NotionAdapter` delegates to the `NotionMapper`, which generates a Notion API-compliant JSON payload (dynamically applying Weekday/Weekend vs. Normal Operation statuses based on the date context).

## Frontend Architecture
- **Framework**: React + TypeScript + Vite.
- **Map**: React-Leaflet for dynamic polyline and marker rendering.
- **UX**: Fully responsive. Loading states use Skeleton UIs. Search inputs retain state via Zustand.

## State Management
- **Zustand** is used for global state.
- **Stores**: `SearchStore` (input params), `RouteStore` (selected route), `MapStore` (map coordinates/zoom).
- The `RouteList`, `Journey Timeline`, `Detail Panel`, and `Map` components all subscribe to the selected route state to update simultaneously.

## Development Roadmap
1. **Phase 1**: Define Domain Models, Application Services, Ports, and Fake Adapters. Achieve 100% test coverage for business logic (Backend TDD).
2. **Phase 2**: Implement Real Infrastructure Adapters (Scraper Pipeline, SQLite, Notion API).
3. **Phase 3**: Develop Frontend Map, Journey Timeline, and Zustand state synchronization.
4. **Phase 4**: End-to-End Integration, Error Handling polish, and Final MVP delivery.
