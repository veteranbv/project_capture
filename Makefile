.PHONY: help install install-dev test lint format type-check security clean build docs

# Default target
.DEFAULT_GOAL := help

# Python interpreter
PYTHON := python3

# Colors for terminal output
COLOR_RESET   = \033[0m
COLOR_BOLD    = \033[1m
COLOR_GREEN   = \033[32m
COLOR_YELLOW  = \033[33m

help: ## Show this help message
	@echo '$(COLOR_BOLD)Usage:$(COLOR_RESET)'
	@echo '  make $(COLOR_GREEN)<target>$(COLOR_RESET)'
	@echo ''
	@echo '$(COLOR_BOLD)Targets:$(COLOR_RESET)'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(COLOR_GREEN)%-15s$(COLOR_RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install the package in production mode
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .

install-dev: ## Install the package with development dependencies
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev,docs]"
	pre-commit install

test: ## Run all tests with coverage
	pytest tests -v --cov=project_capture --cov-report=term-missing --cov-report=html

test-unit: ## Run unit tests only
	pytest tests/unit -v -m unit

test-integration: ## Run integration tests only
	pytest tests/integration -v -m integration

lint: ## Run all linting checks
	ruff check src tests
	mypy src
	bandit -r src

format: ## Format code with ruff
	ruff format src tests
	ruff check --fix src tests

type-check: ## Run type checking with mypy
	mypy src --show-error-codes

security: ## Run security checks
	bandit -r src -ll
	safety check
	pip-audit

clean: ## Clean up build artifacts and cache files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type f -name "*.pyc" -delete

build: clean ## Build distribution packages
	$(PYTHON) -m build
	docs: ## Build documentation
	cd docs && make clean && make html

serve-docs: docs ## Build and serve documentation locally
	cd docs && python -m http.server --directory _build/html 8000

run-cli: ## Run the CLI application
	$(PYTHON) -m project_capture.cli.main

run-web: ## Run the web application
	streamlit run src/project_capture/web/app.py

check-all: lint type-check security test ## Run all checks (lint, type-check, security, test)

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

update-deps: ## Update all dependencies to latest versions
	$(PYTHON) -m pip install --upgrade pip pip-tools
	pip-compile --upgrade -o requirements.txt pyproject.toml
	pip-compile --upgrade --extra dev -o requirements-dev.txt pyproject.toml

watch-test: ## Run tests in watch mode
	ptw -- -vv

profile: ## Profile the application
	$(PYTHON) -m cProfile -o profile.stats src/project_capture/cli/main.py
	$(PYTHON) -m pstats profile.stats