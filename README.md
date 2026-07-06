# Understanding the ELO rating system

A practical example of the [ELO rating system](https://en.wikipedia.org/wiki/Elo_rating_system)
applied to **English Premier League** football results, in Python.

📖 Read the accompanying article on Medium:
[Understanding the ELO rating system — a practical example on the English Premier League using Python](https://kristfmenyhrt.medium.com/understanding-the-elo-rating-system-a-practical-example-on-the-english-premier-league-using-python-59d56ea19d9d)

## What's inside

- [`elo.py`](elo.py) — the reusable, tested ELO + league-table logic.
- [`elo_pl.ipynb`](elo_pl.ipynb) — the walkthrough notebook (imports from `elo.py`).
- [`data/pl/`](data/pl/) — Premier League match results (seasons 2017/18–2022/23),
  from [football-data.co.uk](https://www.football-data.co.uk/englandm.php).
- [`tests/`](tests/) — tests for the ELO maths and league-table logic.

```
pl_elo_score/
├── elo.py            # core logic (loading, league tables, ELO)
├── elo_pl.ipynb      # narrated walkthrough
├── tests/            # pytest suite
├── data/pl/          # season CSVs
├── pyproject.toml    # dependencies (managed by uv)
└── Makefile          # convenience commands
```

## Getting started

This project uses [uv](https://docs.astral.sh/uv/) to manage its environment.

```bash
# 1. Install dependencies into a local .venv (uv creates it for you)
uv sync

# 2a. Explore the notebook
uv run jupyter lab elo_pl.ipynb

# 2b. ...or run the pipeline straight from the module
uv run python elo.py

# 3. Run the tests
uv run pytest
```

There is also a `Makefile` with shortcuts: `make setup`, `make test`, `make run`,
`make notebook`.

## Use it as a library

The logic is importable from `elo.py`, so you can compute ratings without the notebook:

```python
import elo

results = elo.read_results("data/pl")
table = elo.create_elo_league_table(results, default_elo=1400)
final, history = elo.update_elo_league_table(
    table, results, k_value=40, weight=400, home_field_advantage=60
)
print(final.sort_values("elo", ascending=False)[["team", "elo", "points"]].head())
```

## How it works

1. **Load** every season CSV in `data/pl/` and keep the columns that matter:
   date, home/away team, goals and the full-time result (`H`/`A`/`D`).
2. **Build a league table** that is replayed match by match, tracking points,
   wins/draws/losses, goals and each team's ELO rating.
3. For each match, compute the **expected** result from the two teams' ratings
   (optionally adding a home-field advantage) and compare it against what
   **actually** happened. The rating moves proportionally to the surprise,
   scaled by the `k` factor.
4. **Visualise** the final standings and how ELO ratings evolve over time.

Key parameters you can tune (see `elo.py`):

| Parameter              | Meaning                                             | Default |
| ---------------------- | --------------------------------------------------- | ------- |
| `default_elo`          | Starting rating for every team                      | 1500    |
| `k_value`              | How strongly one match moves a rating               | 40      |
| `weight`               | Rating spread (larger = flatter probabilities)      | 400     |
| `home_field_advantage` | Rating points added to the home team when predicting| 50      |
