# AutoTrip

A macOS utility-style application for searching Japanese train routes and seamlessly organizing them into your Notion workspace.

<!-- ![AutoTrip Search](docs/images/search.png) - Coming Soon -->

## Features

- **Station Search**: Quickly find stations with real-time feedback and keyword support. (Note: Currently uses local seeded database)
- **Route Search**: Search explicit travel dates/times and compare route families, transfers and indicative fares. Real providers are enabled through local configuration.
- **Route Timeline**: View your journey in a clean, Apple Maps-inspired vertical timeline.
- **Timetable**: Browse date-specific exact departures, arrivals, available platforms and source links. JR West uses official JR Odekake data; other operators use Yahoo where supported. Non-JR sparse-service discovery remains bounded and is not guaranteed complete.
- **Movement Creation**: Save selected passenger legs to Notion when real Notion integration is explicitly enabled. Unknown exact fares/platforms are not guessed.
- **Notion Integration**: Bridge the gap between travel planning and workspace organization.

<!-- ![AutoTrip Timetable](docs/images/timetable.png) - Coming Soon -->

## Tech Stack

**Frontend**
- React 19 & TypeScript (Node.js 22.18+)
- Vite
- Vanilla CSS (Semantic Design Tokens)

**Backend**
- Python 3.12
- FastAPI
- SQLite

**State Management**
- React Query (Tanstack Query)
- React Built-in Hooks (useState, useContext)

**Deployment**
- Docker & Docker Compose

## Architecture

AutoTrip strictly follows **Clean Architecture** to maintain high cohesion and low coupling.

### Frontend 구조
- `api/`: API Call definitions and type declarations.
- `hooks/`: Custom hooks for state management and React Query.
- `components/ui/`: Reusable, generic UI primitives (Button, Modal, Toast).
- `components/domain/`: Domain-specific components (Search, Route, Timetable).
- `pages/`: Page containers handling structural layout.

### Backend 구조
- `domain/`: Core business entities and models.
- `application/`: Application business logic (Services and Ports).
- `infrastructure/`: Data access and external API integrations (Adapters, Repositories).
- `api/`: FastAPI endpoints (Routers).

```text
autoTrip/
├── backend/
│   ├── api/
│   ├── application/
│   ├── core/
│   ├── domain/
│   ├── infrastructure/
│   ├── tests/            # unit/, integration/, regression/, e2e/, data/
│   └── main.py
├── tools/               # read-only commit safety checker and its tests
├── .local/              # ignored local experiments/backups; never committed
└── frontend/
    ├── src/
    │   ├── api/
    │   ├── components/
    │   ├── hooks/
    │   ├── layouts/
    │   ├── pages/
    │   └── styles/
    └── package.json
```

## Getting Started

Follow these steps to run AutoTrip locally.

1. **Clone the repository**
   ```bash
   git clone https://github.com/<YOUR_GITHUB_REPOSITORY>/autotrip.git
   cd autotrip
   ```

2. **Frontend 설치**
   ```bash
   cd frontend
   npm install
   ```

3. **Backend 실행 (Docker)**
   ```bash
   cd ..
   test -e backend/.env || cp backend/.env.example backend/.env
   docker compose up -d
   ```

4. **Frontend 실행**
   ```bash
   cd frontend
   npm run dev
   ```

## Environment Variables

Copy the provided example environment file to configure your local setup.

```bash
cp .env.example .env
```

**`.env.example`**
```env
# Application
PORT=8000
ENVIRONMENT=development

# Database
DB_PATH=data/autotrip.db

# Notion API (Do not put actual tokens here)
NOTION_API_KEY=secret_your_notion_api_key_here
NOTION_DATABASE_ID=your_notion_database_id_here

# Enable real infrastructure adapters
USE_REAL_SCRAPER=false
USE_REAL_NOTION=false
USE_SQLITE_CACHE=false
```
> **Important:** Never commit the `.env` file containing actual sensitive credentials or API keys to the repository.

## Commit safety and local-only files

Run `python3 tools/check_commit_safety.py` before staging/committing; it inspects
working-tree candidates and staged changes without printing secret values.
Use `--history` for reachable-history review. It does not rewrite Git history and
is not a complete secret detector or dependency audit.

Run `python3 -m unittest discover -s tools/tests`, `pytest`, and frontend
`npm test && npm run build`. Run `npm audit` and a Python `pip-audit` separately
when checking current dependency advisories. See `backend/tests/README.md` for groups.

Keep environment files, tokens, private keys, runtime databases, provider dumps,
browser state and local investigation scripts out of Git and Docker images.
Only `.env.example` templates belong in Git. `.local/` preserves old investigations
and the retired virtual environment locally; it must not be force-added.

The application is for local development: Docker publishes the API on loopback,
and Vite restricts trusted hosts. Existing running services need restarting to
apply configuration changes. Internet deployment needs authentication and a
separate deployment security review; CORS is not authentication.

## API

Once the backend is running, you can access the following standard endpoints:

- **Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

## Screenshots

<!-- - **Route Details**: ![Routes](docs/images/routes.png) - Coming Soon -->
<!-- - **Movement Creation**: ![Movement](docs/images/movement.png) - Coming Soon -->

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
