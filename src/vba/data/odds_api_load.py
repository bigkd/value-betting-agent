"""Store one The Odds API snapshot in DuckDB.

odds_snapshots and odds_api_requests are append-only: this module only ever inserts
into them. odds_api_events is upserted by event_id.
"""

from datetime import datetime
from pathlib import Path

import duckdb

from vba.data.load import insert_records
from vba.data.odds_api_client import SPORT_LEAGUES, Quota, snapshot_id
from vba.data.odds_api_parse import parse_events, parse_odds
from vba.data.teams import UnknownTeamError, resolve_team

SOURCE = "the-odds-api"

# first_seen_at is left out of the update so it keeps the time of the first snapshot.
# COALESCE keeps a team id already resolved if this snapshot's name did not resolve.
_UPSERT_EVENT = """
INSERT INTO odds_api_events (
    event_id, sport_key, league, commence_time, home_name_raw, away_name_raw,
    home_team_id, away_team_id, first_seen_at, last_seen_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (event_id) DO UPDATE SET
    commence_time = excluded.commence_time,
    home_name_raw = excluded.home_name_raw,
    away_name_raw = excluded.away_name_raw,
    home_team_id = COALESCE(excluded.home_team_id, odds_api_events.home_team_id),
    away_team_id = COALESCE(excluded.away_team_id, odds_api_events.away_team_id),
    last_seen_at = excluded.last_seen_at
"""


def _resolve(con: duckdb.DuckDBPyConnection, name: str) -> str | None:
    try:
        return resolve_team(con, SOURCE, name)
    except UnknownTeamError:
        return None


def resolve_pending_events(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Fill in team ids that are still NULL, so that adding an alias to the CSV fixes
    events stored earlier. Returns the sorted names that still have no alias."""
    pending = con.execute(
        "SELECT event_id, home_name_raw, away_name_raw, home_team_id, away_team_id "
        "FROM odds_api_events WHERE home_team_id IS NULL OR away_team_id IS NULL"
    ).fetchall()
    unresolved: set[str] = set()
    for event_id, home_name, away_name, home_id, away_id in pending:
        home_id = home_id or _resolve(con, home_name)
        away_id = away_id or _resolve(con, away_name)
        con.execute(
            "UPDATE odds_api_events SET home_team_id = ?, away_team_id = ? WHERE event_id = ?",
            [home_id, away_id, event_id],
        )
        if home_id is None:
            unresolved.add(home_name)
        if away_id is None:
            unresolved.add(away_name)
    return sorted(unresolved)


def load_snapshot(
    con: duckdb.DuckDBPyConnection,
    sport_key: str,
    captured_at: datetime,
    payload: list[dict],
    quota: Quota,
    raw_path: Path,
    regions: str,
    markets: str,
) -> tuple[int, int]:
    """Upsert the events and append the odds rows and the request log, in one transaction.

    Returns (events, odds rows). A payload that does not parse stores nothing.
    """
    snap_id = snapshot_id(sport_key, captured_at)
    events = parse_events(payload)
    odds = parse_odds(payload, snap_id, captured_at)
    league = SPORT_LEAGUES[sport_key]

    con.begin()
    try:
        for event, raw in zip(events, payload, strict=True):
            con.execute(
                _UPSERT_EVENT,
                [
                    event["event_id"],
                    sport_key,
                    league,
                    event["commence_time"],
                    event["home_name_raw"],
                    event["away_name_raw"],
                    _resolve(con, raw["home_team"]),
                    _resolve(con, raw["away_team"]),
                    captured_at,
                    captured_at,
                ],
            )
        insert_records(con, "odds_snapshots", odds)
        con.execute(
            "INSERT INTO odds_api_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                snap_id,
                captured_at,
                sport_key,
                regions,
                markets,
                quota.last,
                quota.used,
                quota.remaining,
                len(events),
                raw_path.as_posix(),
            ],
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
    return len(events), len(odds)
