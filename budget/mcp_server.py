"""MCP Server for Budget Tracker.

This server exposes budget tracking functionality as tools for LLM interaction.
The server is modular with separate tool definitions and handlers.
"""

import logging
import os
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from budget.budget import Budget
from budget.mcp.handlers import ToolRouter
from budget.mcp.tools import get_all_tools


# Configure logging
def setup_logging():
    """Configure logging for the MCP server."""
    log_level = os.environ.get("MCP_LOG_LEVEL", "INFO").upper()
    log_file = os.environ.get("MCP_LOG_FILE", "budget_mcp.log")

    # Create logger
    logger = logging.getLogger("budget.mcp")
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level, logging.INFO))

    # Console handler (for stderr, won't interfere with stdio MCP communication)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to stderr

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Setup logging
logger = setup_logging()

# Initialize the MCP server
app = Server("budget-tracker")
logger.info("MCP Server initializing...")

# Initialize budget instance
db_name = os.environ.get("BUDGET_DB_NAME", "budget.db")
budget = Budget(db_name)
logger.info(f"Budget instance created with database: {db_name}")

# Initialize tool router
router = ToolRouter(budget)
logger.info("Tool router initialized")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools from the tools module."""
    logger.debug("Listing available tools")
    tools = get_all_tools()
    logger.info(f"Returning {len(tools)} tools")
    return tools


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Route tool calls to appropriate handlers."""
    logger.info(f"Tool call: {name}")
    logger.debug(f"Arguments: {arguments}")

    try:
        result = await router.route(name, arguments)
        logger.info(f"Tool call '{name}' completed successfully")
        logger.debug(f"Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Tool call '{name}' failed: {str(e)}", exc_info=True)
        raise


async def async_main():
    """Run the MCP server asynchronously."""
    logger.info("Starting MCP server on stdio")
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("MCP server running, waiting for requests...")
            await app.run(read_stream, write_stream, app.create_initialization_options())
    except Exception as e:
        logger.error(f"MCP server error: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("MCP server shutting down")


def main():
    """Entry point for the MCP server."""
    import asyncio

    logger.info("=== Budget MCP Server Starting ===")
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server crashed: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("=== Budget MCP Server Stopped ===")


if __name__ == "__main__":
    main()
