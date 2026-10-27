import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from vba.data.db import connect, create_schema
from vba.data.odds_api_client import Quota
from vba.data.odds_api_load import load_snapshot, resolve_pending_events

FIXTURE = Path(__file__).parent / "fixtures" / "odds_api_soccer_la_liga.json"
FIRST = datetime(2026, 10, 27, 19, 0)
QUOTA = Quota(last=2, used=6, remaining=494)
RAW = Path("data/raw/odds_api/soccer_spain_la_liga_x.json")


@pytest.fixture
def con():
    connection = connect(":memory:")
    create_schema(connection)
    return connection


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _load(con, payload, captured_at=FIRST):
    return load_snapshot(
        con, "soccer_spain_la_liga", captured_at, payload, QUOTA, RAW, "eu", "h2h,totals"
    )


def test_load_snapshot_stores_events_odds_and_request_log(con, payload):
    n_events, n_odds = _load(con, payload)

    assert n_events == 2
    assert con.execute("SELECT count(*) FROM odds_snapshots").fetchone()[0] == n_odds > 0
    events = con.execute(
        "SELECT league, commence_time, home_team_id, away_team_id FROM odds_api_events "
        "ORDER BY commence_time"
    ).fetchall()
    assert events == [
        ("SP1", datetime(2026, 10, 30, 20, 0), "villarreal", "espanyol"),
        ("SP1", events[1][1], "levante", "atletico_madrid"),
    ]
    request = con.execute(
        "SELECT snapshot_id, regions, markets, credits_last, credits_remaining, n_events, raw_path "
        "FROM odds_api_requests"
    ).fetchone()
    assert request == (
        "soccer_spain_la_liga_20261027T190000Z",
        "eu",
        "h2h,totals",
        2,
        494,
        2,
        RAW.as_posix(),
    )


def test_snapshots_are_appended_never_overwritten(con, payload):
    _load(con, payload, FIRST)
    after_first = con.execute("SELECT count(*) FROM odds_snapshots").fetchone()[0]
    later = FIRST + timedelta(hours=6)
    _load(con, payload, later)

    assert con.execute("SELECT count(*) FROM odds_snapshots").fetchone()[0] == 2 * after_first
    assert con.execute("SELECT count(DISTINCT captured_at) FROM odds_snapshots").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM odds_api_requests").fetchone()[0] == 2
    # Events are upserted: still two rows, first_seen_at kept, last_seen_at moved.
    assert con.execute(
        "SELECT count(*), min(first_seen_at), max(last_seen_at) FROM odds_api_events"
    ).fetchone() == (2, FIRST, later)


def test_closing_line_is_the_last_snapshot_before_kickoff(con, payload):
    _load(con, payload, FIRST)
    _load(con, payload, datetime(2026, 10, 30, 19, 0))  # one hour before Villarreal-Espanyol
    _load(con, payload, datetime(2026, 10, 30, 21, 0))  # after it started

    closing = con.execute(
        "SELECT max(s.captured_at) FROM odds_snapshots s JOIN odds_api_events e USING (event_id) "
        "WHERE e.home_team_id = 'villarreal' AND s.captured_at < e.commence_time"
    ).fetchone()[0]
    assert closing == datetime(2026, 10, 30, 19, 0)


def test_unknown_team_is_stored_with_null_id_and_fixed_by_a_later_alias(con, payload):
    payload[0]["home_team"] = "Villarreal Unidos"
    for bookmaker in payload[0]["bookmakers"]:
        for market in bookmaker["markets"]:
            if market["key"] == "h2h":
                for outcome in market["outcomes"]:
                    if outcome["name"] == "Villarreal":
                        outcome["name"] = "Villarreal Unidos"
    _load(con, payload)

    row = "SELECT home_team_id, away_team_id FROM odds_api_events WHERE home_name_raw = ?"
    assert con.execute(row, ["Villarreal Unidos"]).fetchone() == (None, "espanyol")
    assert resolve_pending_events(con) == ["Villarreal Unidos"]

    con.execute(
        "INSERT INTO team_aliases VALUES ('the-odds-api', 'Villarreal Unidos', 'villarreal')"
    )
    assert resolve_pending_events(con) == []
    assert con.execute(row, ["Villarreal Unidos"]).fetchone() == ("villarreal", "espanyol")


def test_payload_that_does_not_parse_stores_nothing(con, payload):
    payload[1]["bookmakers"][0]["markets"][0]["outcomes"][0]["name"] = "Nobody FC"

    with pytest.raises(ValueError):
        _load(con, payload)

    for table in ("odds_api_events", "odds_snapshots", "odds_api_requests"):
        assert con.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
