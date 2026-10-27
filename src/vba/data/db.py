"""DuckDB connection and schema for historical matches and odds."""

from pathlib import Path

import duckdb

DEFAULT_DB_PATH = Path("data/vba.duckdb")

# Each stat becomes a home_<stat> / away_<stat> column pair.
STAT_SUFFIXES = ("shots", "shots_on_target", "corners", "fouls", "yellow", "red")

_STAT_COLUMNS = ",\n    ".join(
    f"{side}_{stat} INTEGER" for stat in STAT_SUFFIXES for side in ("home", "away")
)

_MATCHES_DDL = f"""
CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR PRIMARY KEY,
    league VARCHAR NOT NULL,
    season VARCHAR NOT NULL,
    date DATE NOT NULL,
    -- Team names are stored exactly as football-data.co.uk writes them and are
    -- never modified. Name normalization (issue #6) will add new columns.
    home_team VARCHAR NOT NULL,
    away_team VARCHAR NOT NULL,
    ht_home_goals INTEGER,
    ht_away_goals INTEGER,
    ft_home_goals INTEGER,
    ft_away_goals INTEGER,
    {_STAT_COLUMNS},
    referee VARCHAR
)
"""

# Long format: one row per match + bookmaker + market + selection + line + closing flag.
# No primary key: idempotency comes from delete + insert per (league, season).
_ODDS_DDL = """
CREATE TABLE IF NOT EXISTS odds (
    match_id VARCHAR NOT NULL,
    bookmaker VARCHAR NOT NULL,
    market VARCHAR NOT NULL,
    selection VARCHAR NOT NULL,
    line DOUBLE,  -- NULL for markets without a line (1x2)
    is_closing BOOLEAN NOT NULL,
    odds DOUBLE NOT NULL
)
"""


def connect(path: Path | str = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open the database, creating its folder if needed. Use ":memory:" for tests."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def create_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the tables if they do not exist yet (safe to call repeatedly)."""
    con.execute(_MATCHES_DDL)
    con.execute(_ODDS_DDL)
