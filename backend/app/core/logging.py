import logging
import time

from jose import jwt
from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.settings import settings


def configure_logging() -> None:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started_at = time.perf_counter()
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "", 1)
            try:
                payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                request.state.user_id = payload.get("sub")
            except Exception:
                request.state.user_id = None
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        request.state.duration_ms = duration_ms
        logging.getLogger("inventai.request").info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "user_id": getattr(request.state, "user_id", None),
                "duration_ms": duration_ms,
                "status_code": response.status_code,
            },
        )
        return response
