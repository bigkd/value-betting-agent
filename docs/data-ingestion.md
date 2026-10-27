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
| `home_team`, `away_team` | Names exactly as in the CSV, never modified. Normalization (issue #6) will add new columns. |
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
| `db.py` | Connection and schema. |
| `load.py` | Idempotent, transactional load of a season. |
| `ingest.py` | Entry point that ties everything together. |
