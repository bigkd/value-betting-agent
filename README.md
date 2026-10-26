# Value Betting Agent

[![CI](https://github.com/bigkd/value-betting-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/bigkd/value-betting-agent/actions/workflows/ci.yml)

A football value betting system: it estimates match outcome probabilities with a Dixon-Coles model and compares them with bookmaker odds to find value bets.

**Status:** Phase 1 (project setup) complete. Next: data ingestion.

## Planned features

- **Data:** ingest and store historical matches, xG and bookmaker odds.
- **Model:** fit a Dixon-Coles model to estimate the probability of each match outcome, and backtest it.
- **Value bets:** convert odds to implied probabilities and flag bets where the model's probability beats the market's.
- **Agent:** a Claude agent that reasons over the model and betting outputs, using tools exposed through an MCP server.

## Tech stack

- Python 3.12+, managed with [uv](https://docs.astral.sh/uv/)
- DuckDB for storage (planned)
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

- [x] Phase 1: project setup (tooling, CI, agent conventions)
- [ ] Phase 2: data ingestion and storage (matches, xG, odds)
- [ ] Phase 3: Dixon-Coles model, value engine and backtest
- [ ] Phase 4: API, Claude agent and MCP server
- [ ] Phase 5: dashboard (React/TypeScript)

See [docs/architecture.md](docs/architecture.md) for the system design and [docs/decisions.md](docs/decisions.md) for the reasoning behind key choices.

## How this project is built

This project is developed with [Claude Code](https://claude.com/claude-code). The agent writes the code; the author directs the work, reviews every change and makes the design decisions. The rules the agent follows are in [CLAUDE.md](CLAUDE.md).

## License

[MIT](LICENSE)
