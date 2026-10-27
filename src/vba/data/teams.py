"""Canonical teams and their per-source aliases, seeded from versioned CSV files."""

import csv
from pathlib import Path

import duckdb

SEEDS_DIR = Path(__file__).parent / "seeds"


def _read_seed(name: str) -> list[dict[str, str]]:
    with (SEEDS_DIR / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_seeds(con: duckdb.DuckDBPyConnection) -> None:
    """Replace the contents of `teams` and `team_aliases` with the seed CSVs.

    The CSVs are the source of truth, so every call rebuilds both tables: fixing an
    alias in the CSV takes effect the next time the schema is created. Runs in one
    transaction, so a bad seed leaves the previous contents untouched.
    """
    teams = _read_seed("teams.csv")
    aliases = _read_seed("team_aliases.csv")

    team_ids = {t["team_id"] for t in teams}
    unknown = sorted({a["team_id"] for a in aliases} - team_ids)
    if unknown:
        raise ValueError(f"team_aliases.csv refers to teams missing from teams.csv: {unknown}")

    con.begin()
    try:
        con.execute("DELETE FROM team_aliases")
        con.execute("DELETE FROM teams")
        con.executemany(
            "INSERT INTO teams (team_id, name, country) VALUES (?, ?, ?)",
            [(t["team_id"], t["name"], t["country"]) for t in teams],
        )
        con.executemany(
            "INSERT INTO team_aliases (source, alias, team_id) VALUES (?, ?, ?)",
            [(a["source"], a["alias"], a["team_id"]) for a in aliases],
        )
        con.commit()
    except Exception:
        con.rollback()
        raise
