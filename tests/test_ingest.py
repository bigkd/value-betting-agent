import urllib.error
from datetime import date
from pathlib import Path

from vba.data.db import connect
from vba.data.ingest import run

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2019, 10, 1)  # seasons 1819 and 1920


def fake_fetch(url: str) -> bytes:
    name = "SP1_sample.csv" if "/SP1.csv" in url else "E0_missing_cols.csv"
    return (FIXTURES / name).read_bytes()


def _counts(db_path) -> tuple[int, int]:
    con = connect(db_path)
    result = (
        con.execute("SELECT count(*) FROM matches").fetchone()[0],
        con.execute("SELECT count(*) FROM odds").fetchone()[0],
    )
    con.close()
    return result


def test_run_loads_all_leagues_and_seasons_without_network(tmp_path):
    db = tmp_path / "vba.duckdb"
    run(today=TODAY, db_path=db, raw_dir=tmp_path / "raw", fetch=fake_fetch, pause=0)

    con = connect(db)
    rows = con.execute(
        "SELECT league, season, count(*) FROM matches GROUP BY ALL ORDER BY ALL"
    ).fetchall()
    con.close()
    assert rows == [("E0", "1819", 2), ("E0", "1920", 2), ("SP1", "1819", 3), ("SP1", "1920", 3)]


def test_run_twice_does_not_duplicate_rows(tmp_path):
    db = tmp_path / "vba.duckdb"
    kwargs = dict(today=TODAY, db_path=db, raw_dir=tmp_path / "raw", fetch=fake_fetch, pause=0)

    run(**kwargs)
    first = _counts(db)
    run(**kwargs)

    assert _counts(db) == first


def test_download_failure_skips_that_season(tmp_path, capsys):
    def flaky_fetch(url: str) -> bytes:
        if "/1920/" in url:
            raise urllib.error.URLError("not published yet")
        return fake_fetch(url)

    db = tmp_path / "vba.duckdb"
    run(today=TODAY, db_path=db, raw_dir=tmp_path / "raw", fetch=flaky_fetch, pause=0)

    assert _counts(db)[0] == 5  # only the 1819 seasons: 3 + 2
    assert "download failed" in capsys.readouterr().out
