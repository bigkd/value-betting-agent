"""Client for The Odds API: one request per league, raw response saved to disk.

The API key comes from the ODDS_API_KEY environment variable (loaded from .env when
present) and is only added to the request inside http_get, so it never shows up in
logs, error messages or the fetch seam used by tests.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

BASE_URL = "https://api.the-odds-api.com/v4"
DEFAULT_RAW_DIR = Path("data/raw/odds_api")

# The API's sport keys -> football-data league codes used in the rest of the project.
SPORT_LEAGUES = {"soccer_spain_la_liga": "SP1", "soccer_epl": "E0"}
DEFAULT_REGIONS = ("eu",)  # includes Pinnacle; no Spanish bookmakers
DEFAULT_MARKETS = ("h2h", "totals")


class OddsApiError(RuntimeError):
    """The API could not be reached, rejected the request, or the key is missing."""


@dataclass(frozen=True)
class ApiResponse:
    body: bytes
    headers: dict[str, str]  # keys lowercased


# (path, query params without the key) -> response. Tests replace it with a fake.
Fetch = Callable[[str, dict[str, str]], ApiResponse]


@dataclass(frozen=True)
class Quota:
    """Credits as reported by the response headers (None when a header is missing)."""

    last: int | None
    used: int | None
    remaining: int | None

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> "Quota":
        def number(name: str) -> int | None:
            value = headers.get(name)
            return int(float(value)) if value is not None else None

        return cls(
            last=number("x-requests-last"),
            used=number("x-requests-used"),
            remaining=number("x-requests-remaining"),
        )


def api_key() -> str:
    load_dotenv(find_dotenv(usecwd=True))  # never overrides variables already set
    key = os.environ.get("ODDS_API_KEY", "")
    if not key:
        raise OddsApiError("ODDS_API_KEY is not set (put it in .env or the environment)")
    return key


def http_get(path: str, params: dict[str, str]) -> ApiResponse:
    key = api_key()
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode({**params, 'apiKey': key})}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            headers = {name.lower(): value for name, value in response.headers.items()}
            return ApiResponse(response.read(), headers)
    except urllib.error.HTTPError as error:
        # Built by hand: never include the URL, which carries the key.
        raise OddsApiError(f"HTTP {error.code} {error.reason} from The Odds API") from None
    except (urllib.error.URLError, OSError) as error:
        raise OddsApiError(f"could not reach The Odds API: {error}") from None


def fetch_quota(fetch: Fetch = http_get) -> Quota:
    """Credits left right now. GET /sports is free and carries the x-requests-* headers."""
    return Quota.from_headers(fetch("/sports", {}).headers)


def credit_cost(markets: Sequence[str], regions: Sequence[str]) -> int:
    """Credits one /odds call for one sport costs: markets x regions."""
    return len(markets) * len(regions)


def snapshot_id(sport_key: str, captured_at: datetime) -> str:
    return f"{sport_key}_{captured_at:%Y%m%dT%H%M%SZ}"


def fetch_odds(
    sport_key: str,
    captured_at: datetime,
    regions: Sequence[str] = DEFAULT_REGIONS,
    markets: Sequence[str] = DEFAULT_MARKETS,
    raw_dir: Path = DEFAULT_RAW_DIR,
    fetch: Fetch = http_get,
) -> tuple[list[dict], Quota, Path]:
    """Request current odds for one league and save the raw JSON before anything else.

    captured_at is naive UTC. Only events that have not started yet are requested
    (commenceTimeFrom = captured_at), so no live odds are stored: those move fast and
    would not be a pre-match closing line. Returns the decoded events, the quota after
    the call and the path of the raw file (named after the snapshot id).
    """
    response = fetch(
        f"/sports/{sport_key}/odds",
        {
            "regions": ",".join(regions),
            "markets": ",".join(markets),
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "commenceTimeFrom": f"{captured_at:%Y-%m-%dT%H:%M:%SZ}",
        },
    )
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{snapshot_id(sport_key, captured_at)}.json"
    path.write_bytes(response.body)
    return json.loads(response.body), Quota.from_headers(response.headers), path
