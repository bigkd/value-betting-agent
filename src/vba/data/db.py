"""DuckDB connection and schema for historical matches and odds."""

from pathlib import Path

import duckdb

from vba.data.teams import load_seeds

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
    -- never modified. Canonical ids come from the matches_with_team_ids view.
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

_TEAMS_DDL = """
CREATE TABLE IF NOT EXISTS teams (
    team_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    country VARCHAR NOT NULL
)
"""

# One row per spelling a source uses. The foreign key to teams is checked when the
# seeds are loaded (see vba.data.teams) rather than declared here.
_TEAM_ALIASES_DDL = """
CREATE TABLE IF NOT EXISTS team_aliases (
    source VARCHAR NOT NULL,
    alias VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    PRIMARY KEY (source, alias)
)
"""

# matches stays untouched; canonical ids are looked up at query time. LEFT JOIN keeps
# matches whose team has no alias (ids are NULL) instead of silently dropping them.
_MATCHES_VIEW_DDL = """
CREATE OR REPLACE VIEW matches_with_team_ids AS
SELECT m.*, h.team_id AS home_team_id, a.team_id AS away_team_id
FROM matches m
LEFT JOIN team_aliases h ON h.source = 'football-data' AND h.alias = m.home_team
LEFT JOIN team_aliases a ON a.source = 'football-data' AND a.alias = m.away_team
"""


def connect(path: Path | str = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open the database, creating its folder if needed. Use ":memory:" for tests."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def create_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Create the tables if they do not exist yet and reload the team seeds.

    Safe to call repeatedly."""
    con.execute(_MATCHES_DDL)
    con.execute(_ODDS_DDL)
    con.execute(_TEAMS_DDL)
    con.execute(_TEAM_ALIASES_DDL)
    con.execute(_MATCHES_VIEW_DDL)
    load_seeds(con)
