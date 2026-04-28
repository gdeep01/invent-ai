from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import httpx
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.auth import create_access_token, get_current_user
from app.models import User, UserSettings, get_db
from app.schemas import AuthUserResponse, GoogleAuthRequest, TokenResponse

router = APIRouter()


def _serialize_user(user: User) -> AuthUserResponse:
    return AuthUserResponse(id=user.id, email=user.email, name=user.name, avatar_url=user.avatar_url)


@router.post("/google", response_model=TokenResponse)
def google_auth(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not configured")

    token_info = None
    try:
        token_info = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception:
        try:
            userinfo_response = httpx.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {payload.credential}"},
                timeout=10.0,
            )
            userinfo_response.raise_for_status()
            token_info = userinfo_response.json()
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google credential") from exc

    email = token_info.get("email")
    google_sub = token_info.get("sub")
    if not email or not google_sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google account payload is incomplete")

    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        user = User(
            email=email.lower(),
            google_sub=google_sub,
            name=token_info.get("name"),
            avatar_url=token_info.get("picture"),
        )
        db.add(user)
        db.flush()
        db.add(UserSettings(user_id=user.id))
    else:
        user.google_sub = google_sub
        user.name = token_info.get("name") or user.name
        user.avatar_url = token_info.get("picture") or user.avatar_url

    db.commit()
    db.refresh(user)
    token = create_access_token(user.email)
    return TokenResponse(access_token=token, user=_serialize_user(user))


@router.get("/me", response_model=AuthUserResponse)
def me(current_user: User = Depends(get_current_user)):
    return _serialize_user(current_user)
