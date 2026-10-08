# Common tasks. Run `make help` to list them.
PYTHON_BOOTSTRAP ?= python3.11
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: help setup test test-network lint format data build check report capture all docs notebook notebook-run clean

help:  ## show this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

setup:  ## create the virtual environment and install the project (+ dev tools)
	$(PYTHON_BOOTSTRAP) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

test:  ## run the offline test suite with coverage
	$(PY) -m pytest --cov=ppa_lab --cov-report=term-missing

test-network:  ## run the contract tests against the live API
	$(PY) -m pytest -m network

lint:  ## static checks (style, imports, common bugs)
	$(PY) -m ruff check src tests

format:  ## auto-fix what ruff can fix
	$(PY) -m ruff check --fix src tests

data:  ## download raw data that is not cached yet
	$(PY) -m ppa_lab fetch

build:  ## build processed datasets from the raw cache
	$(PY) -m ppa_lab build

check:  ## run data-quality checks (fails on any FAIL)
	$(PY) -m ppa_lab check

report:  ## write reports/day01_market_data.md and figures
	$(PY) -m ppa_lab report

capture:  ## write reports/day02_capture_prices.md and figures
	$(PY) -m ppa_lab capture

all: data build check report capture  ## the whole pipeline (Day 1 + Day 2)

docs:  ## render docs/learning_track/*.md to PDF (needs Google Chrome)
	$(PY) -m pip install --quiet -e ".[docs]"
	$(PY) scripts/build_docs.py

notebook:  ## open the playground notebook in JupyterLab (installs Jupyter into .venv once)
	$(PY) -m pip install --quiet -e ".[notebook]"
	$(PY) -m jupyterlab notebooks/ppa_lab_playground.ipynb

notebook-run:  ## run every notebook cell headless and save the outputs (fails on any error)
	$(PY) -m nbconvert --to notebook --execute --inplace notebooks/ppa_lab_playground.ipynb

clean:  ## remove processed data and caches (keeps the raw downloads)
	rm -rf data/processed/* .pytest_cache .ruff_cache .coverage htmlcov
