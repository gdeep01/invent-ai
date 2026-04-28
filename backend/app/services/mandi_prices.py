"""
Mandi price integration service.

Fetches commodity prices from the Open Government Data (OGD) Platform India
dataset backed by AGMARKNET.
"""

from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MandiPriceService:
    """
    Service for fetching commodity price data from OGD India / AGMARKNET.

    Dataset:
    https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi
    """

    BASE_URL = "https://api.data.gov.in/resource/9ef2731d-91d2-4581-adbc-a24ad7373c04"
    DEFAULT_LIMIT = 10
    MAX_LIMIT = 100
    REQUEST_TIMEOUT_SECONDS = 12

    def __init__(self, api_key: Optional[str] = None):
        configured_key = api_key or getattr(settings, "OGD_INDIA_API_KEY", None) or self._read_env_file_api_key()
        self.api_key = configured_key.strip() if isinstance(configured_key, str) and configured_key.strip() else None

    def get_latest_prices(
        self,
        commodity: Optional[str] = None,
        state: Optional[str] = None,
        market: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> List[Dict[str, Any]]:
        return self.fetch_latest_prices(
            commodity=commodity,
            state=state,
            market=market,
            limit=limit,
        )["records"]

    def fetch_latest_prices(
        self,
        commodity: Optional[str] = None,
        state: Optional[str] = None,
        market: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> Dict[str, Any]:
        normalized_limit = max(1, min(limit, self.MAX_LIMIT))
        payload: Dict[str, Any] = {
            "source": "OGD India (data.gov.in) / AGMARKNET",
            "live": False,
            "configured": bool(self.api_key),
            "records": [],
            "message": None,
            "fetched_at": datetime.utcnow().isoformat(),
        }

        if not self.api_key:
            payload["message"] = "Set OGD_INDIA_API_KEY to enable live mandi prices."
            return payload

        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": normalized_limit,
            "offset": 0,
        }
        if commodity:
            params["filters[commodity]"] = commodity.strip()
        if state:
            params["filters[state]"] = state.strip()
        if market:
            params["filters[market]"] = market.strip()

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=self.REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            body = response.json()
            records = [self._normalize_record(record) for record in body.get("records", [])]
            payload["records"] = self._sort_records(records)
            payload["live"] = True
            if not payload["records"]:
                payload["message"] = "No mandi price records matched the current filters."
            return payload
        except requests.RequestException as exc:
            logger.warning("Failed to fetch live mandi prices from OGD India: %s", exc)
            payload["message"] = "Live mandi prices are temporarily unavailable."
            return payload
        except ValueError as exc:
            logger.warning("Received invalid mandi price payload from OGD India: %s", exc)
            payload["message"] = "Received an invalid response from the mandi price source."
            return payload

    def _normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        arrival_date = record.get("arrival_date") or record.get("date") or ""
        return {
            **record,
            "commodity": record.get("commodity"),
            "market": record.get("market"),
            "state": record.get("state"),
            "district": record.get("district"),
            "min_price": record.get("min_price"),
            "max_price": record.get("max_price"),
            "modal_price": record.get("modal_price"),
            "date": arrival_date,
        }

    def _sort_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def sort_key(record: Dict[str, Any]) -> tuple[datetime, str, str]:
            raw_date = str(record.get("date") or "").strip()
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    parsed = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    parsed = datetime.min
            commodity = str(record.get("commodity") or "")
            market = str(record.get("market") or "")
            return (parsed, commodity, market)

        return sorted(records, key=sort_key, reverse=True)

    def _read_env_file_api_key(self) -> Optional[str]:
        env_path = Path(__file__).resolve().parents[2] / ".env"
        if not env_path.exists():
            return None

        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("OGD_INDIA_API_KEY="):
                    _, value = line.split("=", 1)
                    return value.strip() or None
        except OSError as exc:
            logger.warning("Could not read %s for OGD_INDIA_API_KEY fallback: %s", env_path, exc)

        return None
