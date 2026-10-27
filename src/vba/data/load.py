"""Idempotent load of one league-season CSV into DuckDB."""

import logging
from pathlib import Path

import duckdb

from vba.data.odds_mapping import unmapped_odds_columns
from vba.data.odds_rows import parse_odds
from vba.data.parse import parse_match, read_rows

logger = logging.getLogger(__name__)


def _insert(con: duckdb.DuckDBPyConnection, table: str, records: list[dict[str, object]]) -> None:
    if not records:
        return
    columns = list(records[0])
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    con.executemany(sql, [[record[c] for c in columns] for record in records])


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
