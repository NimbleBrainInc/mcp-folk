# MCPB bundle configuration
BUNDLE_NAME = mcp-folk
VERSION ?= 0.0.1

.PHONY: help install dev-install format format-check lint lint-fix typecheck test test-cov clean check all bundle bundle-run bump run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	uv pip install -e .

dev-install: ## Install the package with dev dependencies
	uv pip install -e ".[dev]"

format: ## Format code with ruff
	uv run ruff format src/ tests/

format-check: ## Check code formatting with ruff
	uv run ruff format --check src/ tests/

lint: ## Lint code with ruff
	uv run ruff check src/ tests/

lint-fix: ## Lint and fix code with ruff
	uv run ruff check --fix src/ tests/

typecheck: ## Type check code with mypy
	uv run mypy src/

test: ## Run tests with pytest
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=src/mcp_folk --cov-report=term-missing

clean: ## Clean up build artifacts and cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	rm -rf bundle/ *.mcpb

run: ## Run the MCP server in stdio mode
	uv run python -m mcp_folk.server

check: format-check lint typecheck test ## Run all checks

all: clean install format lint typecheck test ## Clean, install, format, lint, type check, and test

# MCPB bundle commands
bundle: ## Build MCPB bundle locally
	@./scripts/build-bundle.sh . $(VERSION)

bundle-run: bundle ## Build and run MCPB bundle locally
	@echo "Starting bundle with mcpb-python base image..."
	@python -m http.server 9999 --directory . &
	@sleep 1
	docker run --rm \
		--add-host host.docker.internal:host-gateway \
		-p 8000:8000 \
		-e BUNDLE_URL=http://host.docker.internal:9999/$(BUNDLE_NAME)-v$(VERSION).mcpb \
		ghcr.io/nimblebrain/mcpb-python:3.14

bump: ## Bump version across all files (usage: make bump VERSION=0.2.0)
	@if [ -z "$(VERSION)" ]; then echo "Usage: make bump VERSION=x.y.z"; exit 1; fi
	@echo "Bumping version to $(VERSION)..."
	@jq --arg v "$(VERSION)" '.version = $$v' manifest.json > manifest.tmp.json && mv manifest.tmp.json manifest.json
	@sed -i '' 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	@sed -i '' 's/^__version__ = ".*"/__version__ = "$(VERSION)"/' src/mcp_folk/__init__.py
	@echo "Updated:"
	@echo "  manifest.json:            $$(jq -r .version manifest.json)"
	@echo "  pyproject.toml:           $$(grep '^version' pyproject.toml)"
	@echo "  src/mcp_folk/__init__.py: $$(grep '__version__' src/mcp_folk/__init__.py)"

# Development shortcuts
fmt: format ## Alias for format
t: test ## Alias for test
l: lint ## Alias for lint
tc: typecheck ## Alias for typecheck
