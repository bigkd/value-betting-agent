# Data ingestion

Historical results and odds come from [football-data.co.uk](https://www.football-data.co.uk) (leagues SP1 and E0, seasons from 2018-19 to the current one) and are stored in `data/vba.duckdb`.

## Running it

```bash
uv run python -m vba.data.ingest
```

- CSVs are cached in `data/raw/` as `{league}_{season}.csv`. Finished seasons are downloaded once; the current season is refreshed on every run because the site updates it weekly. There is a 1.5 s pause between downloads.
- A season that cannot be downloaded is skipped with a message and the run continues.
- The load is idempotent: for each (league, season) the stored rows are deleted and reinserted in one transaction, so running it twice leaves the same rows, and a failed load leaves the database untouched.
- A season loads in well under a second: rows go in through a temporary NDJSON file read by DuckDB instead of row-by-row inserts.
- `data/` is git-ignored.

## Tables

### `matches` — one row per match

| Column | Notes |
|---|---|
| `match_id` | Primary key: `{league}_{season}_{date}_{home_team}_{away_team}`, e.g. `SP1_2425_2024-10-26_Barcelona_Real Madrid`. |
| `league`, `season`, `date` | Season is the football-data code (`2425` = 2024-25). |
| `home_team`, `away_team` | Names exactly as in the CSV, never modified. Canonical ids are in the `matches_with_team_ids` view (see below). |
| `ht_*_goals`, `ft_*_goals` | Half-time and full-time goals (`ht_home_goals`, `ft_away_goals`, ...). |
| `home_/away_` `shots`, `shots_on_target`, `corners`, `fouls`, `yellow`, `red` | Match statistics. |
| `referee` | When the CSV has it. |

Any column missing from a CSV (for example the referee in 2018-19, or statistics in some leagues) is stored as NULL.

### `odds` — long format, one row per price

| Column | Notes |
|---|---|
| `match_id` | Joins to `matches`. |
| `bookmaker` | `pinnacle`, `bet365`, `bet_and_win`, ..., plus the aggregates `market_max`, `market_avg` (Max*/Avg* columns) and `betbrain_max`, `betbrain_avg` (Bb* columns, 2018-19). |
| `market` | `1x2`, `ou` (over/under 2.5) or `ah` (asian handicap). |
| `selection` | `home`/`draw`/`away`, `over`/`under`, or `home`/`away` for handicap. |
| `line` | 2.5 for `ou`, the home-team handicap for `ah` (as in the CSV), NULL for `1x2`. |
| `is_closing` | `true` for closing odds. |
| `odds` | Decimal odds. |

Example, Barcelona 2-1 Real Madrid (SP1 2024-25), a few of its rows:

| bookmaker | market | selection | line | is_closing | odds |
|---|---|---|---|---|---|
| pinnacle | 1x2 | home | NULL | false | 2.15 |
| pinnacle | 1x2 | home | NULL | true | 2.08 |
| pinnacle | ou | over | 2.5 | false | 1.85 |
| bet365 | ah | home | -0.5 | false | 1.95 |
| market_max | 1x2 | draw | NULL | false | 3.80 |

Closing 1X2 odds of Pinnacle for a season:

```sql
SELECT m.date, m.home_team, m.away_team, o.selection, o.odds
FROM odds o JOIN matches m USING (match_id)
WHERE m.league = 'SP1' AND m.season = '2425'
  AND o.bookmaker = 'pinnacle' AND o.market = '1x2' AND o.is_closing;
```

## Team names

Each source spells teams differently (`Ath Madrid`, `Man City`, `Nott'm Forest`), so every team has a canonical `team_id` (for example `atletico_madrid`).

- [`src/vba/data/seeds/teams.csv`](../src/vba/data/seeds/teams.csv): `team_id,name,country`. Names are the short press name, with accents and without FC/RCD/AFC/CF.
- [`src/vba/data/seeds/team_aliases.csv`](../src/vba/data/seeds/team_aliases.csv): `source,alias,team_id`. Only `football-data` for now.
- `create_schema` reloads both CSVs into the `teams` and `team_aliases` tables on every run, so the CSV is the source of truth: editing an alias needs no data reload.
- `matches` is not modified. The view `matches_with_team_ids` adds `home_team_id` and `away_team_id` by joining `matches` with `team_aliases` (NULL when the name has no alias):

```sql
SELECT date, home_team_id, away_team_id FROM matches_with_team_ids WHERE league = 'SP1';
```

- `resolve_team(con, source, name)` in `teams.py` returns the `team_id` ignoring case, accents and punctuation, and raises `UnknownTeamError` for unknown names. It is meant for future sources (Understat, The Odds API).

**Adding a team or alias:** add the rows to the CSVs (a new `team_id` goes in `teams.csv` first). The ingestion logs a warning listing any team name without alias, and you can check the whole database with:

```bash
uv run python -m vba.data.team_check
```

It prints the unknown names and exits with code 1 if there are any. The tests also check that every team in `tests/fixtures/` has an alias.

## Column mapping

[`src/vba/data/odds_mapping.py`](../src/vba/data/odds_mapping.py) is the single place that maps CSV odds columns to `(bookmaker, market, selection, is_closing, line)`. Prefixes follow the [football-data notes](https://www.football-data.co.uk/notes.txt) (for example `BW` is Bet&Win, not Betway). To support a new bookmaker or market, add it to the prefix tables in that file.

When a CSV has columns that look like odds but are not mapped, the load logs a warning listing them, so no data is lost silently. The check only looks at column endings (`H/D/A`, `>2.5`, `<2.5`, `AHH/AHA`), so a market with a different format (for example over/under 3.5) would not be flagged.

## Code layout (`vba.data`)

| Module | Role |
|---|---|
| `download.py` | Season codes and cached download. |
| `parse.py` | CSV reading (UTF-8 with latin-1 fallback) and `matches` records. |
| `odds_mapping.py` | Column mapping and unmapped-column detection. |
| `odds_rows.py` | One CSV row into long-format `odds` records. |
| `db.py` | Connection, schema and the team view. |
| `teams.py` | Team seeds, name normalization and lookup. |
| `team_check.py` | Lists team names without alias in the database. |
| `load.py` | Idempotent, transactional load of a season. |
| `ingest.py` | Entry point that ties everything together. |
