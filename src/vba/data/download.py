"""Download football-data.co.uk CSVs into a local cache (data/raw/)."""

import time
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
DEFAULT_RAW_DIR = Path("data/raw")

# Seasons start in August: before July we are still in the season that began last year.
_SEASON_START_MONTH = 7


def current_season_start_year(today: date) -> int:
    return today.year if today.month >= _SEASON_START_MONTH else today.year - 1


def season_code(start_year: int) -> str:
    """2024 -> "2425"."""
    return f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"


def season_codes(first_start_year: int, today: date) -> list[str]:
    """All season codes from first_start_year up to the current one."""
    last = current_season_start_year(today)
    return [season_code(year) for year in range(first_start_year, last + 1)]


def http_get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def fetch_csv(
    league: str,
    season: str,
    today: date,
    raw_dir: Path = DEFAULT_RAW_DIR,
    fetch: Callable[[str], bytes] = http_get,
    pause: float = 1.5,
) -> Path:
    """Return the cached CSV path, downloading it when needed.

    Finished seasons are downloaded once. The current season is refreshed on
    every call because football-data.co.uk updates it weekly.
    """
    path = raw_dir / f"{league}_{season}.csv"
    is_current = season == season_code(current_season_start_year(today))
    if path.exists() and not is_current:
        return path

    time.sleep(pause)  # be polite with the server
    data = fetch(BASE_URL.format(season=season, league=league))
    raw_dir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path
