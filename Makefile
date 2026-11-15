VENV   := .venv
PYTHON := python3
PIP    := $(VENV)/bin/pip
FLASK  := $(VENV)/bin/flask
RUFF   := $(VENV)/bin/ruff

.PHONY: run venv install lint format fix

run:
	$(FLASK) run --port 5095

venv:
	$(PYTHON) -m venv $(VENV)

install:
	@test -d $(VENV) || $(MAKE) venv
	$(PIP) install -r requirements.txt

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) format .

fix:
	$(RUFF) check --fix .
	$(RUFF) format .
