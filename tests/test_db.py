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
