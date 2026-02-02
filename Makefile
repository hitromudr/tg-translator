# Makefile for tg-translator

.PHONY: help install format lint test test-backend run clean session-init deploy

# Default target
.DEFAULT_GOAL := help

# Python interpreter
VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install dependencies
	$(PIP) install -e .

dev-install: ## Install dependencies with dev tools
	$(PIP) install -e .
	$(PIP) install black isort mypy pytest pytest-cov types-requests

format: ## Format code using black and isort
	$(PYTHON) -m isort src tests
	$(PYTHON) -m black src tests

lint: ## Run static analysis (mypy, black check, isort check)
	$(PYTHON) -m black --check src tests
	$(PYTHON) -m isort --check-only src tests
	$(PYTHON) -m mypy src

test: ## Run tests
	$(PYTHON) -m pytest

test-backend: test ## Alias for test (Meta-rule compliance)

run: ## Run the Telegram bot
	$(PYTHON) -m tg_translator.main

clean: ## Clean up build artifacts and cache
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +

session-init: ## Initialize session (Meta-rule compliance)
	@echo "Session initialized. Checking git status..."
	@git status
	@echo "Checking for active tasks..."
	@ls -1 docs/tasks/current 2>/dev/null || echo "No active tasks found in docs/tasks/current."

deploy: ## Deploy using Ansible (placeholder)
	@echo "Running ansible playbook..."
	# ansible-playbook deploy/playbook.yml
