"""Parse football-data.co.uk CSV rows into `matches` records."""

import csv
import io
from datetime import date, datetime
from pathlib import Path

# CSV column -> `matches` column. Columns missing from a CSV simply become NULL.
SCORE_COLUMNS = {
    "HTHG": "ht_home_goals",
    "HTAG": "ht_away_goals",
    "FTHG": "ft_home_goals",
    "FTAG": "ft_away_goals",
}
STAT_COLUMNS = {
    "HS": "home_shots",
    "AS": "away_shots",
    "HST": "home_shots_on_target",
    "AST": "away_shots_on_target",
    "HC": "home_corners",
    "AC": "away_corners",
    "HF": "home_fouls",
    "AF": "away_fouls",
    "HY": "home_yellow",
    "AY": "away_yellow",
    "HR": "home_red",
    "AR": "away_red",
}
_INT_COLUMNS = {**SCORE_COLUMNS, **STAT_COLUMNS}


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV as dicts, trying UTF-8 first and falling back to latin-1."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
    # newline="" lets the csv module handle line breaks inside quoted fields itself.
    rows = csv.DictReader(io.StringIO(text, newline=""))
    # Files often end with blank lines: keep only rows that have a date and teams.
    return [r for r in rows if r.get("Date") and r.get("HomeTeam") and r.get("AwayTeam")]


def parse_date(value: str) -> date:
    """Accept both 26/10/24 and 26/10/2024."""
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: {value!r}")


def _to_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    return int(float(value))


def parse_match(row: dict[str, str], league: str, season: str) -> dict[str, object]:
    """Build a `matches` record from a CSV row.

    home_team / away_team keep the names exactly as they come in the CSV and are
    never modified; name normalization (issue #6) will add new columns instead.
    """
    day = parse_date(row["Date"])
    home, away = row["HomeTeam"].strip(), row["AwayTeam"].strip()
    record: dict[str, object] = {
        "match_id": f"{league}_{season}_{day.isoformat()}_{home}_{away}",
        "league": league,
        "season": season,
        "date": day,
        "home_team": home,
        "away_team": away,
        "referee": (row.get("Referee") or "").strip() or None,
    }
    for csv_col, db_col in _INT_COLUMNS.items():
        record[db_col] = _to_int(row.get(csv_col))
    return record
