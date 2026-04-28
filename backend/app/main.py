import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.api import api_router
from app.config.settings import settings
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.core.rate_limit import limiter
from app.models import create_tables

configure_logging()
logger = logging.getLogger("inventai.startup")

app = FastAPI(
    title="InventAI API",
    description="Inventory intelligence for Indian retail stores",
    version=settings.APP_VERSION,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    allow_credentials=True,
    max_age=3600,
)
app.include_router(api_router, prefix=settings.API_PREFIX)


def prepare_database() -> None:
    alembic_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    create_tables()


@app.on_event("startup")
async def startup() -> None:
    try:
        prepare_database()
    except Exception:
        logger.exception("database_startup_failed")
        raise


@app.get("/")
async def root():
    return {"message": "InventAI API", "docs": "/docs", "health": f"{settings.API_PREFIX}/health"}
