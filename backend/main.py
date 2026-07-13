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
        import sys
        import sqlite3
        
        def setup_db(db_path: str, csv_path: str, script_path: str, table_name: str, name: str):
            is_valid = False
            if os.path.exists(db_path):
                try:
                    with sqlite3.connect(db_path) as conn:
                        cursor = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                        if cursor.fetchone():
                            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                            if count > 0:
                                is_valid = True
                except Exception as e:
                    logger.error(f"Failed to validate {db_path}: {e}")
            
            if not is_valid:
                logger.info(f"{name} DB is missing, empty, or corrupted. Seeding from CSV...")
                if os.path.exists(db_path):
                    try:
                        os.remove(db_path)
                    except OSError:
                        pass
                try:
                    # Note: seed_poi_db doesn't take args in our impl, so we call it directly or run it as script
                    if "poi" in name.lower():
                        subprocess.run([sys.executable, script_path], check=True, cwd=os.path.dirname(os.path.dirname(__file__)))
                    else:
                        subprocess.run([sys.executable, script_path, "--csv", csv_path, "--db", db_path], check=True, cwd=os.path.dirname(os.path.dirname(__file__)))
                    logger.info(f"{name} Database seeding completed successfully.")
                except Exception as e:
                    logger.error(f"Failed to seed {name} database: {e}")
            else:
                logger.info(f"{name} DB is valid and ready.")

        # Station DB
        station_db = settings.sqlite_station_db_path
        station_csv = os.path.join(os.path.dirname(__file__), "data", "station.csv")
        station_script = os.path.join(os.path.dirname(__file__), "scripts", "seed_station_db.py")
        setup_db(station_db, station_csv, station_script, "stations", "Station")

        # Bus Stop DB
        bus_db = settings.bus_stop_db_path
        bus_csv = os.path.join(os.path.dirname(__file__), "data", "bus_stop.csv")
        bus_script = os.path.join(os.path.dirname(__file__), "scripts", "seed_bus_stop_db.py")
        if os.path.exists(bus_csv):
            setup_db(bus_db, bus_csv, bus_script, "bus_stops", "Bus Stop")
            
        # POI DB
        poi_db = settings.poi_db_path
        poi_csv = os.path.join(os.path.dirname(__file__), "data", "poi.csv")
        poi_script = os.path.join(os.path.dirname(__file__), "scripts", "seed_poi_db.py")
        if os.path.exists(poi_csv):
            setup_db(poi_db, poi_csv, poi_script, "pois", "POI")

    return app

app = create_app()
