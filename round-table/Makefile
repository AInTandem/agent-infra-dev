# Round Table Makefile

.PHONY: help dev test lint format build clean install

help:  ## Show this help message
	@echo "🏰 Round Table - Available Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

dev:  ## Start development environment
	@echo "🚀 Starting development environment..."
	@./scripts/dev.sh

test:  ## Run all tests
	@echo "🧪 Running tests..."
	@./scripts/test.sh

test-api:  ## Run API tests only
	@echo "🧪 Testing API Server..."
	@source venv/bin/activate && pytest api/tests/ -v

test-sdk:  ## Run SDK tests only
	@echo "🧪 Testing Python SDK..."
	@source venv/bin/activate && pytest sdk/python/tests/ -v

test-ts:  ## Run TypeScript SDK tests
	@echo "🧪 Testing TypeScript SDK..."
	@cd sdk/typescript && npm test

lint:  ## Run linters
	@echo "🔍 Running linters..."
	@source venv/bin/activate && ruff check api/ sdk/python/
	@cd sdk/typescript && npm run lint

format:  ## Format code
	@echo "✨ Formatting code..."
	@source venv/bin/activate && black api/ sdk/python/
	@source venv/bin/activate && ruff check --fix api/ sdk/python/
	@cd sdk/typescript && npm run format

build:  ## Build all components
	@echo "🔨 Building..."
	@cd sdk/typescript && npm run build
	@docker-compose -f docker/docker-compose.yml build

install:  ## Install dependencies
	@echo "📦 Installing dependencies..."
	@python3 -m venv venv
	@source venv/bin/activate && pip install -r api/requirements.txt
	@cd sdk/typescript && npm install

clean:  ## Clean build artifacts
	@echo "🧹 Cleaning..."
	@rm -rf build dist *.egg-info
	@rm -rf sdk/typescript/dist
	@rm -rf .pytest_cache .mypy_cache htmlcov
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

up:  ## Start Docker services
	@docker-compose -f docker/docker-compose.yml up -d

down:  ## Stop Docker services
	@docker-compose -f docker/docker-compose.yml down

logs:  ## Show Docker logs
	@docker-compose -f docker/docker-compose.yml logs -f
