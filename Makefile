.PHONY: setup install test lint format clean docker-build docker-up docker-down migrate init-models run run-prod help

VENV = venv
PYTHON = $(VENV)/Scripts/python.exe
PIP = $(VENV)/Scripts/pip.exe

# Development
setup: $(VENV)
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

$(VENV):
	python -m venv $(VENV)

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
	@if exist $(VENV) rmdir /s /q $(VENV)
	@for /r %%i in (*.pyc *.pyo *.pyd) do del /q %%i
	@for /d /r %%i in (__pycache__ *.egg-info *.egg .pytest_cache .mypy_cache htmlcov) do if exist %%i rmdir /s /q %%i
	@if exist .coverage del /q .coverage

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

# Development server
run:
	$(PYTHON) -m flask run

run-prod:
	$(PYTHON) -m gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 "app:create_app()"

# Help
help:
	@echo Available commands:
	@echo   setup        - Set up development environment
	@echo   install      - Install dependencies
	@echo   test         - Run tests
	@echo   lint         - Run linters
	@echo   format       - Format code
	@echo   clean        - Clean up development files
	@echo   docker-build - Build Docker images
	@echo   docker-up    - Start Docker containers
	@echo   docker-down  - Stop Docker containers
	@echo   migrate      - Run database migrations
	@echo   init-models  - Initialize AI models
	@echo   run          - Run development server
	@echo   run-prod     - Run production server
	@echo   help         - Show this help message
