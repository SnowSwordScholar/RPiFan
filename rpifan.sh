#!/bin/bash
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ ! -f "$PROJECT_DIR/pyproject.toml" ]; then
    echo "Error: Cannot find project configuration. Please run this script from the installation directory or ensure PROJECT_DIR is correct."
    exit 1
fi
cd "$PROJECT_DIR" || exit 1
uv run -m src.frontend "$@"
