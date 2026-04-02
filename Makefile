.PHONY: test test-unit test-integration test-live test-benchmark test-all coverage lint format security setup-dev ci help

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Open Dsearch Test Suite$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Test commands
test: test-unit test-integration ## Run all tests (unit + integration)

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest tests/unit -v --cov=scripts --cov-report=term-missing

test-integration: ## Run integration tests (no live APIs)
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest tests/integration -v -m "not live_api"

test-live: ## Run tests with live APIs (requires API keys)
	@echo "$(YELLOW)Running live API tests...$(NC)"
	LIVE_API_TESTS=1 pytest tests/integration -v -m "live_api"

test-benchmark: ## Run performance benchmarks
	@echo "$(BLUE)Running benchmarks...$(NC)"
	pytest tests/benchmarks -v --benchmark-only

test-all: test test-live test-benchmark ## Run all tests including live and benchmarks

# Coverage
coverage: ## Generate coverage report
	@echo "$(BLUE)Generating coverage report...$(NC)"
	pytest tests/unit tests/integration -v \
		--cov=scripts \
		--cov-report=html \
		--cov-report=xml \
		--cov-report=term
	@echo "$(GREEN)Coverage report: tests/reports/coverage/index.html$(NC)"

coverage-open: coverage ## Generate and open coverage report
	@echo "$(BLUE)Opening coverage report...$(NC)"
	@python -c "import webbrowser; webbrowser.open('tests/reports/coverage/index.html')"

# Code quality
lint: ## Run linters (black, ruff)
	@echo "$(BLUE)Running linters...$(NC)"
	@echo "Checking black formatting..."
	black --check scripts/ tests/
	@echo "Running ruff..."
	ruff check scripts/ tests/

format: ## Format code with black and ruff
	@echo "$(BLUE)Formatting code...$(NC)"
	@echo "Running black..."
	black scripts/ tests/
	@echo "Running ruff fix..."
	ruff check --fix scripts/ tests/

typecheck: ## Run type checker (mypy)
	@echo "$(BLUE)Running type checker...$(NC)"
	mypy scripts/ --ignore-missing-imports || true

# Security
security: ## Run security scans (bandit, drift_scan)
	@echo "$(BLUE)Running security scans...$(NC)"
	@echo "Running drift_scan..."
	python scripts/drift_scan.py
	@echo "Running bandit..."
	bandit -r scripts/ -f json -o security-report.json || true
	@echo "$(GREEN)Security report: security-report.json$(NC)"

# Setup
setup-dev: ## Install development dependencies
	@echo "$(BLUE)Setting up development environment...$(NC)"
	pip install -r requirements.txt
	pip install -r requirements-api.txt
	pip install -r requirements-dev.txt
	pre-commit install || echo "pre-commit not installed, skipping"
	@echo "$(GREEN)Development environment ready!$(NC)"

setup-test: ## Install test dependencies only
	@echo "$(BLUE)Installing test dependencies...$(NC)"
	pip install -r requirements-dev.txt

# CI
ci: lint security test-unit ## Run CI checks (lint, security, unit tests)
	@echo "$(GREEN)CI checks complete!$(NC)"

# Cleaning
clean: ## Clean generated files
	@echo "$(BLUE)Cleaning generated files...$(NC)"
	rm -rf tests/reports/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf security-report.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)Clean complete!$(NC)"

# Rust
rust-test: ## Run Rust tests
	@echo "$(BLUE)Running Rust tests...$(NC)"
	cd scripts/rust && cargo test

rust-build: ## Build Rust release binary
	@echo "$(BLUE)Building Rust binary...$(NC)"
	cd scripts/rust && cargo build --release

# Documentation
docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@echo "API docs available at: http://localhost:8000/docs (when server is running)"

# Quick commands
quick: test-unit ## Quick test run (unit tests only)
	@echo "$(GREEN)Quick test complete!$(NC)"
