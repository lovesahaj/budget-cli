setup:
    uv venv
    uv sync

run:
    uv run budget_cli.py tui

test:
    uv run pytest

lint:
    uv run ruff check .

clean:
    rm -rf ./.venv
    rm -rf ./.pytest_cache
    rm -rf ./__pycache__
    rm -f ./budget.db