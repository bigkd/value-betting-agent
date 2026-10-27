"""Idempotent load of one league-season CSV into DuckDB."""

import json
import logging
import tempfile
from pathlib import Path

import duckdb

from vba.data.odds_mapping import unmapped_odds_columns
from vba.data.odds_rows import parse_odds
from vba.data.parse import parse_match, read_rows

logger = logging.getLogger(__name__)


def _insert(con: duckdb.DuckDBPyConnection, table: str, records: list[dict[str, object]]) -> None:
    """Bulk insert through a temporary NDJSON file read by DuckDB.

    executemany sends one statement per row (~20 s for a season of odds); letting
    DuckDB read a file loads the same rows in a fraction of a second. NDJSON keeps
    NULLs distinct from empty strings and escapes any character in team names.
    """
    if not records:
        return
    columns = list(records[0])
    types = dict(
        con.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ?",
            [table],
        ).fetchall()
    )
    column_types = ", ".join(f"'{c}': '{types[c]}'" for c in columns)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{table}.ndjson"
        with path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, default=str) + "\n")  # dates -> ISO strings
        con.execute(
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"SELECT {', '.join(columns)} FROM read_json(?, format = 'newline_delimited', "
            f"columns = {{{column_types}}})",
            [path.as_posix()],
        )


def load_season(
    con: duckdb.DuckDBPyConnection, league: str, season: str, csv_path: Path
) -> tuple[int, int]:
    """Replace everything stored for (league, season) with the CSV contents.

    Runs in one transaction: delete + insert, so running it twice leaves the same
    rows. If anything fails the database stays as it was. Returns the number of
    (matches, odds) rows loaded.
    """
    rows = read_rows(csv_path)
    if rows:
        unmapped = unmapped_odds_columns(rows[0])
        if unmapped:
            logger.warning(
                "%s %s: %d columns look like odds but are not in ODDS_COLUMNS and were ignored: %s",
                league,
                season,
                len(unmapped),
                ", ".join(unmapped),
            )

    matches: list[dict[str, object]] = []
    odds: list[dict[str, object]] = []
    for row in rows:
        match = parse_match(row, league, season)
        matches.append(match)
        odds.extend(parse_odds(row, str(match["match_id"])))

    con.begin()
    try:
        # odds has no league/season column, so it is deleted through its matches.
        con.execute(
            "DELETE FROM odds WHERE match_id IN "
            "(SELECT match_id FROM matches WHERE league = ? AND season = ?)",
            [league, season],
        )
        con.execute("DELETE FROM matches WHERE league = ? AND season = ?", [league, season])
        _insert(con, "matches", matches)
        _insert(con, "odds", odds)
        con.commit()
    except Exception:
        con.rollback()
        raise
    return len(matches), len(odds)
