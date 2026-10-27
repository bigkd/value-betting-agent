# Decisions

Short log of key technical decisions.

## uv instead of pip or poetry

- **Alternatives:** pip + venv, poetry.
- **Reason:** one fast tool for Python versions, virtualenvs, dependencies and a lockfile. CI reproduces the environment with `uv sync --locked`.

## src layout

- **Alternatives:** package at the repository root.
- **Reason:** tests run against the installed package, not the working directory, which catches packaging mistakes early.

## DuckDB instead of PostgreSQL

- **Alternatives:** PostgreSQL, SQLite.
- **Reason:** the workload is analytical (aggregations over historical matches) and single-user. DuckDB is embedded, needs no server and is columnar and fast for this. Revisit if the API needs concurrent writers.

## Ingestion: stdlib download and CSV parsing, delete + insert per season

- **Alternatives:** `httpx` and pandas for download and parsing; upsert with a primary key on `odds`.
- **Reason:** the download is a plain GET and the CSVs change columns between seasons, so reading rows with `csv` and filling missing columns with NULL is more predictable than type inference. Only `duckdb` was added as a dependency. Idempotency comes from deleting and reinserting each (league, season) in one transaction, which avoids a key over a nullable `line`.
- Bulk loading uses a temporary NDJSON file read by DuckDB: `executemany` took about 21 s for 45,000 odds rows, the file approach about 0.2 s. Betbrain (`Bb*`) and market (`Max*`/`Avg*`) aggregates are kept as separate bookmakers because they come from different sets of bookmakers.

## Closing-line reference for CLV: Pinnacle, then Betfair Exchange, then market average

- **Alternatives:** Pinnacle only; market average only.
- **Context:** football-data.co.uk stopped publishing Pinnacle odds midway through 2025-26 and has none in 2026-27. Betfair Exchange (`betfair_exchange`) has closing odds since 2024-25, including the current season. The market average (`market_avg`) is available in all seasons from 2019-20.
- **Decision:** the closing reference for CLV is Pinnacle in the historical backtest (up to 2024-25, the last season with complete Pinnacle data) and Betfair Exchange from then on, with the market average as a fallback when neither has a price for a match. Pinnacle remains the best sharp reference where it exists, so it is not dropped for the older seasons just to keep one source everywhere.
- **Configurable:** the reference is a setting, not a constant in the code: an ordered list of bookmakers (for example `pinnacle, betfair_exchange, market_avg`), where each match uses the first one that has closing odds for the market. The ingestion keeps all bookmakers, so changing the reference needs no reload.
- **Consequence:** CLV measured against different references is not strictly comparable across seasons. Reports must say which reference each figure used. Tracked in the issue "Configurable closing-line reference for CLV".

## Team names: CSV seeds reloaded on every run, ids through a view

- **Alternatives:** rewriting `matches.home_team`/`away_team` with canonical names; storing ids in `matches` at load time; seeds inserted only when missing.
- **Reason:** raw names stay untouched, so the source data is never lost. Ids come from a view joining `team_aliases`, and the seed CSVs (versioned in the package, not in the git-ignored `data/`) are reloaded each time the schema is created, so fixing an alias needs no reload of matches. Unknown names are reported (ingestion warning and `vba.data.team_check`) instead of creating teams silently.

## Dixon-Coles as the base model

- **Alternatives:** independent Poisson, Elo ratings, machine learning models.
- **Reason:** it is the standard football score model: Poisson goals with attack/defence strengths, a low-score correction and time decay. It is interpretable and gives full scoreline probabilities, so 1X2 and other markets come from the same fit. It also sets a baseline that other models must beat in the backtest.

## ruff instead of flake8 + black

- **Alternatives:** flake8 + black + isort.
- **Reason:** one tool for linting, import sorting and formatting, configured in `pyproject.toml`, and much faster.

## Development assisted by Claude Code

- **Alternatives:** writing everything by hand.
- **Reason:** the agent writes the code in small steps while the author directs and reviews each change. Working rules are in [CLAUDE.md](../CLAUDE.md).

## Context signals on top of the statistical model

- **Alternatives:** statistical model only; automatic probability adjustment from news.
- **Reason:** Dixon-Coles only sees past results, so it misses information such as suspensions, motivation, rotation, injuries and line-ups. Signals are split in three levels by how they can be validated:
  - Levels 1 and 2 come from data, so they are validated with a historical backtest.
  - Level 3 (news read by the agent) cannot be backtested: there is no reliable historical record of what was known and when, and an LLM may already have seen the outcomes. It is measured going forward with closing line value (CLV), logging odds taken and closing odds for every signal and bet.
  - Because of that, level 3 signals do not adjust probabilities automatically. The agent flags markets to review and explains why, and the user decides.
- Football comes first. NBA player props is an optional phase 6.
