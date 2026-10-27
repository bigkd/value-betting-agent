"""Turn a The Odds API /odds response into event and odds rows.

Pure functions: no network and no database, so they are easy to test with a recorded response.
"""

from datetime import UTC, datetime

# The API's market keys -> the vocabulary of the odds table. Any other market in a response
# (h2h_lay from exchanges, for instance) is ignored.
MARKETS = {"h2h": "1x2", "totals": "ou"}


def parse_time(text: str) -> datetime:
    """ "2026-10-30T20:00:00Z" -> naive UTC datetime (how the tables store timestamps)."""
    return datetime.fromisoformat(text).astimezone(UTC).replace(tzinfo=None)


def parse_events(payload: list[dict]) -> list[dict[str, object]]:
    return [
        {
            "event_id": event["id"],
            "sport_key": event["sport_key"],
            "commence_time": parse_time(event["commence_time"]),
            "home_name_raw": event["home_team"],
            "away_name_raw": event["away_team"],
        }
        for event in payload
    ]


def _selection(market: str, outcome_name: str, home: str, away: str) -> str:
    if market == "h2h":
        if outcome_name == home:
            return "home"
        if outcome_name == away:
            return "away"
        if outcome_name == "Draw":
            return "draw"
    elif outcome_name in ("Over", "Under"):
        return outcome_name.lower()
    # Fail loudly: silently dropping an outcome would store half a market.
    raise ValueError(f"unexpected {market} outcome {outcome_name!r} in {home} - {away}")


def parse_odds(
    payload: list[dict], snapshot_id: str, captured_at: datetime
) -> list[dict[str, object]]:
    """One row per event + bookmaker + market + selection (+ line for totals)."""
    rows: list[dict[str, object]] = []
    for event in payload:
        home, away = event["home_team"], event["away_team"]
        for bookmaker in event["bookmakers"]:
            for market in bookmaker["markets"]:
                if market["key"] not in MARKETS:
                    continue
                updated = parse_time(market.get("last_update") or bookmaker["last_update"])
                for outcome in market["outcomes"]:
                    rows.append(
                        {
                            "snapshot_id": snapshot_id,
                            "captured_at": captured_at,
                            "event_id": event["id"],
                            "bookmaker": bookmaker["key"],
                            "market": MARKETS[market["key"]],
                            "selection": _selection(market["key"], outcome["name"], home, away),
                            "line": outcome.get("point"),
                            "odds": outcome["price"],
                            "bookmaker_updated_at": updated,
                        }
                    )
    return rows
