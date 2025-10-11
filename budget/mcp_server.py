"""MCP Server for Budget Tracker.

This server exposes budget tracking functionality as tools for LLM interaction.
"""

import json
import os
from datetime import datetime
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from budget.budget import Budget

# Initialize the MCP server
app = Server("budget-tracker")

# Initialize budget instance
budget = Budget(os.environ.get("BUDGET_DB_NAME", "budget.db"))


# Transaction tools
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="add_transaction",
            description="Add a new transaction (expense) to the budget",
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


def format_transaction(txn: Any) -> str:
    """Format a transaction for display."""
    date = txn.timestamp.strftime("%Y-%m-%d %H:%M") if txn.timestamp else "N/A"
    card_str = f" ({txn.card})" if txn.card else ""
    cat_str = f" [{txn.category}]" if txn.category else ""
    return f"#{txn.id} {date} - {txn.description}{card_str}{cat_str}: ${txn.amount:.2f}"


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""

    try:
        if name == "add_transaction":
            txn_id = budget.add_transaction(
                type=arguments["type"],
                description=arguments["description"],
                amount=arguments["amount"],
                card=arguments.get("card"),
                category=arguments.get("category"),
            )
            return [
                TextContent(
                    type="text",
                    text=f"Transaction added successfully with ID: {txn_id}",
                )
            ]

        elif name == "list_transactions":
            limit = arguments.get("limit", 10)
            query = arguments.get("query")
            category = arguments.get("category")
            card = arguments.get("card")

            if query or category or card:
                txns = budget.search_transactions(
                    query=query or "", category=category, card=card
                )
            else:
                txns = budget.get_recent_transactions(limit)

            if not txns:
                return [TextContent(type="text", text="No transactions found")]

            result = "Recent Transactions:\n\n"
            for txn in txns[:limit]:
                result += format_transaction(txn) + "\n"

            return [TextContent(type="text", text=result)]

        elif name == "search_transactions":
            txns = budget.search_transactions(
                query=arguments.get("query", ""),
                category=arguments.get("category"),
                card=arguments.get("card"),
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
                min_amount=arguments.get("min_amount"),
                max_amount=arguments.get("max_amount"),
            )

            if not txns:
                return [TextContent(type="text", text="No matching transactions found")]

            result = f"Found {len(txns)} transactions:\n\n"
            for txn in txns:
                result += format_transaction(txn) + "\n"

            return [TextContent(type="text", text=result)]

        elif name == "update_transaction":
            success = budget.update_transaction(
                transaction_id=int(arguments["transaction_id"]),
                type=arguments.get("type"),
                card=arguments.get("card"),
                description=arguments.get("description"),
                amount=arguments.get("amount"),
                category=arguments.get("category"),
            )

            if success:
                return [
                    TextContent(
                        type="text",
                        text=f"Transaction {arguments['transaction_id']} updated successfully",
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Transaction {arguments['transaction_id']} not found",
                    )
                ]

        elif name == "delete_transaction":
            success = budget.delete_transaction(int(arguments["transaction_id"]))

            if success:
                return [
                    TextContent(
                        type="text",
                        text=f"Transaction {arguments['transaction_id']} deleted successfully",
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Transaction {arguments['transaction_id']} not found",
                    )
                ]

        elif name == "add_category":
            success = budget.add_category(
                name=arguments["name"], description=arguments.get("description", "")
            )

            if success:
                return [
                    TextContent(
                        type="text",
                        text=f"Category '{arguments['name']}' added successfully",
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"Category '{arguments['name']}' already exists",
                    )
                ]

        elif name == "list_categories":
            categories = budget.get_categories()

            if not categories:
                return [TextContent(type="text", text="No categories found")]

            result = "Available Categories:\n\n"
            for cat in categories:
                desc = f" - {cat.description}" if cat.description else ""
                result += f"• {cat.name}{desc}\n"

            return [TextContent(type="text", text=result)]

        elif name == "add_card":
            success = budget.add_card(name=arguments["name"])

            if success:
                return [
                    TextContent(
                        type="text",
                        text=f"Card '{arguments['name']}' added successfully",
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text", text=f"Card '{arguments['name']}' already exists"
                    )
                ]

        elif name == "list_cards":
            cards = budget.get_cards()

            if not cards:
                return [TextContent(type="text", text="No cards found")]

            result = "Payment Cards:\n\n"
            for card in cards:
                result += f"• {card.name}\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_balance":
            balance = budget.get_balance(arguments["type"])
            return [
                TextContent(
                    type="text",
                    text=f"Balance for '{arguments['type']}': ${balance:.2f}",
                )
            ]

        elif name == "get_all_balances":
            balances = budget.get_all_balances()

            if not balances:
                return [TextContent(type="text", text="No balances found")]

            result = "Current Balances:\n\n"
            for balance_type, amount in balances.items():
                result += f"• {balance_type}: ${amount:.2f}\n"

            total = sum(balances.values())
            result += f"\nTotal: ${total:.2f}"

            return [TextContent(type="text", text=result)]

        elif name == "update_balance":
            budget.update_balance(type=arguments["type"], amount=arguments["amount"])
            return [
                TextContent(
                    type="text",
                    text=f"Balance for '{arguments['type']}' set to ${arguments['amount']:.2f}",
                )
            ]

        elif name == "set_spending_limit":
            budget.set_spending_limit(
                limit_amount=arguments["limit_amount"],
                period=arguments.get("period", "monthly"),
                category=arguments.get("category"),
                source=arguments.get("source"),
            )

            period = arguments.get("period", "monthly")
            return [
                TextContent(
                    type="text",
                    text=f"Spending limit set to ${arguments['limit_amount']:.2f} per {period}",
                )
            ]

        elif name == "check_spending_limit":
            result = budget.check_spending_limit(
                category=arguments.get("category"),
                source=arguments.get("source"),
                period=arguments.get("period", "monthly"),
            )

            if result["limit"] == 0:
                return [
                    TextContent(
                        type="text", text="No spending limit set for these criteria"
                    )
                ]

            period = arguments.get("period", "monthly")
            response = f"Spending Limit Check ({period}):\n\n"
            response += f"• Limit: ${result['limit']:.2f}\n"
            response += f"• Spent: ${result['spent']:.2f}\n"
            response += f"• Remaining: ${result['remaining']:.2f}\n"
            response += f"• Status: {'⚠️ EXCEEDED' if result['exceeded'] else '✓ OK'}"

            return [TextContent(type="text", text=response)]

        elif name == "get_daily_spending":
            days = arguments.get("days", 30)
            daily_spending = budget.get_daily_spending(days)

            if not daily_spending:
                return [
                    TextContent(
                        type="text", text=f"No spending data for the last {days} days"
                    )
                ]

            result = f"Daily Spending (Last {days} days):\n\n"
            for date, amount in daily_spending:
                result += f"{date}: ${amount:.2f}\n"

            total = sum(amount for _, amount in daily_spending)
            avg = total / len(daily_spending)
            result += f"\nTotal: ${total:.2f}"
            result += f"\nAverage: ${avg:.2f}/day"

            return [TextContent(type="text", text=result)]

        elif name == "get_spending_by_category":
            now = datetime.now()
            year = arguments.get("year", now.year)
            month = arguments.get("month", now.month)

            spending = budget.get_spending_by_category(year, month)

            if not spending:
                return [
                    TextContent(
                        type="text", text=f"No spending data for {year}-{month:02d}"
                    )
                ]

            total = sum(spending.values())

            result = f"Spending by Category ({year}-{month:02d}):\n\n"
            for category, amount in sorted(
                spending.items(), key=lambda x: x[1], reverse=True
            ):
                pct = (amount / total * 100) if total > 0 else 0
                result += f"• {category}: ${amount:.2f} ({pct:.1f}%)\n"

            result += f"\nTotal: ${total:.2f}"

            return [TextContent(type="text", text=result)]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]


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
