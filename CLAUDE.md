# CLAUDE.md

Guidance for working in this repository.

## What this is

An educational demo of the **ELO rating system** applied to **English Premier
League** football results. It accompanies a Medium article. Small, single-topic
repo — keep changes simple and focused.

## Layout

- `elo.py` — single source of truth for the logic (data loading, league tables,
  ELO calculation). Import from here; don't reimplement.
- `elo_pl.ipynb` — narrative walkthrough that imports from `elo.py`.
- `data/pl/*.csv` — match results (seasons 2017/18–2022/23) from
  football-data.co.uk. `read_results()` concatenates them.
- `tests/test_elo.py` — pytest suite for the ELO maths and table logic.

## Environment & commands

Uses [uv](https://docs.astral.sh/uv/). Always run tools through `uv run`.

```bash
uv sync                            # create/update .venv from pyproject.toml
uv run pytest                      # run the tests
uv run python elo.py              # run the full ELO pipeline as a smoke test
uv run jupyter lab elo_pl.ipynb   # open the notebook
```

A `Makefile` wraps these: `make setup` / `make test` / `make run` / `make notebook`.

## Conventions

- Keep `elo.py` the single implementation. If you change a function's behaviour,
  update `tests/test_elo.py` and keep the notebook in sync (it imports the
  functions, so it should just work).
- Preserve the notebook's teaching narrative (markdown cells) when editing.
- Column names in the tables (e.g. `matched_played`) are referenced across the
  notebook — rename with care and update all call sites.
- Don't over-engineer. This is a small demo, not a library or service.

## Data format

Each CSV row is one match. Relevant columns: `Date`, `HomeTeam`, `AwayTeam`,
`FTHG`/`FTAG` (full-time home/away goals), `FTR` (result: `H` home win, `A` away
win, `D` draw).
