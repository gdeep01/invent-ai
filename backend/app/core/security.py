import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import settings


def _build_fernet() -> Fernet:
    digest = hashlib.sha256(settings.ENCRYPTION_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


fernet = _build_fernet()


def encrypt_value(value: str) -> str:
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
