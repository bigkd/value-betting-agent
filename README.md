# Value Betting Agent

[![CI](https://github.com/bigkd/value-betting-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/bigkd/value-betting-agent/actions/workflows/ci.yml)

A football value betting system: it estimates match outcome probabilities with a Dixon-Coles model and compares them with bookmaker odds to find value bets.

**Status:** Phase 1 (project setup) complete. Phase 2 in progress: historical results and odds from football-data.co.uk load into DuckDB.

## Planned features

- **Data:** ingest and store historical matches, xG and bookmaker odds.
- **Model:** fit a Dixon-Coles model to estimate the probability of each match outcome, and backtest it.
- **Value bets:** convert odds to implied probabilities and flag bets where the model's probability beats the market's.
- **Context signals:** add information the statistical model does not see, in three levels:
  - Level 1: signals computed from data and validated by backtest: suspensions from card accumulation (including deliberately picking up a fifth yellow), motivation from the league table (nothing at stake, already champion or relegated) and rotation risk (rest days, important upcoming match).
  - Level 2: injuries, suspensions and line-ups from a structured API.
  - Level 3: the agent reads news and turns it into structured signals (player, status, confidence, source). It does not adjust probabilities on its own: it flags markets to review and explains why, and the user decides.
- **CLV tracking:** log every signal and bet with the odds taken and the closing odds, to measure closing line value (CLV).
- **Agent:** a Claude agent that reasons over the model and betting outputs, using tools exposed through an MCP server.

## Tech stack

- Python 3.12+, managed with [uv](https://docs.astral.sh/uv/)
- DuckDB for storage
- pytest, ruff and GitHub Actions for tests, lint and CI
- Claude + MCP for the agent (planned)
- React + TypeScript for the dashboard (planned)

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/getting-started/installation/) (it installs the right Python version if needed).

```bash
git clone https://github.com/bigkd/value-betting-agent.git
cd value-betting-agent
uv sync
uv run pytest
```

Lint and format: `uv run ruff check` and `uv run ruff format`.

Load the historical data (La Liga and Premier League, 2018-19 to the current season) into `data/vba.duckdb`:

```bash
uv run python -m vba.data.ingest
```

See [docs/data-ingestion.md](docs/data-ingestion.md) for the tables and the odds column mapping.

## Roadmap

- [x] Phase 1: project setup (tooling, CI, agent conventions)
- [ ] Phase 2: data ingestion and storage (matches, xG, odds) and level 2 signals (injuries, suspensions, line-ups from a structured API)
- [ ] Phase 3: Dixon-Coles model, value engine, backtest and level 1 signals (cards, motivation, rotation)
- [ ] Phase 4: API, Claude agent and MCP server, with level 3 signals (news read by the agent, CLV tracking)
- [ ] Phase 5: dashboard (React/TypeScript)
- [ ] Phase 6 (optional): NBA player props

The project is football-first; phase 6 only starts if the football system works.

See [docs/architecture.md](docs/architecture.md) for the system design and [docs/decisions.md](docs/decisions.md) for the reasoning behind key choices.

## How this project is built

This project is developed with [Claude Code](https://claude.com/claude-code). The agent writes the code; the author directs the work, reviews every change and makes the design decisions. The rules the agent follows are in [CLAUDE.md](CLAUDE.md).

## License

[MIT](LICENSE)
