# AutoTrip v1.0.0

We are excited to announce the initial release of AutoTrip v1.0.0! AutoTrip is a macOS utility-style application designed to search and organize Japanese train routes and timetables directly into your Notion workspace.

## Highlights
- **macOS Utility App UX**: High density, clean interface inspired by Raycast, Notion Desktop, and Apple Maps.
- **End-to-End Flow**: Search stations, view routes, check timetables, and add them seamlessly to Notion.
- **Robust Infrastructure**: Custom-built accessible UI primitives (Modal, Toast, Tooltip, Portal) without heavy component libraries.

## Features
- **Station Search**: Find stations across Japan with bilingual support (English/Japanese) and Midori no Madoguchi info.
- **Route Search**: Find direct or transfer routes between stations with duration, fare, and transfer details.
- **Route Timeline**: Visualize routes beautifully using an Apple Maps-like timeline view.
- **Timetable**: Check precise departure and arrival times for any given route.
- **Movement Creation**: Automatically create trip movement entries in a linked Notion Database with a single click.

## Architecture
- **Frontend**: Clean Architecture separation (`api/`, `hooks/`, `components/ui`, `components/domain`). Fully separated View and Business Logic.
- **Backend**: FastAPI with robust Clean Architecture (`Domain`, `Usecase`, `Repository`, `Router`).
- **State Management**: Zero global state libraries. Only React `useState`, `useContext`, and `Tanstack Query`.

## Tech Stack
- **Frontend**: React 18, TypeScript, Vite, Tanstack Query, Vanilla CSS (Semantic Tokens).
- **Backend**: Python 3.12, FastAPI, SQLAlchemy, SQLite.
- **Deployment**: Docker Compose.

## Known Limitations
- Search results currently use mock data/external proxies for demonstration. Real-time API integration may require additional external API keys.
- Requires manual Notion API Key and Database setup to fully utilize the Movement Creation feature.

## Future Work
- Integration with live Japanese Transit APIs.
- Saving favorite stations and routes locally.
- Advanced Notion synchronization features.
