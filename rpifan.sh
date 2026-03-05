#!/bin/bash
# Resolve the directory where the script is actually located, following symlinks
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
PROJECT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

# Add common local bin paths if uv is not in PATH
if ! command -v uv &> /dev/null; then
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if [ ! -f "$PROJECT_DIR/pyproject.toml" ]; then
    echo "Error: Cannot find project configuration."
    exit 1
fi

# Check again
if ! command -v uv &> /dev/null; then
    echo "Error: 'uv' not found. Please ensure it is installed (curl -LsSf https://astral.sh/uv/install.sh | sh)"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1
exec uv run -m src.frontend "$@"
