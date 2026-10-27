"""Take one snapshot of upcoming fixtures and odds from The Odds API.

Run with: uv run python -m vba.data.odds_ingest [--ttl-minutes N] [--force] [--sport KEY]

A league is only requested if its last snapshot is older than the TTL, so running the
command twice in a row spends credits once. Needs ODDS_API_KEY (see docs/data-ingestion.md).
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb

from vba.data.db import DEFAULT_DB_PATH, connect, create_schema
from vba.data.odds_api_client import (
    DEFAULT_MARKETS,
    DEFAULT_RAW_DIR,
    DEFAULT_REGIONS,
    SPORT_LEAGUES,
    Fetch,
    OddsApiError,
    credit_cost,
    fetch_odds,
    fetch_quota,
    http_get,
)
from vba.data.odds_api_load import load_snapshot, resolve_pending_events

logger = logging.getLogger(__name__)

DEFAULT_TTL = timedelta(minutes=60)


def last_captured_at(con: duckdb.DuckDBPyConnection, sport_key: str) -> datetime | None:
    return con.execute(
        "SELECT max(captured_at) FROM odds_api_requests WHERE sport_key = ?", [sport_key]
    ).fetchone()[0]


def run(
    sport_keys: Sequence[str] = tuple(SPORT_LEAGUES),
    regions: Sequence[str] = DEFAULT_REGIONS,
    markets: Sequence[str] = DEFAULT_MARKETS,
    ttl: timedelta = DEFAULT_TTL,
    force: bool = False,
    now: datetime | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
    raw_dir: Path = DEFAULT_RAW_DIR,
    fetch: Fetch = http_get,
) -> int:
    """Snapshot each league whose last snapshot is older than ttl. Returns the API calls made.

    now is naive UTC. force ignores the TTL but not the quota. The quota is read from the API
    (free) before the first paid call, never from the log: the log keeps the value of the
    last call, which is stale once the monthly quota resets. An OddsApiError (bad key, no
    quota, no network) stops the run; snapshots already stored are kept.
    """
    now = now or datetime.now(UTC).replace(tzinfo=None)
    cost = credit_cost(markets, regions)
    con = connect(db_path)
    try:
        create_schema(con)
        resolve_pending_events(con)  # a new alias in the CSV fixes events stored earlier

        calls = 0
        remaining: int | None = None
        quota_checked = False
        for sport_key in sport_keys:
            last = last_captured_at(con, sport_key)
            if not force and last is not None and now - last < ttl:
                minutes = int((now - last).total_seconds() // 60)
                print(f"{sport_key}: last snapshot {minutes} min ago (TTL {ttl}), no API call")
                continue
            if not quota_checked:
                remaining = fetch_quota(fetch).remaining
                quota_checked = True
            if remaining is not None and remaining < cost:
                print(f"{sport_key}: needs {cost} credits but only {remaining} left, stopping")
                break

            print(f"{sport_key}: requesting odds ({cost} credits)")
            payload, quota, raw_path = fetch_odds(sport_key, now, regions, markets, raw_dir, fetch)
            n_events, n_odds = load_snapshot(
                con, sport_key, now, payload, quota, raw_path, ",".join(regions), ",".join(markets)
            )
            calls += 1
            remaining = quota.remaining
            print(
                f"{sport_key}: {n_events} events, {n_odds} odds rows; cost {quota.last}, "
                f"{quota.remaining} credits remaining"
            )

        unresolved = resolve_pending_events(con)
        if unresolved:
            logger.warning(
                "%d team names from the-odds-api have no alias in team_aliases.csv "
                "(their events are stored without team ids): %s",
                len(unresolved),
                ", ".join(unresolved),
            )
        return calls
    finally:
        con.close()


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Snapshot upcoming fixtures and odds.")
    parser.add_argument(
        "--ttl-minutes",
        type=int,
        default=int(DEFAULT_TTL.total_seconds() // 60),
        help="skip a league whose last snapshot is newer than this",
    )
    parser.add_argument("--force", action="store_true", help="ignore the TTL")
    parser.add_argument(
        "--sport", action="append", choices=sorted(SPORT_LEAGUES), help="repeat; default: all"
    )
    args = parser.parse_args(argv)
    try:
        run(
            sport_keys=tuple(args.sport or SPORT_LEAGUES),
            ttl=timedelta(minutes=args.ttl_minutes),
            force=args.force,
        )
    except OddsApiError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
