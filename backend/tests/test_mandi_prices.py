import requests

from app.services.mandi_prices import MandiPriceService


class _MockResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_fetch_latest_prices_returns_unconfigured_payload_without_api_key():
    service = MandiPriceService(api_key=None)

    payload = service.fetch_latest_prices()

    assert payload["configured"] is False
    assert payload["live"] is False
    assert payload["records"] == []
    assert "OGD_INDIA_API_KEY" in payload["message"]


def test_fetch_latest_prices_normalizes_and_sorts_records(monkeypatch):
    def fake_get(url, params, timeout):
        assert params["filters[commodity]"] == "Onion"
        assert params["filters[state]"] == "Karnataka"
        assert params["filters[market]"] == "Bengaluru"
        assert params["limit"] == 2
        return _MockResponse(
            {
                "records": [
                    {
                        "commodity": "Onion",
                        "market": "Mysuru",
                        "state": "Karnataka",
                        "district": "Mysuru",
                        "modal_price": "2000",
                        "arrival_date": "01/04/2026",
                    },
                    {
                        "commodity": "Onion",
                        "market": "Bengaluru",
                        "state": "Karnataka",
                        "district": "Bengaluru Urban",
                        "modal_price": "2200",
                        "arrival_date": "27/04/2026",
                    },
                ]
            }
        )

    monkeypatch.setattr("app.services.mandi_prices.requests.get", fake_get)

    service = MandiPriceService(api_key="live-key")
    payload = service.fetch_latest_prices(commodity="Onion", state="Karnataka", market="Bengaluru", limit=2)

    assert payload["configured"] is True
    assert payload["live"] is True
    assert payload["records"][0]["market"] == "Bengaluru"
    assert payload["records"][0]["date"] == "27/04/2026"


def test_fetch_latest_prices_returns_empty_payload_on_request_failure(monkeypatch):
    def fake_get(url, params, timeout):
        raise requests.RequestException("boom")

    monkeypatch.setattr("app.services.mandi_prices.requests.get", fake_get)

    service = MandiPriceService(api_key="live-key")
    payload = service.fetch_latest_prices()

    assert payload["configured"] is True
    assert payload["live"] is False
    assert payload["records"] == []
    assert payload["message"] is not None
