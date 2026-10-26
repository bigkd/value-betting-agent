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

## Dixon-Coles as the base model

- **Alternatives:** independent Poisson, Elo ratings, machine learning models.
- **Reason:** it is the standard football score model: Poisson goals with attack/defence strengths, a low-score correction and time decay. It is interpretable and gives full scoreline probabilities, so 1X2 and other markets come from the same fit. It also sets a baseline that other models must beat in the backtest.

## ruff instead of flake8 + black

- **Alternatives:** flake8 + black + isort.
- **Reason:** one tool for linting, import sorting and formatting, configured in `pyproject.toml`, and much faster.

## Development assisted by Claude Code

- **Alternatives:** writing everything by hand.
- **Reason:** the agent writes the code in small steps while the author directs and reviews each change. Working rules are in [CLAUDE.md](../CLAUDE.md).
