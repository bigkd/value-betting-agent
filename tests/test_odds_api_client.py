import urllib.error
from datetime import datetime
from pathlib import Path

import pytest

from vba.data import odds_api_client
from vba.data.odds_api_client import (
    ApiResponse,
    OddsApiError,
    Quota,
    api_key,
    credit_cost,
    fetch_odds,
    fetch_quota,
    http_get,
)

FIXTURE = Path(__file__).parent / "fixtures" / "odds_api_soccer_la_liga.json"
CAPTURED = datetime(2026, 10, 27, 19, 5, 9)
HEADERS = {"x-requests-last": "2", "x-requests-used": "6", "x-requests-remaining": "494"}


class FakeFetch:
    def __init__(self, body: bytes = FIXTURE.read_bytes(), headers: dict[str, str] = HEADERS):
        self.calls: list[tuple[str, dict[str, str]]] = []
        self._response = ApiResponse(body, headers)

    def __call__(self, path: str, params: dict[str, str]) -> ApiResponse:
        self.calls.append((path, params))
        return self._response


def test_credit_cost_is_markets_times_regions():
    assert credit_cost(["h2h", "totals"], ["eu"]) == 2
    assert credit_cost(["h2h"], ["eu", "uk"]) == 2


def test_fetch_odds_saves_raw_response_and_reads_quota(tmp_path):
    fake = FakeFetch()

    events, quota, path = fetch_odds(
        "soccer_spain_la_liga", CAPTURED, raw_dir=tmp_path / "raw", fetch=fake
    )

    assert path == tmp_path / "raw" / "soccer_spain_la_liga_20261027T190509Z.json"
    assert path.read_bytes() == FIXTURE.read_bytes()
    assert len(events) == 2
    assert quota == Quota(last=2, used=6, remaining=494)
    [(called_path, params)] = fake.calls
    assert called_path == "/sports/soccer_spain_la_liga/odds"
    assert params["regions"] == "eu"
    assert params["markets"] == "h2h,totals"
    assert "apiKey" not in params


def test_quota_headers_may_be_missing():
    assert Quota.from_headers({}) == Quota(last=None, used=None, remaining=None)


def test_api_key_requires_the_variable(monkeypatch):
    monkeypatch.setattr(odds_api_client, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    with pytest.raises(OddsApiError, match="ODDS_API_KEY"):
        api_key()

    monkeypatch.setenv("ODDS_API_KEY", "secret")
    assert api_key() == "secret"


def test_http_errors_never_leak_the_key(monkeypatch):
    monkeypatch.setattr(odds_api_client, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("ODDS_API_KEY", "secret")

    def refuse(url, timeout):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(odds_api_client.urllib.request, "urlopen", refuse)

    with pytest.raises(OddsApiError) as error:
        http_get("/sports", {})
    assert "401" in str(error.value)
    assert "secret" not in str(error.value)
    assert error.value.__cause__ is None  # the original error carries the URL


def test_fetch_quota_reads_the_free_sports_endpoint():
    fake = FakeFetch(body=b"[]", headers={"x-requests-remaining": "431"})

    assert fetch_quota(fake) == Quota(last=None, used=None, remaining=431)
    assert fake.calls == [("/sports", {})]
