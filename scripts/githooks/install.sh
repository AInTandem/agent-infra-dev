#!/bin/bash
# Copyright (c) 2025 AInTandem
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Install Git Hooks using core.hooksPath

Uses git config core.hooksPath to point to the project's githooks directory.
This allows the hooks to be version-controlled and shared across the team.
"""

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

echo -e "${BLUE}${BOLD}============================================${RESET}"
echo -e "${BLUE}${BOLD}    Installing Git Hooks${RESET}"
echo -e "${BLUE}${BOLD}============================================${RESET}"
echo ""

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Hooks directory
HOOKS_DIR="$PROJECT_ROOT/scripts/githooks"

echo -e "${BLUE}Project root:${RESET} $PROJECT_ROOT"
echo -e "${BLUE}Hooks directory:${RESET} $HOOKS_DIR"
echo ""

# Check if .git directory exists
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${RED}Error: .git directory not found!${RESET}"
    echo -e "${YELLOW}Are you in a git repository?${RESET}"
    exit 1
fi

# Check if hooks directory exists
if [ ! -d "$HOOKS_DIR" ]; then
    echo -e "${RED}Error: Hooks directory not found: $HOOKS_DIR${RESET}"
    exit 1
fi

# Set core.hooksPath using git config
echo -e "${BLUE}${BOLD}Configuring git hooks...${RESET}"
echo ""

# Get the relative path from project root to hooks dir
RELATIVE_HOOKS_PATH="scripts/githooks"

# Set the hooks path for this repository
git config core.hooksPath "$RELATIVE_HOOKS_PATH"

# Verify the configuration
configured_path=$(git config --get core.hooksPath)

echo -e "${GREEN}✓${RESET} Git hooks path configured: ${BLUE}$configured_path${RESET}"
echo ""

# List available hooks
echo -e "${BLUE}${BOLD}Available hooks:${RESET}"
for hook_file in "$HOOKS_DIR"/*; do
    if [ -f "$hook_file" ]; then
        hook_name=$(basename "$hook_file")
        if [ -x "$hook_file" ]; then
            echo -e "  ${GREEN}✓${RESET} ${BLUE}$hook_name${RESET} (executable)"
        else
            echo -e "  ${YELLOW}⚠${RESET} ${BLUE}$hook_name${RESET} (not executable)"
        fi
    fi
done
echo ""

echo -e "${BLUE}${BOLD}============================================${RESET}"
echo -e "${GREEN}${BOLD}✓ Git hooks installed successfully!${RESET}"
echo -e "${BLUE}${BOLD}============================================${RESET}"
echo ""
echo -e "${BLUE}Configuration:${RESET}"
echo -e "  • core.hooksPath: ${GREEN}$configured_path${RESET}"
echo -e "  • Scope: ${BLUE}Local repository${RESET} (.git/config)"
echo ""
echo -e "${YELLOW}Note: The hooks are now version-controlled!${RESET}"
echo -e "${YELLOW}      All team members can use the same hooks.${RESET}"
echo ""
echo -e "${BLUE}To uninstall/hooks:${RESET}"
echo -e "  ${BOLD}git config --unset core.hooksPath${RESET}"
echo ""
echo -e "${YELLOW}To bypass pre-commit checks:${RESET}"
echo -e "  ${BOLD}git commit --no-verify${RESET}"
echo ""
