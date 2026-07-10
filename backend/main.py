from fastapi import FastAPI
from core.config import settings
from core.logger import logger
from core.exceptions import setup_exception_handlers
from api.v1.health import router as health_router
from api.v1.search import router as search_router
from api.v1.timetable import router as timetable_router
from api.v1.movements import router as movements_router
from api.v1.stations import router as stations_router

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

    return app

app = create_app()
