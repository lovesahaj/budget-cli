setup:
    uv venv
    uv sync --extra dev

run:
    uv run python -m budget.budget_cli tui

test:
    uv run pytest

lint:
    uv run ruff check .

# gRPC commands
grpc-server PORT="50051":
    uv run python start_grpc_server.py --port {{PORT}} -v

grpc-client HOST="localhost" PORT="50051":
    uv run python example_grpc_client.py --host {{HOST}} --port {{PORT}}

grpc-compile:
    uv run python -m grpc_tools.protoc -Ibudget/server/proto --python_out=budget/server/proto --grpc_python_out=budget/server/proto budget/server/proto/budget.proto
    sed -i '' 's/^import budget_pb2/from budget.server.proto import budget_pb2/' budget/server/proto/budget_pb2_grpc.py

clean:
    rm -rf ./.venv
    rm -rf ./.pytest_cache
    rm -rf ./__pycache__
    rm -f ./budget.db


format:
    uv run isort .
    uv run ruff format --line-length 88 .
