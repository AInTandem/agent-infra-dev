# Round Table - Agent Collaboration Bus

> "Where AI agents gather as equals to collaborate and solve complex problems"

## What is Round Table?

Round Table is a cross-container AI agent collaboration infrastructure that enables multiple AI agents to communicate, coordinate, and work together to solve complex problems.

Inspired by King Arthur and the Round Table Knights, it creates a coworking space where AI agents in isolated containers can collaborate as equals.

## Quick Start

```bash
# Clone repository
cd /path/to/aintandem/templates/agent-infra/round-table

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r api/requirements.txt

# Start development environment
docker-compose -f docker/docker-compose.yml up -d
python -m uvicorn api.app.main:app --reload
```

## Project Structure

```
round-table/
├── api/                # FastAPI Server
├── sdk/
│   ├── python/         # Python SDK
│   └── typescript/     # TypeScript SDK
├── docker/             # Docker configuration
├── scripts/            # Development scripts
├── worklogs/           # Development work logs
└── tests/              # Integration tests
```

## Documentation

See parent project docs:
- `../../docs/round-table/README.md` - Project overview
- `../../docs/round-table/TESTING_STRATEGY.md` - Testing strategy
- `../../plans/round-table-mvp.md` - Implementation plan

## Development

```bash
# Run tests
pytest

# Format code
black api/ sdk/python/

# Type check
mypy api/
```

---

**Project**: Round Table
**Status**: In Development
**Version**: 0.1.0-alpha
