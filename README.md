# AutoTrip

A macOS utility-style application for searching Japanese train routes and seamlessly organizing them into your Notion workspace.

<!-- ![AutoTrip Search](docs/images/search.png) - Coming Soon -->

## Features

- **Station Search**: Quickly find stations with real-time feedback and keyword support. (Note: Currently uses local seeded database)
- **Route Search**: Find the best transit options with transfer counts and fare details. (Note: Currently returns mock/stub data for demonstration)
- **Route Timeline**: View your journey in a clean, Apple Maps-inspired vertical timeline.
- **Timetable**: Browse all departure and arrival schedules for selected routes. (Note: Currently returns mock/stub data for demonstration)
- **Movement Creation**: Automatically generate trip logs directly in your Notion database. (Note: Currently returns a stub response without making actual Notion API calls)
- **Notion Integration**: Bridge the gap between travel planning and workspace organization.

<!-- ![AutoTrip Timetable](docs/images/timetable.png) - Coming Soon -->

## Tech Stack

**Frontend**
- React 18 & TypeScript
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
│   ├── tests/
│   └── main.py
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
```
> **Important:** Never commit the `.env` file containing actual sensitive credentials or API keys to the repository.

## API

Once the backend is running, you can access the following standard endpoints:

- **Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

## Screenshots

<!-- - **Route Details**: ![Routes](docs/images/routes.png) - Coming Soon -->
<!-- - **Movement Creation**: ![Movement](docs/images/movement.png) - Coming Soon -->

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
