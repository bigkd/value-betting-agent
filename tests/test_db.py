from vba.data.db import connect, create_schema


def _columns(con, table: str) -> set[str]:
    rows = con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?", [table]
    ).fetchall()
    return {row[0] for row in rows}


def test_create_schema_creates_both_tables():
    con = connect(":memory:")
    create_schema(con)

    assert {"match_id", "home_team", "away_team", "home_shots", "away_red", "referee"} <= _columns(
        con, "matches"
    )
    assert _columns(con, "odds") == {
        "match_id",
        "bookmaker",
        "market",
        "selection",
        "line",
        "is_closing",
        "odds",
    }


def test_create_schema_is_repeatable():
    con = connect(":memory:")
    create_schema(con)
    create_schema(con)  # must not fail
    assert con.execute("SELECT count(*) FROM teams").fetchone()[0] == 63


def test_create_schema_loads_team_seeds():
    con = connect(":memory:")
    create_schema(con)

    assert _columns(con, "teams") == {"team_id", "name", "country"}
    assert _columns(con, "team_aliases") == {"source", "alias", "team_id"}
    team = con.execute(
        "SELECT t.team_id, t.name FROM team_aliases a JOIN teams t USING (team_id) "
        "WHERE a.source = 'football-data' AND a.alias = 'Ath Madrid'"
    ).fetchone()
    assert team == ("atletico_madrid", "Atlético de Madrid")


def test_seeds_are_consistent():
    con = connect(":memory:")
    create_schema(con)

    orphans = con.execute(
        "SELECT alias FROM team_aliases WHERE team_id NOT IN (SELECT team_id FROM teams)"
    ).fetchall()
    assert orphans == []
    n_aliases = con.execute("SELECT count(*) FROM team_aliases").fetchone()[0]
    n_distinct = con.execute("SELECT count(DISTINCT (source, alias)) FROM team_aliases").fetchone()
    assert n_distinct[0] == n_aliases


def test_view_adds_team_ids_and_keeps_unknown_teams():
    con = connect(":memory:")
    create_schema(con)
    for match_id, home, away in [("1", "Ath Madrid", "Man City"), ("2", "Ath Madrid", "Nobody FC")]:
        con.execute(
            "INSERT INTO matches (match_id, league, season, date, home_team, away_team) "
            "VALUES (?, 'SP1', '2425', DATE '2024-08-01', ?, ?)",
            [match_id, home, away],
        )

    rows = con.execute(
        "SELECT match_id, home_team_id, away_team_id FROM matches_with_team_ids ORDER BY match_id"
    ).fetchall()

    assert rows == [
        ("1", "atletico_madrid", "manchester_city"),
        ("2", "atletico_madrid", None),
    ]


def test_reloading_seeds_replaces_edited_rows():
    con = connect(":memory:")
    create_schema(con)
    con.execute("UPDATE team_aliases SET team_id = 'barcelona' WHERE alias = 'Betis'")

    create_schema(con)

    betis = con.execute("SELECT team_id FROM team_aliases WHERE alias = 'Betis'").fetchone()
    assert betis == ("real_betis",)


def test_create_schema_creates_odds_api_tables():
    con = connect(":memory:")
    create_schema(con)

    assert {"event_id", "league", "commence_time", "home_team_id", "away_team_id"} <= _columns(
        con, "odds_api_events"
    )
    assert _columns(con, "odds_snapshots") == {
        "snapshot_id",
        "captured_at",
        "event_id",
        "bookmaker",
        "market",
        "selection",
        "line",
        "odds",
        "bookmaker_updated_at",
    }
    assert {"snapshot_id", "credits_last", "credits_remaining", "raw_path"} <= _columns(
        con, "odds_api_requests"
    )
