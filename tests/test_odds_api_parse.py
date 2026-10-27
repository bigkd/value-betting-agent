import json
from datetime import datetime
from pathlib import Path

import pytest

from vba.data.odds_api_parse import parse_events, parse_odds, parse_time

# Real La Liga response trimmed to 2 events and 4 bookmakers (one of them an exchange).
FIXTURE = Path(__file__).parent / "fixtures" / "odds_api_soccer_la_liga.json"
CAPTURED = datetime(2026, 10, 27, 19, 0)


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parse_time_returns_naive_utc():
    assert parse_time("2026-10-30T20:00:00Z") == datetime(2026, 10, 30, 20, 0)
    assert parse_time("2026-10-30T22:00:00+02:00") == datetime(2026, 10, 30, 20, 0)


def test_parse_events(payload):
    events = parse_events(payload)

    assert len(events) == 2
    assert events[0] == {
        "event_id": payload[0]["id"],
        "sport_key": "soccer_spain_la_liga",
        "commence_time": datetime(2026, 10, 30, 20, 0),
        "home_name_raw": "Villarreal",
        "away_name_raw": "Espanyol",
    }


def test_parse_odds_maps_markets_and_selections(payload):
    rows = parse_odds(payload, "snap1", CAPTURED)

    pinnacle = [
        r for r in rows if r["event_id"] == payload[0]["id"] and r["bookmaker"] == "pinnacle"
    ]
    one_x_two = {r["selection"]: r["odds"] for r in pinnacle if r["market"] == "1x2"}
    assert one_x_two == {"away": 6.72, "home": 1.44, "draw": 5.06}
    assert all(r["line"] is None for r in pinnacle if r["market"] == "1x2")

    totals = [r for r in pinnacle if r["market"] == "ou"]
    assert {(r["selection"], r["line"], r["odds"]) for r in totals} == {
        ("over", 3.0, 1.82),
        ("under", 3.0, 2.09),
    }
    assert all(r["snapshot_id"] == "snap1" and r["captured_at"] == CAPTURED for r in rows)
    assert pinnacle[0]["bookmaker_updated_at"] == datetime(2026, 10, 27, 18, 42, 21)


def test_parse_odds_discards_exchange_lay_market(payload):
    rows = parse_odds(payload, "snap1", CAPTURED)

    assert {r["market"] for r in rows} == {"1x2", "ou"}
    # betfair_ex_eu only has h2h and h2h_lay in the fixture: back prices only.
    exchange = [r for r in rows if r["bookmaker"] == "betfair_ex_eu"]
    assert len(exchange) == 2 * 3


def test_parse_odds_fails_on_unexpected_outcome(payload):
    payload[0]["bookmakers"][0]["markets"][0]["outcomes"][0]["name"] = "Nobody FC"

    with pytest.raises(ValueError, match="Nobody FC"):
        parse_odds(payload, "snap1", CAPTURED)
