#!/bin/sh
set -e

# Run the MCP server using the virtual environment created during build
exec uv run budget-mcp
