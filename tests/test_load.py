from pathlib import Path

import pytest

from vba.data.db import connect, create_schema
from vba.data.load import load_season

FIXTURES = Path(__file__).parent / "fixtures"
SP1 = FIXTURES / "SP1_sample.csv"
E0 = FIXTURES / "E0_missing_cols.csv"


@pytest.fixture
def con():
    connection = connect(":memory:")
    create_schema(connection)
    return connection


def _counts(con) -> tuple[int, int]:
    matches = con.execute("SELECT count(*) FROM matches").fetchone()[0]
    odds = con.execute("SELECT count(*) FROM odds").fetchone()[0]
    return matches, odds


def test_load_inserts_matches_and_odds(con):
    n_matches, n_odds = load_season(con, "SP1", "2425", SP1)

    assert n_matches == 3
    assert n_odds > 0
    assert _counts(con) == (n_matches, n_odds)


def test_load_is_idempotent(con):
    first = load_season(con, "SP1", "2425", SP1)
    after_first = _counts(con)
    second = load_season(con, "SP1", "2425", SP1)

    assert first == second
    assert _counts(con) == after_first


def test_reloading_one_season_leaves_other_leagues_untouched(con):
    load_season(con, "SP1", "2425", SP1)
    load_season(con, "E0", "2425", E0)
    before = _counts(con)

    load_season(con, "SP1", "2425", SP1)

    assert _counts(con) == before
    assert con.execute("SELECT count(*) FROM matches WHERE league = 'E0'").fetchone()[0] == 2


def test_missing_columns_are_stored_as_null(con):
    load_season(con, "E0", "2425", E0)

    row = con.execute(
        "SELECT home_shots, referee, ft_home_goals FROM matches WHERE home_team = 'Man United'"
    ).fetchone()
    assert row == (None, None, 1)


def test_failed_load_rolls_back(con, tmp_path):
    load_season(con, "SP1", "2425", SP1)
    before = _counts(con)

    # The same match twice violates the primary key, so the reload must roll back.
    header, line = SP1.read_text().splitlines()[:2]
    bad = tmp_path / "dup.csv"
    bad.write_text("\n".join([header, line, line]))
    with pytest.raises(Exception, match="(?i)duplicate|constraint"):
        load_season(con, "SP1", "2425", bad)

    assert _counts(con) == before
