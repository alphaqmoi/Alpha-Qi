.PHONY: setup install test lint format clean docker-build docker-up docker-down migrate init-models run run-prod help pre-commit

VENV ?= venv
OS := $(shell uname 2>/dev/null || echo Windows)
USE_POETRY := $(shell if command -v poetry >/dev/null 2>&1; then echo true; else echo false; fi)
WORKON_HOME := $(WORKON_HOME)

ifeq ($(OS),Windows)
	PYTHON := $(VENV)/Scripts/python.exe
	PIP := $(VENV)/Scripts/pip.exe
else
	PYTHON := $(VENV)/bin/python
	PIP := $(VENV)/bin/pip
endif

# Development setup
setup: $(VENV)
ifeq ($(USE_POETRY),true)
	@echo "📦 Poetry detected. Installing with Poetry..."
	poetry install
	poetry run pre-commit install
	poetry run pre-commit autoupdate
else
	@echo "📦 Installing requirements..."
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	@echo "🧼 Installing pre-commit hooks..."
	$(PIP) install pre-commit
	pre-commit install
	pre-commit autoupdate
endif
	@echo "✅ Development environment is ready."

# Create virtualenv (skip if poetry or virtualenvwrapper)
$(VENV):
ifeq ($(USE_POETRY),true)
	@echo "🎯 Using Poetry — skipping manual venv setup"
else ifdef WORKON_HOME
	@echo "🌐 Detected virtualenvwrapper in $(WORKON_HOME). Activate manually."
else
	python -m venv $(VENV)
endif

install:
	$(PIP) install -r requirements.txt

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m flake8
	$(PYTHON) -m mypy .
	$(PYTHON) -m black --check .
	$(PYTHON) -m isort --check-only .

format:
	$(PYTHON) -m black .
	$(PYTHON) -m isort .

clean:
	@if [ -d "$(VENV)" ]; then rm -rf $(VENV); fi
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d \( -name "*.egg-info" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name "htmlcov" \) -exec rm -rf {} +
	@rm -f .coverage

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Database
migrate:
	$(PYTHON) -m flask db upgrade

init-models:
	$(PYTHON) scripts/init_models.py

# Dev servers
run:
	$(PYTHON) -m flask run

run-prod:
	$(PYTHON) -m gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 "app:create_app()"

# Pre-commit (manual run)
pre-commit:
	pre-commit run --all-files

# Help
help:
	@echo "Available commands:"
	@echo "  setup        - Set up development environment (supports Poetry, venv, or virtualenvwrapper)"
	@echo "  install      - Install runtime dependencies"
	@echo "  test         - Run tests with pytest"
	@echo "  lint         - Run flake8, mypy, black --check, isort --check"
	@echo "  format       - Auto-format code with black and isort"
	@echo "  clean        - Remove virtualenv and caches"
	@echo "  docker-build - Build Docker containers"
	@echo "  docker-up    - Start Docker containers"
	@echo "  docker-down  - Stop Docker containers"
	@echo "  migrate      - Run database migrations"
	@echo "  init-models  - Run scripts/init_models.py"
	@echo "  run          - Start Flask development server"
	@echo "  run-prod     - Start Gunicorn production server"
	@echo "  pre-commit   - Run pre-commit hooks manually"
	@echo "  help         - Show this help message"
