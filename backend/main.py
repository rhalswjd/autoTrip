from fastapi import FastAPI
from core.config import settings
from core.logger import logger
from core.exceptions import setup_exception_handlers
from api.v1.health import router as health_router
from api.v1.search import router as search_router
from api.v1.timetable import router as timetable_router
from api.v1.movements import router as movements_router
from api.v1.stations import router as stations_router

from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="A Personal Railway Travel Planner for Japan. Integrates with JR Odekake and Notion.",
        version="1.0.0",
        contact={
            "name": "AutoTrip Developer",
            "url": "https://github.com/autotrip",
            "email": "dev@autotrip.local",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        debug=settings.debug
    )

    if settings.backend_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.backend_cors_origins],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register Exception Handlers
    setup_exception_handlers(app)

    # Register Routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(timetable_router, prefix="/api/v1")
    app.include_router(movements_router, prefix="/api/v1")
    app.include_router(stations_router, prefix="/api/v1")

    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.app_name} in {settings.environment} mode.")
        import os
        import subprocess
        import sqlite3
        
        db_path = settings.sqlite_station_db_path
        csv_path = os.path.join(os.path.dirname(__file__), "data", "station.csv")
        script_path = os.path.join(os.path.dirname(__file__), "scripts", "seed_station_db.py")

        def check_db_valid() -> bool:
            if not os.path.exists(db_path):
                return False
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stations'")
                    if not cursor.fetchone():
                        return False
                    cursor.execute("SELECT COUNT(*) FROM stations")
                    count = cursor.fetchone()[0]
                    return count > 0
            except (sqlite3.OperationalError, sqlite3.DatabaseError):
                return False

        if not check_db_valid():
            logger.info("Station DB is missing, empty, or corrupted. Seeding from CSV...")
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except OSError:
                    pass
            try:
                subprocess.run(["python", script_path, "--csv", csv_path, "--db", db_path], check=True)
                if check_db_valid():
                    logger.info("Database seeding and verification completed successfully.")
                else:
                    logger.error("Database seeding completed, but verification failed.")
            except Exception as e:
                logger.error(f"Failed to seed database: {e}")
        else:
            logger.info("Station DB is valid and ready.")

    return app

app = create_app()
