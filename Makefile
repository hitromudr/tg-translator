# Makefile for tg-translator

.PHONY: help install dev-install format lint test run clean session-init deploy logs stop-remote start-remote restart-remote remote-status

# Default target
.DEFAULT_GOAL := help

# Configuration
VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
SERVER_HOST := root@130.49.143.223
SERVICE_NAME := tg-translator

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# --- Setup & Install ---
install: ## Install dependencies
	$(PIP) install -e .

dev-install: ## Install dependencies with dev tools
	$(PIP) install -e .
	$(PIP) install black isort mypy pytest pytest-cov types-requests

session-init: ## Initialize session (Meta-rule compliance)
	@echo "Session initialized. Checking git status..."
	@git status
	@echo "Checking for active tasks..."
	@ls -1 docs/tasks/current 2>/dev/null || echo "No active tasks found in docs/tasks/current."

# --- Local Development (Running HERE) ---
run: ## Run the bot LOCALLY (on your machine)
	$(PYTHON) -m tg_translator.main

clean: ## Clean up build artifacts and cache
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +

# --- Quality Assurance ---
format: ## Format code using black and isort
	$(PYTHON) -m isort src tests
	$(PYTHON) -m black src tests

lint: ## Run static analysis (mypy, black check, isort check)
	$(PYTHON) -m black --check src tests
	$(PYTHON) -m isort --check-only src tests
	$(PYTHON) -m mypy src

test: ## Run tests
	$(PYTHON) -m pytest

# --- Remote / Production (Running THERE) ---
deploy: ## Deploy current code to REMOTE server and restart
	ansible-playbook -i deploy/inventory deploy/playbook.yml

logs: ## Watch REMOTE server logs
	ssh $(SERVER_HOST) "journalctl -u $(SERVICE_NAME) -f"

remote-status: ## Check REMOTE service status
	ssh $(SERVER_HOST) "systemctl status $(SERVICE_NAME)"

stop-remote: ## Stop REMOTE service (use before 'make run' if sharing token)
	ssh $(SERVER_HOST) "systemctl stop $(SERVICE_NAME)"

start-remote: ## Start REMOTE service
	ssh $(SERVER_HOST) "systemctl start $(SERVICE_NAME)"

restart-remote: ## Restart REMOTE service manually
	ssh $(SERVER_HOST) "systemctl restart $(SERVICE_NAME)"
