import logging
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from vba.data.db import connect
from vba.data.odds_api_client import ApiResponse, OddsApiError
from vba.data.odds_ingest import main, run

FIXTURE = Path(__file__).parent / "fixtures" / "odds_api_soccer_la_liga.json"
NOW = datetime(2026, 10, 27, 19, 0)
LA_LIGA = ("soccer_spain_la_liga",)


class FakeFetch:
    """paths lists the paid /odds calls; quota_checks counts the free GET /sports calls."""

    def __init__(self, remaining: int = 494):
        self.paths: list[str] = []
        self.quota_checks = 0
        self.remaining = remaining  # what the API reports right now

    def __call__(self, path: str, params: dict[str, str]) -> ApiResponse:
        headers = {"x-requests-last": "2", "x-requests-remaining": str(self.remaining)}
        if path == "/sports":
            self.quota_checks += 1
            return ApiResponse(b"[]", {**headers, "x-requests-last": "0"})
        self.paths.append(path)
        return ApiResponse(FIXTURE.read_bytes(), headers)


@pytest.fixture
def paths(tmp_path):
    return {"db_path": tmp_path / "vba.duckdb", "raw_dir": tmp_path / "raw"}


def _count(db_path, table):
    con = connect(db_path)
    try:
        return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    finally:
        con.close()


def test_run_stores_a_snapshot_and_the_raw_file(paths, capsys):
    fake = FakeFetch()

    calls = run(LA_LIGA, now=NOW, fetch=fake, **paths)

    assert calls == 1
    assert fake.paths == ["/sports/soccer_spain_la_liga/odds"]
    assert _count(paths["db_path"], "odds_api_events") == 2
    assert _count(paths["db_path"], "odds_snapshots") > 0
    assert [p.name for p in paths["raw_dir"].iterdir()] == [
        "soccer_spain_la_liga_20261027T190000Z.json"
    ]
    assert "494 credits remaining" in capsys.readouterr().out


def test_second_run_within_ttl_makes_no_api_call(paths, capsys):
    fake = FakeFetch()
    run(LA_LIGA, now=NOW, fetch=fake, **paths)
    n_rows = _count(paths["db_path"], "odds_snapshots")

    calls = run(LA_LIGA, now=NOW + timedelta(minutes=30), fetch=fake, **paths)

    assert calls == 0
    assert len(fake.paths) == 1
    assert fake.quota_checks == 1  # only the first run; the TTL skip needs no call at all
    assert _count(paths["db_path"], "odds_snapshots") == n_rows
    assert "no API call" in capsys.readouterr().out


def test_run_after_ttl_or_with_force_takes_a_new_snapshot(paths):
    fake = FakeFetch()
    run(LA_LIGA, now=NOW, fetch=fake, **paths)
    run(LA_LIGA, now=NOW + timedelta(minutes=61), fetch=fake, **paths)
    run(LA_LIGA, now=NOW + timedelta(minutes=62), force=True, fetch=fake, **paths)

    assert len(fake.paths) == 3
    assert _count(paths["db_path"], "odds_api_requests") == 3
    assert _count(paths["db_path"], "odds_api_events") == 2  # upserted, not duplicated


def test_ttl_is_tracked_per_league(paths):
    fake = FakeFetch()
    run(LA_LIGA, now=NOW, fetch=fake, **paths)

    calls = run(("soccer_spain_la_liga", "soccer_epl"), now=NOW, fetch=fake, **paths)

    assert calls == 1
    assert fake.paths[-1] == "/sports/soccer_epl/odds"


def test_run_stops_when_the_api_reports_less_quota_than_the_cost(paths, capsys):
    fake = FakeFetch()
    run(LA_LIGA, now=NOW, fetch=fake, **paths)
    fake.remaining = 1

    calls = run(("soccer_epl",), now=NOW + timedelta(hours=2), fetch=fake, **paths)

    assert calls == 0
    assert "only 1 left" in capsys.readouterr().out


@pytest.mark.parametrize("force", [False, True])
def test_stale_low_quota_in_the_log_does_not_block_after_the_monthly_reset(paths, force):
    fake = FakeFetch(remaining=494)
    run(LA_LIGA, now=NOW, fetch=fake, **paths)
    # The last call of the previous month left 1 credit; the API has reset since then.
    con = connect(paths["db_path"])
    con.execute("UPDATE odds_api_requests SET credits_remaining = 1")
    con.close()
    fake.remaining = 500

    calls = run(LA_LIGA, now=NOW + timedelta(hours=2), force=force, fetch=fake, **paths)

    assert calls == 1
    assert len(fake.paths) == 2


def test_quota_is_checked_once_per_run(paths):
    fake = FakeFetch()

    run(("soccer_spain_la_liga", "soccer_epl"), now=NOW, fetch=fake, **paths)

    assert len(fake.paths) == 2
    assert fake.quota_checks == 1


def test_unresolved_team_names_are_reported_once(paths, caplog):
    def fetch(path, params):
        body = FIXTURE.read_text(encoding="utf-8").replace("Espanyol", "Espanyol Barcelona")
        return ApiResponse(body.encode(), {"x-requests-last": "2"})

    with caplog.at_level(logging.WARNING):
        run(LA_LIGA, now=NOW, fetch=fetch, **paths)

    warnings = [r.getMessage() for r in caplog.records if "no alias" in r.getMessage()]
    assert len(warnings) == 1
    assert "Espanyol Barcelona" in warnings[0]


def test_main_reports_a_missing_key_without_a_traceback(monkeypatch, capsys):
    def no_key(*args, **kwargs):
        raise OddsApiError("ODDS_API_KEY is not set")

    monkeypatch.setattr("vba.data.odds_ingest.run", no_key)

    assert main([]) == 1
    assert "ODDS_API_KEY is not set" in capsys.readouterr().err
