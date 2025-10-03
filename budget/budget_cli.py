from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from budget.budget_core import BudgetManager
from budget.exceptions import BudgetError, DatabaseError, ValidationError

app = typer.Typer(
    help="Personal Budget Tracker - Track your daily transactions and account balances"
)
console = Console()


import os


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Manage the BudgetManager lifecycle.
    """
    db_name = os.environ.get("BUDGET_DB_NAME", "budget.db")
    bm = BudgetManager(db_name)
    bm.__enter__()
    ctx.obj = bm
    ctx.call_on_close(lambda: bm.__exit__(None, None, None))


def _add_funds_interactive(budget_manager: BudgetManager):
    """Interactive mode for adding funds"""
    rprint("\n[bold]Let's set up your initial balances:[/bold]")

    # Add cash
    cash_str = Prompt.ask("How much cash do you have? (£)", default="0")
    try:
        cash = float(cash_str)
        if cash > 0:
            budget_manager.balances_manager.update_balance("cash", cash)
    except ValueError:
        rprint("[red]Invalid amount, setting cash to £0[/red]")

    # Add card balances
    for card in budget_manager.cards:
        card_str = Prompt.ask(f"How much is in {card}? (£)", default="0")
        try:
            amount = float(card_str)
            if amount != 0:
                budget_manager.balances_manager.update_balance(card, amount)
        except ValueError:
            rprint(f"[red]Invalid amount for {card}, setting to £0[/red]")


@app.command()
def add_funds(
    ctx: typer.Context,
    cash: Optional[float] = typer.Option(
        None, "--cash", "-c", help="Amount to add to cash"
    ),
    card: Optional[str] = typer.Option(
        None, "--card", help="Card name to add funds to"
    ),
    amount: Optional[float] = typer.Option(
        None, "--amount", "-a", help="Amount to add to the specified card"
    ),
):
    """Add funds to your accounts"""
    budget_manager = ctx.obj

    try:
        if cash is not None:
            if cash < 0:
                rprint("[red]Warning: Negative amount entered for cash, ignoring[/red]")
            else:
                cur_cash = budget_manager.balances_manager.get_balance("cash")
                budget_manager.balances_manager.update_balance("cash", cur_cash + cash)
                rprint(
                    f"[green]Added £{cash:.2f} to cash. New balance: £{cur_cash + cash:.2f}[/green]"
                )

        if card and amount is not None:
            if card not in budget_manager.cards:
                rprint(
                    f"[red]Card '{card}' not found. Available cards: {', '.join(budget_manager.cards)}[/red]"
                )
                return

            if amount < 0:
                rprint(
                    f"[red]Warning: Negative amount entered for {card}, ignoring[/red]"
                )
            else:
                cur_card = budget_manager.balances_manager.get_balance(card)
                budget_manager.balances_manager.update_balance(card, cur_card + amount)
                rprint(
                    f"[green]Added £{amount:.2f} to {card}. New balance: £{cur_card + amount:.2f}[/green]"
                )

    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def add_transaction(
    ctx: typer.Context,
    t_type: str = typer.Argument(..., help="Transaction type: cash or card"),
    description: str = typer.Argument(..., help="Description of the transaction"),
    amount: float = typer.Argument(..., help="Amount of the transaction"),
    card: Optional[str] = typer.Option(
        None, "--card", "-c", help="Card name (required if type is 'card')"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "--cat", help="Transaction category"
    ),
):
    """Add a new transaction"""
    budget_manager = ctx.obj

    try:
        if t_type not in ["cash", "card"]:
            rprint("[red]Invalid transaction type. Please use 'cash' or 'card'[/red]")
            raise typer.Exit(1)

        if t_type == "card" and not card:
            rprint("[red]Card name is required when transaction type is 'card'[/red]")
            rprint(f"Available cards: {', '.join(budget_manager.cards)}")
            raise typer.Exit(1)

        if t_type == "card" and card not in budget_manager.cards:
            rprint(
                f"[red]Card '{card}' not found. Available cards: {', '.join(budget_manager.cards)}[/red]"
            )
            raise typer.Exit(1)

        if category and category not in budget_manager.categories:
            rprint(
                f"[yellow]Warning: Category '{category}' doesn't exist. Creating it...[/yellow]"
            )
            budget_manager.add_category(category)

        # Process the transaction
        if t_type == "cash":
            current_cash = budget_manager.get_balance("cash")
            new_cash = current_cash - amount
            if new_cash < 0:
                rprint(
                    f"[yellow]Warning: Cash balance will go negative (£{new_cash:.2f})[/yellow]"
                )
                if not Confirm.ask("Continue anyway?"):
                    rprint("[red]Transaction cancelled[/red]")
                    raise typer.Exit(0)
            budget_manager.update_balance("cash", new_cash)
            rprint(
                f"[green]Transaction recorded. Cash balance: £{new_cash:.2f}[/green]"
            )
        else:
            current_card = budget_manager.get_balance(card)
            new_card = current_card - amount
            if new_card < 0:
                rprint(
                    f"[yellow]Warning: {card} balance will go negative (£{new_card:.2f})[/yellow]"
                )
                if not Confirm.ask("Continue anyway?"):
                    rprint("[red]Transaction cancelled[/red]")
                    raise typer.Exit(0)
            budget_manager.update_balance(card, new_card)
            rprint(
                f"[green]Transaction recorded. {card} balance: £{new_card:.2f}[/green]"
            )

        transaction_id = budget_manager.add_transaction(
            t_type, card, description, amount, category
        )

        # Check spending limits
        check_limits(budget_manager, category, card if t_type == "card" else "cash")

    except (ValidationError, DatabaseError) as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def check_limits(budget_manager: BudgetManager, category: Optional[str], source: str):
    """Check and display spending limit warnings"""
    try:
        # Check category limit
        if category:
            limit_info = budget_manager.check_spending_limit(
                category=category, period="monthly"
            )
            if limit_info and limit_info["exceeded"]:
                rprint(
                    f"[bold red]⚠ Monthly limit for '{category}' exceeded![/bold red]"
                )
                rprint(
                    f"Limit: £{limit_info['limit']:.2f} | Spent: £{limit_info['spent']:.2f}"
                )

        # Check source limit
        limit_info = budget_manager.check_spending_limit(
            source=source, period="monthly"
        )
        if limit_info and limit_info["exceeded"]:
            rprint(f"[bold red]⚠ Monthly limit for '{source}' exceeded![/bold red]")
            rprint(
                f"Limit: £{limit_info['limit']:.2f} | Spent: £{limit_info['spent']:.2f}"
            )
    except DatabaseError:
        pass  # Silently ignore limit check errors


@app.command()
def edit_transaction(
    ctx: typer.Context,
    transaction_id: int = typer.Argument(..., help="Transaction ID to edit"),
    t_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="New transaction type"
    ),
    card: Optional[str] = typer.Option(None, "--card", "-c", help="New card name"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="New description"
    ),
    amount: Optional[float] = typer.Option(None, "--amount", "-a", help="New amount"),
    category: Optional[str] = typer.Option(
        None, "--category", "--cat", help="New category"
    ),
):
    """Edit an existing transaction"""
    budget_manager = ctx.obj

    try:
        # Show current transaction
        transaction = budget_manager.get_transaction_by_id(transaction_id)
        if not transaction:
            rprint(f"[red]Transaction with ID {transaction_id} not found[/red]")
            raise typer.Exit(1)

        rprint("\n[bold]Current transaction:[/bold]")
        rprint(f"ID: {transaction['id']}")
        rprint(f"Type: {transaction['type']}")
        rprint(f"Card: {transaction['card'] or 'N/A'}")
        rprint(f"Description: {transaction['description']}")
        rprint(f"Amount: £{transaction['amount']:.2f}")
        rprint(f"Category: {transaction['category'] or 'None'}")

        # Perform edit
        success = budget_manager.update_transaction(
            transaction_id,
            t_type=t_type,
            card=card,
            description=description,
            amount=amount,
            category=category,
        )

        if success:
            rprint("[green]Transaction updated successfully[/green]")
            # Show updated transaction
            updated = budget_manager.get_transaction_by_id(transaction_id)
            rprint("\n[bold]Updated transaction:[/bold]")
            rprint(f"Type: {updated['type']}")
            rprint(f"Card: {updated['card'] or 'N/A'}")
            rprint(f"Description: {updated['description']}")
            rprint(f"Amount: £{updated['amount']:.2f}")
            rprint(f"Category: {updated['category'] or 'None'}")
        else:
            rprint("[yellow]No changes made[/yellow]")

    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def delete_transaction(
    ctx: typer.Context,
    transaction_id: int = typer.Argument(..., help="Transaction ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a transaction"""
    budget_manager = ctx.obj

    try:
        # Show transaction to delete
        transaction = budget_manager.get_transaction_by_id(transaction_id)
        if not transaction:
            rprint(f"[red]Transaction with ID {transaction_id} not found[/red]")
            raise typer.Exit(1)

        rprint("\n[bold red]Transaction to delete:[/bold red]")
        rprint(f"ID: {transaction['id']}")
        rprint(f"Description: {transaction['description']}")
        rprint(f"Amount: £{transaction['amount']:.2f}")
        rprint(f"Date: {transaction['timestamp']}")

        if not force and not Confirm.ask(
            "\nAre you sure you want to delete this transaction?"
        ):
            rprint("[yellow]Deletion cancelled[/yellow]")
            return

        success = budget_manager.delete_transaction(transaction_id)
        if success:
            rprint("[green]Transaction deleted successfully[/green]")
        else:
            rprint("[red]Failed to delete transaction[/red]")

    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def add_card(
    ctx: typer.Context, name: str = typer.Argument(..., help="Name of the new card")
):
    """Add a new payment card"""
    budget_manager = ctx.obj

    try:
        if budget_manager.add_new_card(name):
            rprint(f"[green]Added new card: {name}[/green]")
        else:
            rprint(f"[red]Card '{name}' already exists[/red]")
            raise typer.Exit(1)
    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def add_category(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name of the category"),
    description: str = typer.Option(
        "", "--description", "-d", help="Category description"
    ),
):
    """Add a new transaction category"""
    budget_manager = ctx.obj

    try:
        if budget_manager.add_category(name, description):
            rprint(f"[green]Added new category: {name}[/green]")
        else:
            rprint(f"[red]Category '{name}' already exists[/red]")
            raise typer.Exit(1)
    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_categories(ctx: typer.Context):
    """List all categories"""
    budget_manager = ctx.obj

    try:
        categories = budget_manager.get_categories()

        if not categories:
            rprint(
                "[yellow]No categories found. Use 'add-category' to create one.[/yellow]"
            )
            return

        table = Table(title="Transaction Categories")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")

        for cat in categories:
            table.add_row(cat["name"], cat["description"] or "-")

        console.print(table)
    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def balance(ctx: typer.Context):
    """Show current account balances"""
    budget_manager = ctx.obj

    try:
        table = Table(title="Account Balances")
        table.add_column("Account", style="cyan", no_wrap=True)
        table.add_column("Balance", justify="right", style="green")

        cash_balance = budget_manager.get_balance("cash")
        table.add_row("Cash", f"£{cash_balance:.2f}")

        total = cash_balance
        for card in budget_manager.cards:
            card_balance = budget_manager.get_balance(card)
            table.add_row(card, f"£{card_balance:.2f}")
            total += card_balance

        table.add_section()
        table.add_row("[bold]Total[/bold]", f"[bold]£{total:.2f}[/bold]")

        console.print(table)
    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_transactions(
    ctx: typer.Context,
    limit: int = typer.Option(
        10, "--limit", "-l", help="Number of recent transactions to show"
    ),
):
    """Show recent transactions"""
    budget_manager = ctx.obj

    try:
        transactions = budget_manager.get_recent_transactions(limit)

        if not transactions:
            rprint("[yellow]No transactions found[/yellow]")
            return

        table = Table(title=f"Recent Transactions (Last {len(transactions)})")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Type", style="cyan")
        table.add_column("Card", style="blue")
        table.add_column("Category", style="magenta")
        table.add_column("Description", style="white")
        table.add_column("Amount", justify="right", style="red")
        table.add_column("Date", style="dim")

        for t in transactions:
            table.add_row(
                str(t["id"]),
                t["type"],
                t["card"] or "N/A",
                t["category"] or "-",
                t["description"],
                f"£{t['amount']:.2f}",
                t["timestamp"],
            )

        console.print(table)
    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Option(
        "", "--query", "-q", help="Search in description or card"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by category"
    ),
    card: Optional[str] = typer.Option(None, "--card", help="Filter by card"),
    start_date: Optional[str] = typer.Option(
        None, "--start", help="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
    min_amount: Optional[float] = typer.Option(None, "--min", help="Minimum amount"),
    max_amount: Optional[float] = typer.Option(None, "--max", help="Maximum amount"),
):
    """Search and filter transactions"""
    budget_manager = ctx.obj

    try:
        transactions = budget_manager.search_transactions(
            query=query,
            category=category,
            card=card,
            start_date=start_date,
            end_date=end_date,
            min_amount=min_amount,
            max_amount=max_amount,
        )

        if not transactions:
            rprint("[yellow]No transactions found matching your criteria[/yellow]")
            return

        table = Table(title=f"Search Results ({len(transactions)} transactions)")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Type", style="cyan")
        table.add_column("Card", style="blue")
        table.add_column("Category", style="magenta")
        table.add_column("Description", style="white")
        table.add_column("Amount", justify="right", style="red")
        table.add_column("Date", style="dim")

        total = 0
        for t in transactions:
            table.add_row(
                str(t["id"]),
                t["type"],
                t["card"] or "N/A",
                t["category"] or "-",
                t["description"],
                f"£{t['amount']:.2f}",
                t["timestamp"],
            )
            total += t["amount"]

        console.print(table)
        rprint(f"\n[bold]Total amount: £{total:.2f}[/bold]")

    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def monthly_spending(
    ctx: typer.Context,
    year: int = typer.Option(
        None, "--year", "-y", help="Year (defaults to current year)"
    ),
    month: int = typer.Option(
        None, "--month", "-m", help="Month (1-12, defaults to current month)"
    ),
    by_category: bool = typer.Option(
        False, "--by-category", help="Show breakdown by category instead of source"
    ),
):
    """Show monthly spending breakdown"""
    budget_manager = ctx.obj
    from datetime import datetime

    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    if not (1 <= month <= 12):
        rprint("[red]Month must be between 1 and 12[/red]")
        raise typer.Exit(1)

    try:
        month_names = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        month_name = month_names[month - 1]

        if by_category:
            spending_data = budget_manager.get_spending_by_category(year, month)

            if not spending_data:
                rprint(f"[yellow]No transactions found for {year}-{month:02d}[/yellow]")
                return

            table = Table(title=f"Monthly Spending by Category - {month_name} {year}")
            table.add_column("Category", style="cyan", no_wrap=True)
            table.add_column("Amount Spent", justify="right", style="red")

            total_spent = sum(amount for _, amount in spending_data)

            for category, amount_spent in spending_data:
                percentage = (
                    (amount_spent / total_spent * 100) if total_spent > 0 else 0
                )
                table.add_row(category, f"£{amount_spent:.2f} ({percentage:.1f}%)")

            table.add_section()
            table.add_row("[bold]Total[/bold]", f"[bold]£{total_spent:.2f}[/bold]")

        else:
            spending_data = budget_manager.get_spending_with_balance_percentage(
                year, month
            )

            if not spending_data:
                rprint(f"[yellow]No transactions found for {year}-{month:02d}[/yellow]")
                return

            table = Table(title=f"Monthly Spending by Source - {month_name} {year}")
            table.add_column("Source", style="cyan", no_wrap=True)
            table.add_column("Amount Spent", justify="right", style="red")
            table.add_column("Current Balance", justify="right", style="green")
            table.add_column("% of Balance Spent", justify="right", style="blue")

            total_spent = sum(amount for _, amount, _, _ in spending_data)
            total_balance = sum(balance for _, _, balance, _ in spending_data)

            for (
                source,
                amount_spent,
                current_balance,
                balance_percentage,
            ) in spending_data:
                if balance_percentage == float("inf"):
                    percentage_display = "∞%"
                else:
                    percentage_display = f"{balance_percentage:.1f}%"

                table.add_row(
                    source,
                    f"£{amount_spent:.2f}",
                    f"£{current_balance:.2f}",
                    percentage_display,
                )

            table.add_section()
            total_percentage = (
                (total_spent / total_balance * 100) if total_balance > 0 else 0
            )
            table.add_row(
                "[bold]Total[/bold]",
                f"[bold]£{total_spent:.2f}[/bold]",
                f"[bold]£{total_balance:.2f}[/bold]",
                f"[bold]{total_percentage:.1f}%[/bold]",
            )

        console.print(table)

    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def set_limit(
    ctx: typer.Context,
    amount: float = typer.Argument(..., help="Limit amount"),
    period: str = typer.Option(
        "monthly", "--period", "-p", help="Period: daily, weekly, monthly, yearly"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Category to limit"
    ),
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Source to limit (cash or card name)"
    ),
):
    """Set a spending limit"""
    budget_manager = ctx.obj

    try:
        budget_manager.set_spending_limit(amount, period, category, source)

        limit_desc = []
        if category:
            limit_desc.append(f"category '{category}'")
        if source:
            limit_desc.append(f"source '{source}'")
        if not limit_desc:
            limit_desc.append("overall spending")

        rprint(
            f"[green]Set {period} limit of £{amount:.2f} for {' and '.join(limit_desc)}[/green]"
        )

    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_limits(ctx: typer.Context):
    """List all spending limits"""
    budget_manager = ctx.obj

    try:
        limits = budget_manager.get_spending_limits()

        if not limits:
            rprint(
                "[yellow]No spending limits set. Use 'set-limit' to create one.[/yellow]"
            )
            return

        table = Table(title="Spending Limits")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Period", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Source", style="blue")
        table.add_column("Limit", justify="right", style="green")
        table.add_column("Status", style="white")

        for limit in limits:
            # Check current status
            status_info = budget_manager.check_spending_limit(
                category=limit["category"],
                source=limit["source"],
                period=limit["period"],
            )

            if status_info:
                status = f"£{status_info['spent']:.2f} / £{status_info['limit']:.2f}"
                if status_info["exceeded"]:
                    status = f"[red]{status} ⚠[/red]"
                else:
                    status = f"[green]{status} ✓[/green]"
            else:
                status = "-"

            table.add_row(
                str(limit["id"]),
                limit["period"],
                limit["category"] or "All",
                limit["source"] or "All",
                f"£{limit['limit_amount']:.2f}",
                status,
            )

        console.print(table)

    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def export(
    ctx: typer.Context,
    filepath: str = typer.Argument(..., help="Output file path"),
    format: str = typer.Option(
        "csv", "--format", "-f", help="Export format: csv or json"
    ),
    start_date: Optional[str] = typer.Option(
        None, "--start", help="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
):
    """Export transactions to CSV or JSON"""
    budget_manager = ctx.obj

    try:
        if format.lower() == "csv":
            budget_manager.export_to_csv(filepath, start_date, end_date)
            rprint(f"[green]Transactions exported to {filepath} (CSV)[/green]")
        elif format.lower() == "json":
            budget_manager.export_to_json(filepath, start_date, end_date)
            rprint(f"[green]Transactions exported to {filepath} (JSON)[/green]")
        else:
            rprint("[red]Invalid format. Use 'csv' or 'json'[/red]")
            raise typer.Exit(1)

    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def tui(ctx: typer.Context):
    """Launch the interactive TUI (lazygit-style)"""
    budget_manager = ctx.obj
    from budget.budget_tui import run_tui

    run_tui(budget_manager.db_name)


@app.command()
def interactive(ctx: typer.Context):
    """Start interactive mode for adding multiple transactions"""
    budget_manager = ctx.obj

    rprint(
        "\n[bold blue]=== Personal Budget Tracker - Interactive Mode ===[/bold blue]"
    )
    rprint("Welcome to your personal budget tracking application!")
    rprint(
        "This app will help you track your daily transactions and account balances.\n"
    )

    # Add funds first
    _add_funds_interactive(budget_manager)

    while True:
        rprint("\n[bold]New transaction entry (or type 'exit' to finish):[/bold]")
        t_type = Prompt.ask(
            "Transaction type", choices=["cash", "card", "exit"], default="cash"
        )

        if t_type == "exit":
            break

        card = None
        if t_type == "card":
            rprint(f"Available cards: {', '.join(budget_manager.cards)}")
            card_choice = Prompt.ask(
                "Which card did you use? (or type 'new' to add a card)"
            )

            if card_choice.lower() == "new":
                new_card_name = Prompt.ask("Enter the name of the new card")
                if new_card_name:
                    try:
                        if budget_manager.add_new_card(new_card_name):
                            card = new_card_name
                        else:
                            rprint(f"[red]Card '{new_card_name}' already exists[/red]")
                            continue
                    except BudgetError as e:
                        rprint(f"[red]Error: {e}[/red]")
                        continue
                else:
                    rprint("[red]Card name cannot be empty[/red]")
                    continue
            elif card_choice not in budget_manager.cards:
                rprint(
                    f"[red]Invalid card name. Available cards: {', '.join(budget_manager.cards)}[/red]"
                )
                continue
            else:
                card = card_choice

        # Category selection
        category = None
        if budget_manager.categories:
            rprint(f"Available categories: {', '.join(budget_manager.categories)}")
            cat_choice = Prompt.ask(
                "Category (leave blank to skip, or type 'new' to add)"
            )
            if cat_choice and cat_choice.lower() != "new":
                category = cat_choice
            elif cat_choice.lower() == "new":
                new_cat = Prompt.ask("Enter new category name")
                if new_cat:
                    try:
                        budget_manager.add_category(new_cat)
                        category = new_cat
                    except BudgetError as e:
                        rprint(f"[red]Error: {e}[/red]")

        description = Prompt.ask("Description of the transaction")
        if not description:
            rprint("[red]Description cannot be empty[/red]")
            continue

        amount_str = Prompt.ask("Amount (£)")
        try:
            amount = float(amount_str)
            if amount <= 0:
                rprint("[red]Amount must be positive[/red]")
                continue
        except ValueError:
            rprint("[red]Invalid amount. Please enter a valid number.[/red]")
            continue

        # Process the transaction
        try:
            if t_type == "cash":
                current_cash = budget_manager.get_balance("cash")
                new_cash = current_cash - amount
                if new_cash < 0:
                    rprint(
                        f"[yellow]Warning: Cash balance will go negative (£{new_cash:.2f})[/yellow]"
                    )
                    if not Confirm.ask("Continue anyway?"):
                        continue
                budget_manager.update_balance("cash", new_cash)
                rprint(
                    f"[green]Transaction recorded. Cash balance: £{new_cash:.2f}[/green]"
                )
            else:
                current_card = budget_manager.get_balance(card)
                new_card = current_card - amount
                if new_card < 0:
                    rprint(
                        f"[yellow]Warning: {card} balance will go negative (£{new_card:.2f})[/yellow]"
                    )
                    if not Confirm.ask("Continue anyway?"):
                        continue
                budget_manager.update_balance(card, new_card)
                rprint(
                    f"[green]Transaction recorded. {card} balance: £{new_card:.2f}[/green]"
                )

            budget_manager.add_transaction(t_type, card, description, amount, category)

            # Check limits
            check_limits(budget_manager, category, card if t_type == "card" else "cash")

        except BudgetError as e:
            rprint(f"[red]Error: {e}[/red]")
            continue

    rprint("\n[bold blue]=== Final Account Balances ===[/bold blue]")

    # Display final balances
    try:
        table = Table(title="Account Balances")
        table.add_column("Account", style="cyan", no_wrap=True)
        table.add_column("Balance", justify="right", style="green")

        cash_balance = budget_manager.balances_manager.get_balance("cash")
        table.add_row("Cash", f"£{cash_balance:.2f}")

        total = cash_balance
        for card in budget_manager.cards:
            card_balance = budget_manager.balances_manager.get_balance(card)
            table.add_row(card, f"£{card_balance:.2f}")
            total += card_balance

        table.add_section()
        table.add_row("[bold]Total[/bold]", f"[bold]£{total:.2f}[/bold]")

        console.print(table)
    except BudgetError as e:
        rprint(f"[red]Error: {e}[/red]")

    rprint("\n[green]Thank you for using the Budget Tracker![/green]")
