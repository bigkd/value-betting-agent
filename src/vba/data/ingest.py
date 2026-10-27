"""Download and load football-data.co.uk history into DuckDB.

Run with: uv run python -m vba.data.ingest
"""

import logging
import urllib.error
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from vba.data.db import DEFAULT_DB_PATH, connect, create_schema
from vba.data.download import DEFAULT_RAW_DIR, fetch_csv, http_get, season_codes
from vba.data.load import load_season

DEFAULT_LEAGUES = ("SP1", "E0")
FIRST_START_YEAR = 2018


def run(
    leagues: Sequence[str] = DEFAULT_LEAGUES,
    first_start_year: int = FIRST_START_YEAR,
    today: date | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
    raw_dir: Path = DEFAULT_RAW_DIR,
    fetch: Callable[[str], bytes] = http_get,
    pause: float = 1.5,
) -> None:
    today = today or date.today()
    con = connect(db_path)
    create_schema(con)

    for league in leagues:
        for season in season_codes(first_start_year, today):
            try:
                path = fetch_csv(league, season, today, raw_dir, fetch, pause)
            except (urllib.error.URLError, OSError) as error:
                print(f"{league} {season}: download failed ({error}), skipping")
                continue
            n_matches, n_odds = load_season(con, league, season, path)
            print(f"{league} {season}: {n_matches} matches, {n_odds} odds")
    con.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run()


if __name__ == "__main__":
    main()
