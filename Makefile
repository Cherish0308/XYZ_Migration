.PHONY: help install install-dev test test-cov lint format clean build-lambda deploy-lambda

# Default target
.DEFAULT_GOAL := help

# Project configuration
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
ISORT := $(PYTHON) -m isort
FLAKE8 := $(PYTHON) -m flake8
MYPY := $(PYTHON) -m mypy

# Directories
SRC_DIR := src
TEST_DIR := tests
BUILD_DIR := build
DIST_DIR := dist

help: ## Show this help message
	@echo "XYZ Migration - Available Commands"
	@echo "===================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(PIP) install -e .

install-dev: ## Install development dependencies
	$(PIP) install -e ".[dev]"

test: ## Run unit tests
	$(PYTEST) $(TEST_DIR)/unit -v

test-cov: ## Run tests with coverage report
	$(PYTEST) $(TEST_DIR)/unit --cov=$(SRC_DIR)/app --cov-report=html --cov-report=term

test-integration: ## Run integration tests
	$(PYTEST) $(TEST_DIR)/integration -v

lint: ## Run linting (flake8)
	$(FLAKE8) $(SRC_DIR) $(TEST_DIR) --max-line-length=100 --exclude=__pycache__,*.pyc

format: ## Format code with black and isort
	$(BLACK) $(SRC_DIR) $(TEST_DIR)
	$(ISORT) $(SRC_DIR) $(TEST_DIR)

format-check: ## Check formatting without making changes
	$(BLACK) --check $(SRC_DIR) $(TEST_DIR)
	$(ISORT) --check-only $(SRC_DIR) $(TEST_DIR)

typecheck: ## Run type checking with mypy
	$(MYPY) $(SRC_DIR)

quality: format-check lint typecheck test ## Run all quality checks

clean: ## Remove build artifacts
	rm -rf $(BUILD_DIR) $(DIST_DIR)
	rm -rf *.egg-info
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build-lambda: clean ## Build Lambda deployment packages
	@echo "Building Lambda packages..."
	./scripts/build_lambda.sh

build-wheel: clean ## Build Python wheel for distribution
	$(PYTHON) -m build

upload-artifactory: build-wheel ## Upload package to Artifactory
	@echo "Uploading to Artifactory..."
	@echo "Configure artifactory credentials in ~/.pypirc"
	twine upload --repository artifactory dist/*.whl

deploy-lambda: build-lambda ## Deploy Lambda functions to AWS
	@echo "Deploying Lambda functions..."
	@echo "Set AWS_PROFILE environment variable before deploying"
	@for lambda in ingestion_lambda validation_lambda transform_lambda load_lambda dq_lambda orchestration_lambda; do \
		echo "Deploying $$lambda..."; \
		aws lambda update-function-code \
			--function-name $$lambda \
			--zip-file fileb://dist/$$lambda.zip; \
	done

ci: install-dev quality ## Run CI pipeline locally
	@echo "✓ CI checks passed"

dev-setup: install-dev ## Setup development environment
	pre-commit install || true
	@echo "Development environment ready"

# Quick commands for common workflows
quick-test: ## Run tests quickly (parallel, no coverage)
	$(PYTEST) $(TEST_DIR)/unit -n auto -q

watch-test: ## Watch for changes and run tests
	$(PYTEST) $(TEST_DIR)/unit --looponfail

# Documentation
docs: ## Generate documentation (future)
	@echo "Documentation generation not yet implemented"
