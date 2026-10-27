from datetime import date
from pathlib import Path

import pytest

from vba.data.parse import parse_date, parse_match, read_rows

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_date_accepts_two_and_four_digit_years():
    assert parse_date("26/10/24") == date(2024, 10, 26)
    assert parse_date("26/10/2024") == date(2024, 10, 26)


def test_parse_date_rejects_garbage():
    with pytest.raises(ValueError):
        parse_date("2024-10-26")


def test_read_rows_skips_blank_trailing_rows():
    rows = read_rows(FIXTURES / "SP1_sample.csv")
    assert len(rows) == 3


def test_parse_match_full_row():
    row = read_rows(FIXTURES / "SP1_sample.csv")[0]
    match = parse_match(row, "SP1", "2425")

    assert match["match_id"] == "SP1_2425_2024-10-26_Barcelona_Real Madrid"
    assert match["date"] == date(2024, 10, 26)
    assert (match["home_team"], match["away_team"]) == ("Barcelona", "Real Madrid")
    assert (match["ht_home_goals"], match["ht_away_goals"]) == (1, 0)
    assert (match["ft_home_goals"], match["ft_away_goals"]) == (2, 1)
    assert match["home_shots"] == 15
    assert match["away_shots_on_target"] == 3
    assert match["home_corners"] == 6
    assert match["away_red"] == 1
    assert match["referee"] == "Gil Manzano"


def test_parse_match_missing_columns_become_null():
    row = read_rows(FIXTURES / "E0_missing_cols.csv")[0]
    match = parse_match(row, "E0", "2425")

    assert match["ft_home_goals"] == 1
    assert match["ht_home_goals"] is None
    assert match["home_shots"] is None
    assert match["away_red"] is None
    assert match["referee"] is None


def test_read_rows_keeps_line_breaks_inside_quoted_fields(tmp_path):
    path = tmp_path / "multiline.csv"
    path.write_bytes(b'Date,HomeTeam,AwayTeam\r\n01/08/24,"Real\nBetis",Bilbao\r\n')

    rows = read_rows(path)

    assert len(rows) == 1
    assert rows[0]["HomeTeam"] == "Real\nBetis"


def test_read_rows_falls_back_to_latin1(tmp_path):
    path = tmp_path / "latin.csv"
    path.write_bytes("Date,HomeTeam,AwayTeam\n01/08/24,Atlético,Bilbao\n".encode("latin-1"))

    assert read_rows(path)[0]["HomeTeam"] == "Atlético"
