from app.core.auth import create_access_token
from jose import jwt

from app.config.settings import settings


def test_create_access_token_embeds_subject():
    token = create_access_token("user@example.com")
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == "user@example.com"
