import pytest

from vba.data.db import connect, create_schema
from vba.data.teams import UnknownTeamError, normalize_name, resolve_team


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
