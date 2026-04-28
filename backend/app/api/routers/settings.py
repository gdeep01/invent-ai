from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.security import encrypt_value
from app.models import FestivalMultiplier, User, UserSettings, get_db
from app.schemas import FestivalResponse, UserSettingsResponse, UserSettingsUpdate
from app.services.festivals import FestivalService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=UserSettingsResponse)
def get_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings_row = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    multipliers = []
    if settings_row:
        multipliers = [{"category": row.category, "multiplier": row.multiplier} for row in settings_row.festival_multipliers]
    return UserSettingsResponse(
        has_gemini_api_key=bool(settings_row and settings_row.encrypted_gemini_api_key),
        notification_threshold_days=settings_row.notification_threshold_days if settings_row else 7,
        festival_multipliers=multipliers,
    )


@router.put("", response_model=UserSettingsResponse)
def update_settings(payload: UserSettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings_row = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings_row:
        settings_row = UserSettings(user_id=current_user.id)
        db.add(settings_row)
        db.flush()

    if payload.gemini_api_key is not None:
        settings_row.encrypted_gemini_api_key = encrypt_value(payload.gemini_api_key) if payload.gemini_api_key else None
    settings_row.notification_threshold_days = payload.notification_threshold_days
    db.query(FestivalMultiplier).filter(FestivalMultiplier.settings_id == settings_row.id).delete(synchronize_session=False)
    for item in payload.festival_multipliers:
        db.add(FestivalMultiplier(settings_id=settings_row.id, category=item.category, multiplier=item.multiplier))
    db.commit()
    return get_settings(current_user, db)


@router.get("/festivals", response_model=list[FestivalResponse])
def list_festivals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return FestivalService(db).get_all_festivals()


@router.post("/festivals/seed")
def seed_festivals(year: int = 2026, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = FestivalService(db).seed_default_festivals(year)
    return {"success": True, "festivals_added": count, "year": year}
