from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models import create_tables, get_db

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    return {
        "status": "ok" if db_connected else "degraded",
        "db_connected": db_connected,
        "background_tasks": "enabled",
        "version": settings.APP_VERSION,
    }


@router.post("/init-db")
def init_db(x_admin_token: str | None = Header(default=None)):
    if x_admin_token != settings.ADMIN_INIT_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
    create_tables()
    return {"success": True, "message": "Database tables created"}
