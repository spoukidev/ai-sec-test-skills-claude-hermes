# Common tasks. Uses the project virtualenv if present (.venv), else the active Python.
PY ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
AISEC = $(PY) -m aisec
SAMPLE_JSONL = results/sample/sample_run.jsonl

.PHONY: help install test lint format report sample demo validate payloads clean

help:
	@echo "make install   - create .venv and install (editable) with dev deps"
	@echo "make test      - run pytest"
	@echo "make lint      - ruff lint + format check"
	@echo "make report    - regenerate results/sample/report.{md,html} + docs/img/sample_chart.svg from $(SAMPLE_JSONL)"
	@echo "make sample    - regenerate $(SAMPLE_JSONL) with the offline mock client (synthetic data)"
	@echo "make demo      - offline mock run of the full suite on claude+hermes, then a report"
	@echo "make validate  - validate skills/payloads/config and check corpus size targets"

install:
	uv venv .venv --python 3.11 || python3 -m venv .venv
	uv pip install --python .venv/bin/python -e ".[dev]" || .venv/bin/pip install -e ".[dev]"

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .

report:
	$(AISEC) report $(SAMPLE_JSONL) -o results/sample/report.md --html results/sample/report.html \
		--svg docs/img/sample_chart.svg --title "Sample report (SYNTHETIC mock data)"

sample:
	rm -rf results/.sample_tmp
	$(AISEC) run --models claude,hermes --suite full --mock -o results/.sample_tmp
	cp results/.sample_tmp/latest.jsonl $(SAMPLE_JSONL)
	rm -rf results/.sample_tmp
	$(MAKE) report

demo:
	$(AISEC) run --models claude,hermes --suite full --mock --report

validate:
	$(AISEC) validate

payloads:
	$(PY) scripts/build_payloads.py

clean:
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info results/.sample_tmp
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
