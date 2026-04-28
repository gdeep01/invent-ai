from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class AuthUserResponse(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


class GoogleAuthRequest(BaseModel):
    credential: str = Field(..., min_length=1)


class FestivalMultiplierSchema(BaseModel):
    category: str
    multiplier: float = Field(..., ge=0.1, le=5.0)


class UserSettingsResponse(BaseModel):
    has_gemini_api_key: bool
    notification_threshold_days: int
    festival_multipliers: List[FestivalMultiplierSchema] = []


class UserSettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    notification_threshold_days: int = Field(default=7, ge=1, le=60)
    festival_multipliers: List[FestivalMultiplierSchema] = []


class SalesRowSchema(BaseModel):
    store_id: str = Field(..., min_length=1, max_length=50)
    sku_id: str = Field(..., min_length=1, max_length=50)
    sku_name: str = Field(default="Unknown", min_length=1, max_length=300)
    date: date
    units_sold: int = Field(..., ge=0)
    price: Optional[float] = Field(None, ge=0)
    discount: Optional[float] = Field(None, ge=0, le=100)
    category: Optional[str] = None

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, value):
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return value


class CSVMappingSuggestion(BaseModel):
    mapping: dict[str, str]
    missing_columns: List[str] = []
    used_ai: bool = False
    note: Optional[str] = None


class UploadAnomaly(BaseModel):
    row_index: int
    sku_name: str
    date: date
    units_sold: float
    note: str


class CSVPreviewResponse(BaseModel):
    success: bool
    suggestion: CSVMappingSuggestion
    sample_columns: List[str]
    anomalies: List[UploadAnomaly] = []


class CSVUploadResponse(BaseModel):
    success: bool
    rows_processed: int
    rows_failed: int
    errors: List[str] = []
    store_id: Optional[str] = None
    anomalies: List[UploadAnomaly] = []


class StoreResponse(BaseModel):
    id: int
    store_id: str
    name: str
    location: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SKUResponse(BaseModel):
    id: int
    sku_id: str
    sku_name: str
    category: Optional[str]
    current_stock: int

    class Config:
        from_attributes = True


class StockUpdateRequest(BaseModel):
    sku_id: str
    current_stock: int = Field(..., ge=0)


class ForecastRequest(BaseModel):
    store_id: str
    sku_ids: Optional[List[str]] = None
    horizon: int = Field(default=7, ge=1, le=30)
    model: str = Field(default="arima")


class ForecastResultSchema(BaseModel):
    sku_id: str
    sku_name: str
    forecast_date: date
    predicted_units: float
    confidence_lower: Optional[float]
    confidence_upper: Optional[float]
    model_used: str
    health_score: Optional[float] = None
    festival_boost_applied: bool = False


class ForecastResponse(BaseModel):
    store_id: str
    horizon: int
    generated_at: datetime
    total_predicted: float
    forecasts: List[ForecastResultSchema]
    insights: List[str] = []
    mae_score: Optional[float] = None
    last_run_at: Optional[datetime] = None


class ForecastTaskResponse(BaseModel):
    success: bool
    task_id: str
    status: str
    forecast_run_id: int


class ForecastTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    error_message: Optional[str] = None
    result: Optional[dict] = None


class ReorderItem(BaseModel):
    sku_id: str
    sku_name: str
    reorder_qty: int
    reason: str
    urgency: str
    forecasted_demand: float
    current_stock: int
    velocity_change_pct: Optional[float] = None


class ReorderListResponse(BaseModel):
    store_id: str
    store_name: str
    generated_at: datetime
    total_items: int
    critical_items: int
    items: List[ReorderItem]


class ReorderSummary(BaseModel):
    total_items: int
    critical: int
    high: int
    medium: int
    low: int
    estimated_value: Optional[float] = None


class AlertResponse(BaseModel):
    id: int
    message: str
    severity: str
    is_dismissed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FestivalResponse(BaseModel):
    id: int
    name: str
    date: date
    region: Optional[str]
    impact_multiplier: float
    category: Optional[str]

    class Config:
        from_attributes = True


class AIChatMessage(BaseModel):
    role: str
    content: str


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_history: List[AIChatMessage] = []
