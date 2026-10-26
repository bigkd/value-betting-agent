# Value Betting Agent

[![CI](https://github.com/bigkd/value-betting-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/bigkd/value-betting-agent/actions/workflows/ci.yml)

A football value betting system: it estimates match outcome probabilities with a Dixon-Coles model and compares them with bookmaker odds to find value bets.

**Status:** Work in progress. Current phase: 1 of 5.

## What it does

- **Data:** ingests and stores historical matches and bookmaker odds.
- **Model:** fits a Dixon-Coles model to estimate the probability of each match outcome, and backtests it.
- **Value bets:** converts odds to implied probabilities and flags bets where the model's probability beats the market's.
- **Agent:** a Claude agent reasons over the model and betting outputs, using tools exposed through an MCP server.

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

## Roadmap

- [ ] **Phase 1 (in progress):** data ingestion and storage of matches and odds
- [ ] **Phase 2:** Dixon-Coles model and backtest
- [ ] **Phase 3:** value engine (odds conversion, edge, staking)
- [ ] **Phase 4:** API, Claude agent and MCP server
- [ ] **Phase 5:** dashboard (React/TypeScript)

See [docs/architecture.md](docs/architecture.md) for the system design and [docs/decisions.md](docs/decisions.md) for the reasoning behind key choices.

## How this project is built

This project is developed with [Claude Code](https://claude.com/claude-code). The agent writes the code; the author directs the work, reviews every change and makes the design decisions. The rules the agent follows are in [CLAUDE.md](CLAUDE.md).

## License

[MIT](LICENSE)
