setup:
    uv venv
    uv sync --extra dev

test:
    uv run pytest

lint:
    uv run ruff check .

clean:
    rm -rf ./.venv
    rm -rf ./.pytest_cache
    rm -rf ./__pycache__
    rm -f ./budget.db


format:
    uv run isort .
    uv run ruff format --line-length 88 .