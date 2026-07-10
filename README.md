# AutoTrip

AutoTrip is a personal railway travel planner for Japan. It helps users search for train routes, check timetables, and save their itineraries directly to Notion. Designed as a macOS companion app, it features a fast, minimal, and Apple HIG-inspired frontend.

## Architecture

AutoTrip strictly adheres to **Clean Architecture** principles:
- **Domain Layer**: Pure business rules and models (e.g., `Station`, `Movement`, `Route`). Has absolutely zero dependencies on frameworks or external libraries.
- **Application Layer**: Use cases and Ports (Interfaces) for external communication.
- **Infrastructure Layer**: Adapters that implement the Ports (e.g., `RealScraperAdapter`, `NotionAdapter`, `SQLiteCacheAdapter`).
- **Presentation Layer (API)**: FastAPI routers that handle HTTP requests and delegate to the Application Layer.

## Folder Structure

```
autoTrip/
├── backend/
│   ├── api/             # FastAPI Routers (Presentation Layer)
│   ├── application/     # Use Cases & Ports (Application Layer)
│   ├── core/            # Config, Exceptions, Logger
│   ├── domain/          # Pure Business Logic (Domain Layer)
│   ├── infrastructure/  # External APIs, DB, Scrapers (Infrastructure Layer)
│   └── tests/           # Pytest test suite
├── frontend/            # React + TypeScript + Vite Companion App
├── docker-compose.yml   # Docker Compose configuration
├── Dockerfile           # Backend Dockerfile
└── requirements.txt     # Backend Dependencies
```

## Running Locally (Without Docker)

### 1. Clone the Repository & Create a Virtual Environment
```bash
git clone https://github.com/username/autotrip.git
cd autotrip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables
Navigate to the `backend` directory, copy the example file, and fill in the required values (like Notion API key).
```bash
cd backend
cp .env.example .env
```

### 3. Run the Server
Start the Uvicorn server from the `backend` directory:
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Running with Docker & Docker Compose

For a consistent and isolated environment, run the backend using Docker Compose:

**Start the service in the background:**
```bash
docker compose up --build -d
```

**Check the status:**
```bash
docker compose ps
```

**View logs in real-time:**
```bash
docker compose logs -f backend
```

**Stop and remove containers:**
```bash
docker compose down
```

## Testing

The project uses `pytest` for all unit and integration tests. To run the tests, execute from the project root:

```bash
pytest
```
*Note: The GitHub Actions CI pipeline automatically runs these tests on every push.*

## API Documentation (Swagger/OpenAPI)

When the backend is running, FastAPI provides automatic interactive documentation:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Test endpoints, view schemas)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) (Detailed specification layout)

## License

This project is licensed under the MIT License.
