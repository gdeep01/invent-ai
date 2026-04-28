import sys
print("=== Starting import sequence ===", flush=True)

try:
    import logging
    import traceback
    from pathlib import Path
    print("stdlib OK", flush=True)
except Exception as e:
    print(f"stdlib FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from alembic import command
    from alembic.config import Config
    print("alembic OK", flush=True)
except Exception as e:
    print(f"alembic FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    print("fastapi OK", flush=True)
except Exception as e:
    print(f"fastapi FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    print("slowapi OK", flush=True)
except Exception as e:
    print(f"slowapi FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from app.core.auth import get_current_user
    print("auth OK", flush=True)
except Exception as e:
    print(f"auth FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from app.models import Base
    print("models OK", flush=True)
except Exception as e:
    print(f"models FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from app.api.routers import forecast, products, auth, reorder, ai
    print("routers OK", flush=True)
except Exception as e:
    print(f"routers FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from app.api import api_router
    print("api router OK", flush=True)
except Exception as e:
    print(f"api router FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from app.config.settings import settings
    print("settings OK", flush=True)
except Exception as e:
    print(f"settings FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from app.core.logging import RequestLoggingMiddleware, configure_logging
    print("logging middleware OK", flush=True)
except Exception as e:
    print(f"logging middleware FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from app.core.rate_limit import limiter
    print("rate limit OK", flush=True)
except Exception as e:
    print(f"rate limit FAILED: {e}", flush=True)
    sys.exit(1)

try:
    from app.models import create_tables
    print("create_tables OK", flush=True)
except Exception as e:
    print(f"create_tables FAILED: {e}", flush=True)
    sys.exit(1)

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
    except Exception as exc:
        traceback.print_exc()
        logger.exception("database_startup_failed")
        raise exc


@app.get("/")
async def root():
    return {"message": "InventAI API", "docs": "/docs", "health": f"{settings.API_PREFIX}/health"}
