"""Tool handlers for the Budget Tracker MCP server."""

from datetime import datetime
from typing import Any

from mcp.types import TextContent

from budget.budget import Budget


def format_transaction(txn: Any) -> str:
    """Format a transaction for display."""
    date = txn.timestamp.strftime("%Y-%m-%d %H:%M") if txn.timestamp else "N/A"
    card_str = f" ({txn.card})" if txn.card else ""
    cat_str = f" [{txn.category}]" if txn.category else ""
    return f"#{txn.id} {date} - {txn.description}{card_str}{cat_str}: ${txn.amount:.2f}"


class TransactionHandlers:
    """Handlers for transaction-related tools."""

    def __init__(self, budget: Budget):
        """Initialize handlers with a budget instance."""
        self.budget = budget

    async def handle_add_transaction(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle adding a single transaction."""
        txn_id = self.budget.add_transaction(
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

    async def handle_add_multiple_transactions(
        self, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle adding multiple transactions at once."""
        transactions = arguments.get("transactions", [])

        if not transactions:
            return [TextContent(type="text", text="Error: No transactions provided")]

        results = {"success": 0, "failed": 0, "errors": []}
        added_ids = []

        for idx, txn in enumerate(transactions):
            try:
                # Validate required fields
                if not all(k in txn for k in ["type", "description", "amount"]):
                    results["failed"] += 1
                    results["errors"].append(
                        f"Transaction {idx + 1}: Missing required fields"
                    )
                    continue

                # Add the transaction
                txn_id = self.budget.add_transaction(
                    type=txn["type"],
                    description=txn["description"],
                    amount=txn["amount"],
                    card=txn.get("card"),
                    category=txn.get("category"),
                )
                results["success"] += 1
                added_ids.append(txn_id)

            except ValueError as e:
                results["failed"] += 1
                results["errors"].append(f"Transaction {idx + 1}: {str(e)}")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Transaction {idx + 1}: Unexpected error - {str(e)}")

        # Build response message
        response = f"Bulk Transaction Import Results:\n\n"
        response += f"✓ Successfully added: {results['success']}\n"
        response += f"✗ Failed: {results['failed']}\n"

        if added_ids:
            response += f"\nAdded transaction IDs: {', '.join(map(str, added_ids))}\n"

        if results["errors"]:
            response += "\nErrors:\n"
            for error in results["errors"]:
                response += f"  • {error}\n"

        return [TextContent(type="text", text=response)]

    async def handle_list_transactions(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle listing transactions."""
        limit = arguments.get("limit", 10)
        query = arguments.get("query")
        category = arguments.get("category")
        card = arguments.get("card")

        if query or category or card:
            txns = self.budget.search_transactions(
                query=query or "", category=category, card=card
            )
        else:
            txns = self.budget.get_recent_transactions(limit)

        if not txns:
            return [TextContent(type="text", text="No transactions found")]

        result = "Recent Transactions:\n\n"
        for txn in txns[:limit]:
            result += format_transaction(txn) + "\n"

        return [TextContent(type="text", text=result)]

    async def handle_search_transactions(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle searching transactions."""
        txns = self.budget.search_transactions(
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

    async def handle_update_transaction(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle updating a transaction."""
        success = self.budget.update_transaction(
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

    async def handle_delete_transaction(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle deleting a transaction."""
        success = self.budget.delete_transaction(int(arguments["transaction_id"]))

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


class CategoryHandlers:
    """Handlers for category-related tools."""

    def __init__(self, budget: Budget):
        """Initialize handlers with a budget instance."""
        self.budget = budget

    async def handle_add_category(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle adding a category."""
        success = self.budget.add_category(
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

    async def handle_list_categories(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle listing categories."""
        categories = self.budget.get_categories()

        if not categories:
            return [TextContent(type="text", text="No categories found")]

        result = "Available Categories:\n\n"
        for cat in categories:
            desc = f" - {cat.description}" if cat.description else ""
            result += f"• {cat.name}{desc}\n"

        return [TextContent(type="text", text=result)]


class CardHandlers:
    """Handlers for card-related tools."""

    def __init__(self, budget: Budget):
        """Initialize handlers with a budget instance."""
        self.budget = budget

    async def handle_add_card(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle adding a card."""
        success = self.budget.add_card(name=arguments["name"])

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

    async def handle_list_cards(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle listing cards."""
        cards = self.budget.get_cards()

        if not cards:
            return [TextContent(type="text", text="No cards found")]

        result = "Payment Cards:\n\n"
        for card in cards:
            result += f"• {card.name}\n"

        return [TextContent(type="text", text=result)]


class BalanceHandlers:
    """Handlers for balance-related tools."""

    def __init__(self, budget: Budget):
        """Initialize handlers with a budget instance."""
        self.budget = budget

    async def handle_get_balance(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle getting a balance."""
        balance = self.budget.get_balance(arguments["type"])
        return [
            TextContent(
                type="text",
                text=f"Balance for '{arguments['type']}': ${balance:.2f}",
            )
        ]

    async def handle_get_all_balances(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle getting all balances."""
        balances = self.budget.get_all_balances()

        if not balances:
            return [TextContent(type="text", text="No balances found")]

        result = "Current Balances:\n\n"
        for balance_type, amount in balances.items():
            result += f"• {balance_type}: ${amount:.2f}\n"

        total = sum(balances.values())
        result += f"\nTotal: ${total:.2f}"

        return [TextContent(type="text", text=result)]

    async def handle_update_balance(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle updating a balance."""
        self.budget.update_balance(type=arguments["type"], amount=arguments["amount"])
        return [
            TextContent(
                type="text",
                text=f"Balance for '{arguments['type']}' set to ${arguments['amount']:.2f}",
            )
        ]


class LimitHandlers:
    """Handlers for spending limit tools."""

    def __init__(self, budget: Budget):
        """Initialize handlers with a budget instance."""
        self.budget = budget

    async def handle_set_spending_limit(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle setting a spending limit."""
        self.budget.set_spending_limit(
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

    async def handle_check_spending_limit(
        self, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle checking spending limits."""
        result = self.budget.check_spending_limit(
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


class ReportHandlers:
    """Handlers for reporting tools."""

    def __init__(self, budget: Budget):
        """Initialize handlers with a budget instance."""
        self.budget = budget

    async def handle_get_daily_spending(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle getting daily spending."""
        days = arguments.get("days", 30)
        daily_spending = self.budget.get_daily_spending(days)

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

    async def handle_get_spending_by_category(
        self, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle getting spending by category."""
        now = datetime.now()
        year = arguments.get("year", now.year)
        month = arguments.get("month", now.month)

        spending = self.budget.get_spending_by_category(year, month)

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


class ToolRouter:
    """Routes tool calls to appropriate handlers."""

    def __init__(self, budget: Budget):
        """Initialize router with all handlers."""
        self.transaction_handlers = TransactionHandlers(budget)
        self.category_handlers = CategoryHandlers(budget)
        self.card_handlers = CardHandlers(budget)
        self.balance_handlers = BalanceHandlers(budget)
        self.limit_handlers = LimitHandlers(budget)
        self.report_handlers = ReportHandlers(budget)

        # Map tool names to handler methods
        self.routes = {
            # Transaction tools
            "add_transaction": self.transaction_handlers.handle_add_transaction,
            "add_multiple_transactions": self.transaction_handlers.handle_add_multiple_transactions,
            "list_transactions": self.transaction_handlers.handle_list_transactions,
            "search_transactions": self.transaction_handlers.handle_search_transactions,
            "update_transaction": self.transaction_handlers.handle_update_transaction,
            "delete_transaction": self.transaction_handlers.handle_delete_transaction,
            # Category tools
            "add_category": self.category_handlers.handle_add_category,
            "list_categories": self.category_handlers.handle_list_categories,
            # Card tools
            "add_card": self.card_handlers.handle_add_card,
            "list_cards": self.card_handlers.handle_list_cards,
            # Balance tools
            "get_balance": self.balance_handlers.handle_get_balance,
            "get_all_balances": self.balance_handlers.handle_get_all_balances,
            "update_balance": self.balance_handlers.handle_update_balance,
            # Limit tools
            "set_spending_limit": self.limit_handlers.handle_set_spending_limit,
            "check_spending_limit": self.limit_handlers.handle_check_spending_limit,
            # Report tools
            "get_daily_spending": self.report_handlers.handle_get_daily_spending,
            "get_spending_by_category": self.report_handlers.handle_get_spending_by_category,
        }

    async def route(self, name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Route a tool call to the appropriate handler."""
        if name not in self.routes:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        try:
            return await self.routes[name](arguments)
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]
