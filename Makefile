# Common tasks. Run `make help` to list them.
PYTHON_BOOTSTRAP ?= python3.11
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: help setup test test-network lint format data build check report capture ppa weather prices scenarios pricing hedging memo app all docs notebook notebook-run clean

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
	$(PY) -m ruff check src tests app

format:  ## auto-fix what ruff can fix
	$(PY) -m ruff check --fix src tests

data:  ## download raw data that is not cached yet
	$(PY) -m ppa_lab fetch

build:  ## build processed datasets from the raw cache
	$(PY) -m ppa_lab build

check:  ## run data-quality checks (fails on any FAIL)
	$(PY) -m ppa_lab check

report:  ## write reports/step01_market_data.md and figures
	$(PY) -m ppa_lab report

capture:  ## write reports/step02_capture_prices.md and figures
	$(PY) -m ppa_lab capture

ppa:  ## write reports/step03_ppa_structures.md and figures (PPA back-test)
	$(PY) -m ppa_lab ppa

weather:  ## ERA5 weather per site -> park generation -> reports/step04_generation.md
	$(PY) -m ppa_lab weather

prices:  ## calibrate + validate the price model -> reports/step05_price_model.md
	$(PY) -m ppa_lab prices

scenarios:  ## joint weather x price scenarios -> reports/step06_joint_scenarios.md
	$(PY) -m ppa_lab scenarios

pricing:  ## price the PPAs: structures, risk premia, price stack -> reports/step07_ppa_pricing.md
	$(PY) -m ppa_lab pricing

memo:  ## one-page management memo + reports/results.json for the dashboard
	$(PY) -m ppa_lab memo

app:  ## open the dashboard (installs Streamlit into .venv once)
	$(PY) -m pip install --quiet -e ".[app]"
	$(PY) -m streamlit run app/streamlit_app.py

hedging:  ## hedging with power futures -> reports/step08_hedging.md
	$(PY) -m ppa_lab hedging

all: data build check report capture ppa weather prices scenarios pricing hedging memo  ## the whole pipeline (Steps 1-9)

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
