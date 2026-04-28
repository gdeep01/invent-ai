from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.models import Alert, User, get_db
from app.schemas import AlertResponse

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AlertResponse])
def list_alerts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Alert)
        .filter(Alert.user_id == current_user.id, Alert.is_dismissed.is_(False))
        .order_by(Alert.created_at.desc())
        .all()
    )


@router.post("/{alert_id}/dismiss")
def dismiss_alert(alert_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.user_id == current_user.id, Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_dismissed = True
    db.commit()
    return {"success": True}
