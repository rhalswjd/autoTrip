from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from application.ports.notion_port import NotionException
from application.ports.scraper_port import ScraperException

class DomainException(Exception):
    """Base exception for Domain logic errors."""
    pass

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException):
        return JSONResponse(status_code=400, content={"detail": str(exc)})
        
    @app.exception_handler(NotionException)
    async def notion_exception_handler(request: Request, exc: NotionException):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(ScraperException)
    async def scraper_exception_handler(request: Request, exc: ScraperException):
        return JSONResponse(status_code=502, content={"detail": str(exc)})
