from datetime import date

from vba.data.download import fetch_csv, season_code, season_codes

TODAY = date(2026, 10, 27)


class FakeFetch:
    """Stands in for the HTTP call and counts how many times it is used."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        return b"Div,Date\nSP1,01/08/2026\n"


def test_season_code():
    assert season_code(2024) == "2425"
    assert season_code(1999) == "9900"


def test_season_codes_up_to_current():
    codes = season_codes(2018, TODAY)
    assert codes[0] == "1819"
    assert codes[-1] == "2627"
    assert len(codes) == 9


def test_current_season_before_july_is_previous_start_year():
    assert season_codes(2023, date(2025, 3, 1)) == ["2324", "2425"]


def test_finished_season_is_downloaded_once(tmp_path):
    fetch = FakeFetch()
    first = fetch_csv("SP1", "2425", TODAY, tmp_path, fetch, pause=0)
    second = fetch_csv("SP1", "2425", TODAY, tmp_path, fetch, pause=0)

    assert first == second == tmp_path / "SP1_2425.csv"
    assert len(fetch.urls) == 1
    assert fetch.urls[0] == "https://www.football-data.co.uk/mmz4281/2425/SP1.csv"


def test_current_season_is_refreshed_every_time(tmp_path):
    fetch = FakeFetch()
    fetch_csv("E0", "2627", TODAY, tmp_path, fetch, pause=0)
    fetch_csv("E0", "2627", TODAY, tmp_path, fetch, pause=0)

    assert len(fetch.urls) == 2
