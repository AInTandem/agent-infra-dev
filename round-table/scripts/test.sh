#!/bin/bash
# Run tests

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

source venv/bin/activate

echo "🧪 Running tests..."

# API tests
echo "Testing API Server..."
pytest api/tests/ -v --cov=api/app --cov-report=html --cov-report=term

# Python SDK tests
echo "Testing Python SDK..."
pytest sdk/python/tests/ -v --cov=sdk/python/src --cov-report=html --cov-report=term

echo "✅ All tests passed!"
