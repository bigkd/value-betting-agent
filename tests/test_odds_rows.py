from pathlib import Path

from vba.data.odds_rows import parse_odds
from vba.data.parse import read_rows

FIXTURES = Path(__file__).parent / "fixtures"


def _find(records, bookmaker, market, selection, is_closing):
    found = [
        r
        for r in records
        if (r["bookmaker"], r["market"], r["selection"], r["is_closing"])
        == (bookmaker, market, selection, is_closing)
    ]
    assert len(found) == 1
    return found[0]


def test_first_match_rows():
    row = read_rows(FIXTURES / "SP1_sample.csv")[0]
    records = parse_odds(row, "m1")

    assert _find(records, "pinnacle", "1x2", "home", False)["odds"] == 2.15
    assert _find(records, "pinnacle", "1x2", "home", True)["odds"] == 2.08
    assert _find(records, "pinnacle", "1x2", "home", False)["line"] is None

    ou = _find(records, "pinnacle", "ou", "over", False)
    assert (ou["odds"], ou["line"]) == (1.85, 2.5)

    ah_open = _find(records, "bet365", "ah", "home", False)
    assert (ah_open["odds"], ah_open["line"]) == (1.95, -0.5)
    ah_close = _find(records, "bet365", "ah", "away", True)
    assert (ah_close["odds"], ah_close["line"]) == (2.00, -0.5)

    assert _find(records, "market_max", "1x2", "draw", False)["odds"] == 3.80
    assert {r["match_id"] for r in records} == {"m1"}


def test_missing_columns_produce_only_available_rows():
    row = read_rows(FIXTURES / "E0_missing_cols.csv")[0]
    records = parse_odds(row, "m2")

    assert {(r["bookmaker"], r["market"]) for r in records} == {("bet365", "1x2")}
    assert len(records) == 3  # home, draw, away opening


def test_invalid_cells_are_skipped():
    row = {"PSH": "", "PSD": "abc", "PSA": "1.0", "B365H": "2.50", "B365AHH": "1.90"}
    records = parse_odds(row, "m3")

    # Only B365H survives: B365AHH has no AHh line in the row.
    assert [(r["bookmaker"], r["selection"], r["odds"]) for r in records] == [
        ("bet365", "home", 2.5)
    ]
