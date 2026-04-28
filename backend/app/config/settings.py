from functools import lru_cache
from typing import List, Optional
import warnings

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    APP_NAME: str = "InventAI"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS_RAW: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,https://your-vercel-app.vercel.app",
        alias="ALLOWED_ORIGINS",
    )

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/inventai"

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ADMIN_INIT_TOKEN: str = "inventai-admin-token"
    ENCRYPTION_KEY: str = "change-me-change-me-change-me-change!!"

    DEFAULT_FORECAST_HORIZON: int = 7
    MIN_DATA_DAYS_ARIMA: int = 60
    MIN_DATA_DAYS_MOVING_AVG: int = 30
    SAFETY_STOCK_MULTIPLIER: float = 1.2
    MAX_UPLOAD_FILE_SIZE_BYTES: int = 5 * 1024 * 1024

    OGD_INDIA_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    @computed_field
    @property
    def allowed_origins(self) -> List[str]:
        origins = [origin.strip() for origin in self.ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.APP_ENV.lower() != "production":
            return self

        insecure_values = {
            "JWT_SECRET_KEY": "change-me-in-production",
            "ENCRYPTION_KEY": "change-me-change-me-change-me-change!!",
            "ADMIN_INIT_TOKEN": "inventai-admin-token",
        }
        for field_name, insecure_value in insecure_values.items():
            if getattr(self, field_name) == insecure_value:
                warnings.warn(
                    f"{field_name} is using an insecure default value in production.",
                    RuntimeWarning,
                    stacklevel=2,
                )

        if "*" in self.allowed_origins:
            warnings.warn(
                "ALLOWED_ORIGINS includes '*', which is unsafe in production.",
                RuntimeWarning,
                stacklevel=2,
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
