from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ForecastModel(enum.Enum):
    NAIVE = "naive"
    MOVING_AVERAGE = "moving_average"
    ARIMA = "arima"
    BASELINE = "baseline"


class UrgencyLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ForecastRunStatus(enum.Enum):
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    google_sub = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    avatar_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    stores = relationship("Store", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    encrypted_gemini_api_key = Column(Text)
    notification_threshold_days = Column(Integer, default=7, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="settings")
    festival_multipliers = relationship("FestivalMultiplier", back_populates="settings", cascade="all, delete-orphan")


class FestivalMultiplier(Base):
    __tablename__ = "festival_multipliers"

    id = Column(Integer, primary_key=True, index=True)
    settings_id = Column(Integer, ForeignKey("user_settings.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    multiplier = Column(Float, nullable=False, default=1.0)

    settings = relationship("UserSettings", back_populates="festival_multipliers")


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    store_id = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    location = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="stores")
    skus = relationship("SKU", back_populates="store", cascade="all, delete-orphan")
    sales = relationship("SalesTransaction", back_populates="store", cascade="all, delete-orphan")
    forecasts = relationship("ForecastResult", back_populates="store", cascade="all, delete-orphan")
    recommendations = relationship("ReorderRecommendation", back_populates="store", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="store", cascade="all, delete-orphan")
    forecast_runs = relationship("ForecastRun", back_populates="store", cascade="all, delete-orphan")


class SKU(Base):
    __tablename__ = "skus"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    sku_id = Column(String(50), nullable=False, index=True)
    sku_name = Column(String(300), nullable=False)
    category = Column(String(100))
    current_stock = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    store = relationship("Store", back_populates="skus")
    sales = relationship("SalesTransaction", back_populates="sku", cascade="all, delete-orphan")
    forecasts = relationship("ForecastResult", back_populates="sku", cascade="all, delete-orphan")
    recommendations = relationship("ReorderRecommendation", back_populates="sku", cascade="all, delete-orphan")


class SalesTransaction(Base):
    __tablename__ = "sales_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    units_sold = Column(Integer, nullable=False)
    price = Column(Float)
    discount = Column(Float)
    excluded_from_forecast = Column(Boolean, default=False, nullable=False)
    anomaly_note = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    store = relationship("Store", back_populates="sales")
    sku = relationship("SKU", back_populates="sales")


class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    task_id = Column(String(100), unique=True, nullable=False, index=True)
    horizon = Column(Integer, nullable=False)
    status = Column(String(20), default=ForecastRunStatus.PENDING.value, nullable=False, index=True)
    model_used = Column(String(50))
    mae_score = Column(Float)
    summary = Column(Text)
    error_message = Column(Text)
    festival_boost_applied = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)

    store = relationship("Store", back_populates="forecast_runs")
    forecast_results = relationship("ForecastResult", back_populates="forecast_run")


class ForecastResult(Base):
    __tablename__ = "forecast_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False, index=True)
    forecast_run_id = Column(Integer, ForeignKey("forecast_runs.id"), index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    predicted_units = Column(Float, nullable=False)
    confidence_lower = Column(Float)
    confidence_upper = Column(Float)
    model_used = Column(String(50), nullable=False)
    forecast_horizon = Column(Integer, nullable=False)
    health_score = Column(Float)
    forecast_confidence = Column(Float)
    festival_boost_applied = Column(Boolean, default=False, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    store = relationship("Store", back_populates="forecasts")
    sku = relationship("SKU", back_populates="forecasts")
    forecast_run = relationship("ForecastRun", back_populates="forecast_results")


class ReorderRecommendation(Base):
    __tablename__ = "reorder_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False, index=True)
    reorder_qty = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    urgency = Column(String(20), nullable=False, index=True)
    forecasted_demand = Column(Float)
    current_stock = Column(Integer)
    safety_stock = Column(Integer)
    velocity_change_pct = Column(Float)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    store = relationship("Store", back_populates="recommendations")
    sku = relationship("SKU", back_populates="recommendations")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), index=True)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    is_dismissed = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    store = relationship("Store", back_populates="alerts")


class Festival(Base):
    __tablename__ = "festivals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    date = Column(Date, nullable=False, index=True)
    region = Column(String(100))
    impact_multiplier = Column(Float, default=1.5, nullable=False)
    category = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
