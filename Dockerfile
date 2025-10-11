# Use the official Python image
FROM python:3.13-slim

# Install uv, the project's package manager
RUN pip install uv

# Set the working directory in the container
WORKDIR /app

# Copy the dependency definitions
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (creates .venv)
RUN uv sync

# Copy the rest of the application's source code
COPY . .

# Install the package in editable mode
RUN uv pip install -e .

# Set the environment variable for the database name
# The database will be stored in the /data volume
ENV BUDGET_DB_NAME=/data/budget.db

# Copy and set executable permissions for entrypoint script
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Use the entrypoint script to run the MCP server
ENTRYPOINT ["/app/entrypoint.sh"]

