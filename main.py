# main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from core.search_api.routes import router as search_router
from core.search_api.settings import Settings
from core.middleware.cache import SearchCacheMiddleware
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app
    Handles startup and shutdown events
    """
    # Load settings
    settings = Settings()
    
    # Log configuration on startup
    logger.info(f"Starting application with settings: {settings.dict()}")
    
    try:
        yield
    finally:
        logger.info("Shutting down application")

app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(search_router, prefix="")
app.add_middleware(SearchCacheMiddleware)

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=2345,
        reload=True
    )
