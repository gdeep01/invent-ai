from fastapi.middleware.cors import CORSMiddleware

from app.main import app


def test_cors_configuration_is_restricted():
    cors_middleware = next(
        middleware for middleware in app.user_middleware if middleware.cls is CORSMiddleware
    )

    assert cors_middleware.kwargs["allow_methods"] == ["GET", "POST", "PUT", "OPTIONS"]
    assert cors_middleware.kwargs["allow_headers"] == ["Authorization", "Content-Type", "Accept"]
    assert cors_middleware.kwargs["allow_credentials"] is True
    assert cors_middleware.kwargs["max_age"] == 3600
