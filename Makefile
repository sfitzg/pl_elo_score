.PHONY: setup test run notebook clean

setup:            ## Install dependencies into .venv
	uv sync

test:             ## Run the test suite
	uv run pytest

run:              ## Run the full ELO pipeline (smoke test)
	uv run python elo.py

notebook:         ## Open the walkthrough notebook
	uv run jupyter lab elo_pl.ipynb

clean:            ## Remove caches
	rm -rf .pytest_cache __pycache__ tests/__pycache__
