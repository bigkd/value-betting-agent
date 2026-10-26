# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Value Betting Agent (`vba`) is a football value betting system: it estimates match outcome probabilities with a Dixon-Coles model, compares them with bookmaker odds to find value bets, and exposes the results through an API and a Claude agent.

Roadmap:

1. Data: ingest and store matches and odds.
2. Model: Dixon-Coles model + backtest.
3. API + agent + MCP server.
4. Dashboard (React/TypeScript).

## Commands

Package manager is `uv` (Python >=3.12, `src/` layout, module name `vba`).

- Install: `uv sync`
- Test all: `uv run pytest`
- Single test: `uv run pytest tests/test_smoke.py::test_package_has_version`
- Lint: `uv run ruff check` (add `--fix` to autofix)
- Format: `uv run ruff format`

CI (`.github/workflows/ci.yml`) runs `uv sync --locked`, `ruff check`, `ruff format --check` and `pytest` on pushes and PRs to `main`, so keep `uv.lock` in sync with `pyproject.toml`.

## Structure

Under `src/vba/`:

- `data/`: fetching, cleaning and storing matches and odds.
- `model/`: Dixon-Coles model, fitting.
- `betting/`: odds conversion, edge/value computation,staking and backtesting.
- `api/`: HTTP API exposing predictions and value bets.
- `agent/`: Claude agent that reasons over the model and betting outputs.
- `mcp_server/`: MCP server exposing the project's tools to the agent.

## Conventions

- Type hints on public functions; use `pathlib` for paths.
- Code, identifiers and commit messages in English; explanations to the user in Spanish.
- Tests live in `tests/` and must not access the network; use fixtures in `tests/fixtures/`.
- Do not add dependencies without asking first.

## Workflow

- Propose a plan before any change that touches more than one file.
- Make small commits using Conventional Commits; never push.
- Never read or commit `.env` or any keys.

## Working with the user

- The user comes from Java and is learning Python: briefly explain new Python idioms.
- Claude writes the code and the user reviews it: work in small steps (one function or one file at a time) and explain what each piece does and why before moving on.
- In `src/vba/model` and `src/vba/betting`, go even slower: explain the mathematical idea before the code and include a numeric example that can be checked by hand.

## Environment

Windows + PowerShell.
