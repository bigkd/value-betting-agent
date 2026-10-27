"""Canonical teams and their per-source aliases, seeded from versioned CSV files."""

import csv
import re
import unicodedata
from pathlib import Path

import duckdb

SEEDS_DIR = Path(__file__).parent / "seeds"


class UnknownTeamError(LookupError):
    """A source used a team name that has no alias."""


def normalize_name(name: str) -> str:
    """Lowercase, strip accents, drop apostrophes and punctuation, collapse spaces.

    "Atlético  de Madrid" -> "atletico de madrid", "Nott'm Forest" -> "nottm forest".
    """
    # NFKD splits "é" into "e" + a combining accent, which category "Mn" lets us drop.
    decomposed = unicodedata.normalize("NFKD", name)
    unaccented = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    no_apostrophes = re.sub(r"['’`]", "", unaccented.lower())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", no_apostrophes).split())


def resolve_team(con: duckdb.DuckDBPyConnection, source: str, name: str) -> str:
    """Return the canonical team_id for `name` as written by `source`.

    Both the name and the stored aliases are normalized before comparing, so
    "ATLETICO MADRID" matches an alias "Atletico Madrid". Raises UnknownTeamError
    instead of creating teams silently.
    """
    rows = con.execute(
        "SELECT alias, team_id FROM team_aliases WHERE source = ?", [source]
    ).fetchall()
    by_key: dict[str, str] = {}
    for alias, team_id in rows:
        key = normalize_name(alias)
        if by_key.setdefault(key, team_id) != team_id:
            raise ValueError(f"{source} aliases collide after normalization: {alias!r}")
    try:
        return by_key[normalize_name(name)]
    except KeyError:
        raise UnknownTeamError(f"No alias for {name!r} from source {source!r}") from None


def _read_seed(name: str) -> list[dict[str, str]]:
    with (SEEDS_DIR / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def unknown_team_names(
    con: duckdb.DuckDBPyConnection, league: str | None = None, season: str | None = None
) -> list[str]:
    """Football-data team names in `matches` that have no alias, sorted.

    Optionally restricted to one league and/or season.
    """
    conditions = []
    params: list[str] = []
    if league is not None:
        conditions.append("league = ?")
        params.append(league)
    if season is not None:
        conditions.append("season = ?")
        params.append(season)
    where = "".join(f" AND {c}" for c in conditions)
    rows = con.execute(
        f"""
        SELECT home_team AS name FROM matches_with_team_ids
        WHERE home_team_id IS NULL{where}
        UNION
        SELECT away_team FROM matches_with_team_ids
        WHERE away_team_id IS NULL{where}
        ORDER BY name
        """,
        params * 2,
    ).fetchall()
    return [row[0] for row in rows]


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
