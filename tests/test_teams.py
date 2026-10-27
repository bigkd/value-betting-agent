from pathlib import Path

import pytest

from vba.data.db import connect, create_schema
from vba.data.load import load_season
from vba.data.team_check import check
from vba.data.teams import UnknownTeamError, normalize_name, resolve_team, unknown_team_names


@pytest.fixture
def con():
    connection = connect(":memory:")
    create_schema(connection)
    return connection


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Nott'm Forest", "nottm forest"),
        ("Atlético  de Madrid", "atletico de madrid"),
        ("  MAN CITY ", "man city"),
        ("Brighton & Hove Albion", "brighton hove albion"),
        ("Alavés", "alaves"),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def test_resolve_team_ignores_case_accents_and_punctuation(con):
    assert resolve_team(con, "football-data", "ath madrid") == "atletico_madrid"
    assert resolve_team(con, "football-data", "NOTT’M FOREST") == "nottingham_forest"
    assert resolve_team(con, "football-data", "Málaga") == "malaga"


def test_resolve_team_fails_loudly_on_unknown_name(con):
    with pytest.raises(UnknownTeamError, match="Nobody FC"):
        resolve_team(con, "football-data", "Nobody FC")


def test_resolve_team_is_scoped_by_source(con):
    with pytest.raises(UnknownTeamError):
        resolve_team(con, "understat", "Barcelona")


FIXTURES = Path(__file__).parent / "fixtures"


def test_every_fixture_team_has_an_alias(con):
    for league, fixture in [("SP1", "SP1_sample.csv"), ("E0", "E0_missing_cols.csv")]:
        load_season(con, league, "2425", FIXTURES / fixture)

    assert con.execute("SELECT count(*) FROM matches").fetchone()[0] > 0
    assert unknown_team_names(con) == []


def test_unknown_team_names_lists_only_names_without_alias(con):
    for match_id, home, away in [("1", "Barcelona", "Zeta"), ("2", "Alpha", "Zeta")]:
        con.execute(
            "INSERT INTO matches (match_id, league, season, date, home_team, away_team) "
            "VALUES (?, 'SP1', '2425', DATE '2024-08-01', ?, ?)",
            [match_id, home, away],
        )

    assert unknown_team_names(con) == ["Alpha", "Zeta"]
    assert unknown_team_names(con, league="E0") == []


def test_check_reports_unknown_names_in_a_database_file(tmp_path, capsys):
    db = tmp_path / "test.duckdb"
    con = connect(db)
    create_schema(con)
    load_season(con, "SP1", "2425", FIXTURES / "SP1_sample.csv")
    assert check(db) == 0

    con.execute("UPDATE matches SET home_team = 'Nobody FC' WHERE home_team = 'Sevilla'")
    con.close()

    assert check(db) == 1
    assert "Nobody FC" in capsys.readouterr().out
