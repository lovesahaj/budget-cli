"""Tool definitions for the Budget Tracker MCP server."""

from mcp.types import Tool


def get_transaction_tools() -> list[Tool]:
    """Get transaction-related tools."""
    return [
        Tool(
            name="add_transaction",
            description="Add a single transaction (expense) to the budget",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["cash", "card"],
                        "description": "Transaction type",
                    },
                    "description": {
                        "type": "string",
                        "description": "Transaction description",
                    },
                    "amount": {
                        "type": "number",
                        "description": "Transaction amount (must be positive)",
                    },
                    "card": {
                        "type": "string",
                        "description": "Card name (for card transactions)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Transaction category",
                    },
                },
                "required": ["type", "description", "amount"],
            },
        ),
        Tool(
            name="add_multiple_transactions",
            description="Add multiple transactions at once. Useful for bulk imports or when adding several transactions together.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transactions": {
                        "type": "array",
                        "description": "Array of transactions to add",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["cash", "card"],
                                    "description": "Transaction type",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Transaction description",
                                },
                                "amount": {
                                    "type": "number",
                                    "description": "Transaction amount (must be positive)",
                                },
                                "card": {
                                    "type": "string",
                                    "description": "Card name (for card transactions)",
                                },
                                "category": {
                                    "type": "string",
                                    "description": "Transaction category",
                                },
                            },
                            "required": ["type", "description", "amount"],
                        },
                    },
                },
                "required": ["transactions"],
            },
        ),
        Tool(
            name="list_transactions",
            description="List recent transactions with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of transactions to return",
                        "default": 10,
                    },
                    "query": {
                        "type": "string",
                        "description": "Search text to filter by",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category",
                    },
                    "card": {
                        "type": "string",
                        "description": "Filter by card name",
                    },
                },
            },
        ),
        Tool(
            name="search_transactions",
            description="Search transactions with advanced filters including date range and amount",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search in description/card",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category",
                    },
                    "card": {
                        "type": "string",
                        "description": "Filter by card",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                    "min_amount": {
                        "type": "number",
                        "description": "Minimum amount",
                    },
                    "max_amount": {
                        "type": "number",
                        "description": "Maximum amount",
                    },
                },
            },
        ),
        Tool(
            name="update_transaction",
            description="Update an existing transaction",
            inputSchema={
                "type": "object",
                "properties": {
                    "transaction_id": {
                        "type": "number",
                        "description": "ID of transaction to update",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["cash", "card"],
                        "description": "New transaction type",
                    },
                    "description": {
                        "type": "string",
                        "description": "New description",
                    },
                    "amount": {
                        "type": "number",
                        "description": "New amount",
                    },
                    "card": {
                        "type": "string",
                        "description": "New card name",
                    },
                    "category": {
                        "type": "string",
                        "description": "New category",
                    },
                },
                "required": ["transaction_id"],
            },
        ),
        Tool(
            name="delete_transaction",
            description="Delete a transaction by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "transaction_id": {
                        "type": "number",
                        "description": "ID of transaction to delete",
                    },
                },
                "required": ["transaction_id"],
            },
        ),
    ]


def get_category_tools() -> list[Tool]:
    """Get category-related tools."""
    return [
        Tool(
            name="add_category",
            description="Add a new transaction category",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Category name",
                    },
                    "description": {
                        "type": "string",
                        "description": "Category description",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="list_categories",
            description="List all available categories",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


def get_card_tools() -> list[Tool]:
    """Get card-related tools."""
    return [
        Tool(
            name="add_card",
            description="Add a new payment card",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Card name",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="list_cards",
            description="List all payment cards",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


def get_balance_tools() -> list[Tool]:
    """Get balance-related tools."""
    return [
        Tool(
            name="get_balance",
            description="Get balance for a specific type (cash or card name)",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Balance type (e.g., 'cash' or card name)",
                    },
                },
                "required": ["type"],
            },
        ),
        Tool(
            name="get_all_balances",
            description="Get all balances (cash and cards)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="update_balance",
            description="Update balance for a type",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Balance type",
                    },
                    "amount": {
                        "type": "number",
                        "description": "New balance amount",
                    },
                },
                "required": ["type", "amount"],
            },
        ),
    ]


def get_limit_tools() -> list[Tool]:
    """Get spending limit tools."""
    return [
        Tool(
            name="set_spending_limit",
            description="Set a spending limit for a period",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit_amount": {
                        "type": "number",
                        "description": "Maximum spending amount",
                    },
                    "period": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly", "yearly"],
                        "description": "Time period for the limit",
                        "default": "monthly",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category to limit",
                    },
                    "source": {
                        "type": "string",
                        "description": "Optional source to limit (card name or 'cash')",
                    },
                },
                "required": ["limit_amount"],
            },
        ),
        Tool(
            name="check_spending_limit",
            description="Check spending against limits for a period",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly", "yearly"],
                        "description": "Time period to check",
                        "default": "monthly",
                    },
                    "category": {
                        "type": "string",
                        "description": "Category to check",
                    },
                    "source": {
                        "type": "string",
                        "description": "Source to check",
                    },
                },
            },
        ),
    ]


def get_report_tools() -> list[Tool]:
    """Get reporting tools."""
    return [
        Tool(
            name="get_daily_spending",
            description="Get daily spending for the last N days",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "number",
                        "description": "Number of days to include",
                        "default": 30,
                    },
                },
            },
        ),
        Tool(
            name="get_spending_by_category",
            description="Get spending breakdown by category for a specific month",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "number",
                        "description": "Year (defaults to current year)",
                    },
                    "month": {
                        "type": "number",
                        "description": "Month 1-12 (defaults to current month)",
                    },
                },
            },
        ),
    ]


def get_all_tools() -> list[Tool]:
    """Get all available tools."""
    return (
        get_transaction_tools()
        + get_category_tools()
        + get_card_tools()
        + get_balance_tools()
        + get_limit_tools()
        + get_report_tools()
    )
