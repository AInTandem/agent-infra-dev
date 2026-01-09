# Git Hooks

This directory contains Git hooks for maintaining code quality.

## Available Hooks

### pre-commit
Runs automatically before each commit to check:
- **Python syntax** - Ensures all Python files compile correctly
- **Imports** - Verifies modules can be imported
- **Ruff linter** - Checks code style (if installed)
- **Debugger breakpoints** - Prevents accidental commits with `pdb.set_trace()`
- **TODO comments** - Warns about TODO/FIXME comments

## Installation

### Install Hooks

```bash
./scripts/githooks/install.sh
```

This sets `git config core.hooksPath` to point to `scripts/githooks/`.

### Uninstall Hooks

```bash
git config --unset core.hooksPath
```

## Usage

### Automatic Checks

Hooks run automatically when you commit:

```bash
git commit -m "My changes"
```

If checks fail, the commit will be aborted. Fix the errors and try again.

### Bypass Hooks (if needed)

```bash
git commit --no-verify -m "My changes"
```

Use this only when necessary (e.g., WIP commits).

## Hook Checks

### Critical Checks (block commit)

| Check | Description | Example Error |
|-------|-------------|---------------|
| Syntax | Python compilation | `SyntaxError: invalid syntax` |
| Breakpoints | Debugger statements | `pdb.set_trace() found in file.py` |
| Ruff | Code style | `F401 'unused' imported but unused` |

### Warning Checks (don't block)

| Check | Description |
|-------|-------------|
| Imports | Module import errors (may be due to missing dependencies) |
| TODO | TODO/FIXME/HACK comments |

## Configuration

### Ruff Configuration

If you have Ruff installed, it will be run automatically. Configure in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "W"]
ignore = ["E501"]
```

### Skip Specific Checks

Edit `scripts/githooks/pre-commit` to disable specific checks.

## Team Usage

Because hooks are configured via `core.hooksPath`, all team members can use the same hooks:

1. Clone the repository
2. Run `./scripts/githooks/install.sh`
3. Done!

The hooks are version-controlled, so everyone stays in sync.

## Troubleshooting

### Hook not running?

Check if hooks are installed:
```bash
git config --get core.hooksPath
```

Should return: `scripts/githooks`

### Permission denied?

Make hooks executable:
```bash
chmod +x scripts/githooks/pre-commit
```

### Need to use different Python?

Edit the shebang line in `pre-commit`:
```bash
#!/usr/bin/env python3.11
```

## Development

### Adding New Hooks

1. Create a new hook file in `scripts/githooks/`
2. Make it executable: `chmod +x scripts/githooks/your-hook`
3. It will be automatically available to all team members

### Testing Hooks

Test without committing:
```bash
./scripts/githooks/pre-commit
```

## Files

```
scripts/githooks/
├── pre-commit      # Pre-commit checks (Python)
├── install.sh      # Installation script
└── README.md       # This file
```
