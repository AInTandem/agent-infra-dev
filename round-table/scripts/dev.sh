#!/bin/bash
# Round Table Development Environment Startup

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🏰 Round Table Development Environment"
echo "======================================"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r api/requirements.txt

# Install Node.js dependencies
if [ -d "sdk/typescript" ]; then
    echo "📥 Installing Node.js dependencies..."
    cd sdk/typescript
    npm install
    cd "$PROJECT_ROOT"
fi

# Create data directory
mkdir -p data

# Start Redis
echo "🚀 Starting Redis..."
docker-compose -f docker/docker-compose.yml up -d redis

# Wait for Redis
echo "⏳ Waiting for Redis..."
until docker-compose -f docker/docker-compose.yml exec -T redis redis-cli ping > /dev/null 2>&1; do
    sleep 1
done
echo "✅ Redis is ready!"

echo ""
echo "✨ Development environment ready!"
echo ""
echo "Available commands:"
echo "  make test      - Run tests"
echo "  make lint     - Run linters"
echo "  make format   - Format code"
echo "  make build    - Build all components"
echo ""
echo "To start the API server:"
echo "  uvicorn api.app.main:app --reload"
echo ""
