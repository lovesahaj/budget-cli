"""MCP Server for Budget Tracker.

This server exposes budget tracking functionality as tools for LLM interaction.
The server is modular with separate tool definitions and handlers.
"""

import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from budget.budget import Budget
from budget.mcp.handlers import ToolRouter
from budget.mcp.tools import get_all_tools

# Initialize the MCP server
app = Server("budget-tracker")

# Initialize budget instance
budget = Budget(os.environ.get("BUDGET_DB_NAME", "budget.db"))

# Initialize tool router
router = ToolRouter(budget)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools from the tools module."""
    return get_all_tools()


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Route tool calls to appropriate handlers."""
    return await router.route(name, arguments)


async def async_main():
    """Run the MCP server asynchronously."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Entry point for the MCP server."""
    import asyncio

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
