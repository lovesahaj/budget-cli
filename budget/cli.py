"""Simple CLI interface for budget tracker."""

import sys
from datetime import datetime

import click

from budget.budget import Budget


@click.group()
@click.option("--db", default="budget.db", help="Database file name")
@click.pass_context
def cli(ctx, db):
    """Personal Budget Tracker - Track your expenses and income."""
    ctx.ensure_object(dict)
    ctx.obj["budget"] = Budget(db)


# Transaction commands
@cli.command()
@click.argument("type", type=click.Choice(["cash", "card"]))
@click.argument("description")
@click.argument("amount", type=float)
@click.option("--card", help="Card name (for card transactions)")
@click.option("--category", help="Transaction category")
@click.pass_context
def add(ctx, type, description, amount, card, category):
    """Add a new transaction."""
    budget = ctx.obj["budget"]
    try:
        txn_id = budget.add_transaction(type, description, amount, card, category)
        click.echo(f"Transaction added with ID: {txn_id}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("transaction_id", type=int)
@click.pass_context
def delete(ctx, transaction_id):
    """Delete a transaction."""
    budget = ctx.obj["budget"]
    if budget.delete_transaction(transaction_id):
        click.echo(f"Transaction {transaction_id} deleted")
    else:
        click.echo(f"Transaction {transaction_id} not found", err=True)
        sys.exit(1)


@cli.command()
@click.option("--limit", default=10, help="Number of transactions to show")
@click.option("--query", help="Search text")
@click.option("--category", help="Filter by category")
@click.option("--card", help="Filter by card")
@click.pass_context
def list(ctx, limit, query, category, card):
    """List recent transactions."""
    budget = ctx.obj["budget"]

    if query or category or card:
        txns = budget.search_transactions(query=query or "", category=category, card=card)
    else:
        txns = budget.get_recent_transactions(limit)

    if not txns:
        click.echo("No transactions found")
        return

    click.echo(f"\n{'ID':<6} {'Date':<12} {'Type':<6} {'Card':<12} {'Category':<15} {'Amount':>10} {'Description'}")
    click.echo("-" * 90)

    for txn in txns:
        date = txn.timestamp.strftime("%Y-%m-%d") if txn.timestamp else "N/A"
        card_display = (txn.card or "")[:12]
        category_display = (txn.category or "")[:15]
        click.echo(
            f"{txn.id:<6} {date:<12} {txn.type:<6} {card_display:<12} {category_display:<15} ${txn.amount:>9.2f} {txn.description}"
        )


# Category commands
@cli.group()
def category():
    """Manage categories."""
    pass


@category.command(name="add")
@click.argument("name")
@click.option("--description", default="", help="Category description")
@click.pass_context
def category_add(ctx, name, description):
    """Add a new category."""
    budget = ctx.obj["budget"]
    if budget.add_category(name, description):
        click.echo(f"Category '{name}' added")
    else:
        click.echo(f"Category '{name}' already exists", err=True)


@category.command(name="list")
@click.pass_context
def category_list(ctx):
    """List all categories."""
    budget = ctx.obj["budget"]
    categories = budget.get_categories()

    if not categories:
        click.echo("No categories found")
        return

    click.echo(f"\n{'Name':<20} {'Description'}")
    click.echo("-" * 60)
    for cat in categories:
        click.echo(f"{cat.name:<20} {cat.description or ''}")


# Balance commands
@cli.group()
def balance():
    """Manage balances."""
    pass


@balance.command(name="show")
@click.option("--type", help="Show specific balance type")
@click.pass_context
def balance_show(ctx, type):
    """Show current balances."""
    budget = ctx.obj["budget"]

    if type:
        amount = budget.get_balance(type)
        click.echo(f"{type}: ${amount:.2f}")
    else:
        balances = budget.get_all_balances()
        if not balances:
            click.echo("No balances found")
            return

        click.echo(f"\n{'Type':<15} {'Amount':>12}")
        click.echo("-" * 30)
        for b_type, amount in balances.items():
            click.echo(f"{b_type:<15} ${amount:>11.2f}")


@balance.command(name="set")
@click.argument("type")
@click.argument("amount", type=float)
@click.pass_context
def balance_set(ctx, type, amount):
    """Set a balance amount."""
    budget = ctx.obj["budget"]
    budget.update_balance(type, amount)
    click.echo(f"Balance for '{type}' set to ${amount:.2f}")


# Limit commands
@cli.group()
def limit():
    """Manage spending limits."""
    pass


@limit.command(name="set")
@click.argument("amount", type=float)
@click.option("--period", type=click.Choice(["daily", "weekly", "monthly", "yearly"]), default="monthly")
@click.option("--category", help="Category to limit")
@click.option("--source", help="Source to limit (card name or 'cash')")
@click.pass_context
def limit_set(ctx, amount, period, category, source):
    """Set a spending limit."""
    budget = ctx.obj["budget"]
    budget.set_spending_limit(amount, period, category, source)
    click.echo(f"Spending limit set: ${amount:.2f} per {period}")


@limit.command(name="check")
@click.option("--period", default="monthly")
@click.option("--category", help="Category to check")
@click.option("--source", help="Source to check")
@click.pass_context
def limit_check(ctx, period, category, source):
    """Check spending against limits."""
    budget = ctx.obj["budget"]
    result = budget.check_spending_limit(category, source, period)

    if result["limit"] == 0:
        click.echo("No limit set for these criteria")
        return

    click.echo(f"\nSpending Limit Check ({period}):")
    click.echo(f"  Limit:     ${result['limit']:.2f}")
    click.echo(f"  Spent:     ${result['spent']:.2f}")
    click.echo(f"  Remaining: ${result['remaining']:.2f}")
    if result["exceeded"]:
        click.echo("  Status:    EXCEEDED", err=True)
    else:
        click.echo("  Status:    OK")


# Report commands
@cli.group()
def report():
    """View spending reports."""
    pass


@report.command(name="daily")
@click.option("--days", default=7, help="Number of days to show")
@click.pass_context
def report_daily(ctx, days):
    """Show daily spending report."""
    budget = ctx.obj["budget"]
    daily = budget.get_daily_spending(days)

    if not daily:
        click.echo("No spending data found")
        return

    click.echo(f"\n{'Date':<12} {'Amount':>10}")
    click.echo("-" * 25)
    for date, amount in daily:
        click.echo(f"{date:<12} ${amount:>9.2f}")


@report.command(name="category")
@click.option("--year", type=int, help="Year (default: current)")
@click.option("--month", type=int, help="Month (default: current)")
@click.pass_context
def report_category(ctx, year, month):
    """Show spending by category."""
    budget = ctx.obj["budget"]

    now = datetime.now()
    year = year or now.year
    month = month or now.month

    spending = budget.get_spending_by_category(year, month)

    if not spending:
        click.echo(f"No spending data for {year}-{month:02d}")
        return

    total = sum(spending.values())

    click.echo(f"\nSpending by Category ({year}-{month:02d}):")
    click.echo(f"{'Category':<20} {'Amount':>10} {'Percent':>8}")
    click.echo("-" * 42)

    for category, amount in sorted(spending.items(), key=lambda x: x[1], reverse=True):
        pct = (amount / total * 100) if total > 0 else 0
        click.echo(f"{category:<20} ${amount:>9.2f} {pct:>7.1f}%")

    click.echo("-" * 42)
    click.echo(f"{'Total':<20} ${total:>9.2f} {'100.0%':>8}")


# Import commands
@cli.group(name="import")
def import_group():
    """Import transactions from PDF, images, or email."""
    pass


@import_group.command(name="pdf")
@click.argument("path")
@click.option("--context", default="bank statement or receipt", help="Context hint for extraction")
@click.option("--provider", type=click.Choice(["anthropic", "local"]), default="anthropic", help="LLM provider to use")
@click.option("--base-url", help="Base URL for local LLM (e.g., http://localhost:1234/v1)")
@click.option("--model", help="Model name for local LLM")
@click.pass_context
def import_pdf(ctx, path, context, provider, base_url, model):
    """Import transactions from PDF file(s)."""
    budget = ctx.obj["budget"]

    try:
        from budget.importers.pdf import PDFImporter
        from pathlib import Path

        importer = PDFImporter(provider=provider, base_url=base_url, model=model)
        pdf_path = Path(path)

        if pdf_path.is_dir():
            # Import from directory
            result = importer.extract_from_directory(path, context=context)
            transactions = result["transactions"]
            click.echo(f"\nProcessed {result['files_processed']} PDF files")
            if result['files_failed'] > 0:
                click.echo(f"Failed: {result['files_failed']} files", err=True)
        else:
            # Import single file
            transactions = importer.extract_from_file(path, context)

        if not transactions:
            click.echo("No transactions found in PDF(s)")
            return

        # Import with deduplication
        stats = budget.import_transactions(transactions, "pdf")

        click.echo(f"\nImport Summary:")
        click.echo(f"  Total found:     {stats['total']}")
        click.echo(f"  Imported:        {stats['imported']}")
        click.echo(f"  Duplicates:      {stats['duplicates']}")
        if stats['errors'] > 0:
            click.echo(f"  Errors:          {stats['errors']}", err=True)

    except Exception as e:
        click.echo(f"Error importing PDF: {e}", err=True)
        sys.exit(1)


@import_group.command(name="image")
@click.argument("path")
@click.option("--context", default="receipt", help="Context hint for extraction")
@click.option("--provider", type=click.Choice(["anthropic", "local"]), default="anthropic", help="LLM provider to use")
@click.option("--base-url", help="Base URL for local LLM (e.g., http://localhost:1234/v1)")
@click.option("--model", help="Model name for local LLM")
@click.option("--multimodal/--no-multimodal", default=True, help="Use direct image input for multimodal models (default: enabled)")
@click.pass_context
def import_image(ctx, path, context, provider, base_url, model, multimodal):
    """Import transactions from image file(s) (receipts, screenshots).

    For multimodal models like Gemma 3, images are automatically normalized to 896x896.
    """
    budget = ctx.obj["budget"]

    try:
        from budget.importers.image import ImageImporter
        from pathlib import Path

        importer = ImageImporter(
            provider=provider,
            base_url=base_url,
            model=model,
            use_multimodal=multimodal,
        )
        image_path = Path(path)

        if image_path.is_dir():
            # Import from directory
            result = importer.extract_from_directory(path, context=context)
            transactions = result["transactions"]
            click.echo(f"\nProcessed {result['files_processed']} image files")
            if result['files_failed'] > 0:
                click.echo(f"Failed: {result['files_failed']} files", err=True)
        else:
            # Import single file
            transactions = importer.extract_from_file(path, context)

        if not transactions:
            click.echo("No transactions found in image(s)")
            return

        # Import with deduplication
        stats = budget.import_transactions(transactions, "image")

        click.echo(f"\nImport Summary:")
        click.echo(f"  Total found:     {stats['total']}")
        click.echo(f"  Imported:        {stats['imported']}")
        click.echo(f"  Duplicates:      {stats['duplicates']}")
        if stats['errors'] > 0:
            click.echo(f"  Errors:          {stats['errors']}", err=True)

    except Exception as e:
        click.echo(f"Error importing images: {e}", err=True)
        sys.exit(1)


@import_group.command(name="email")
@click.option("--email", required=True, help="Your email address")
@click.option("--password", required=True, prompt=True, hide_input=True, help="Email password or app password")
@click.option("--provider", type=click.Choice(["gmail", "outlook"]), default="gmail", help="Email provider")
@click.option("--days", default=30, help="Number of days to scan back")
@click.option("--llm-provider", type=click.Choice(["anthropic", "local"]), default="anthropic", help="LLM provider to use")
@click.option("--base-url", help="Base URL for local LLM (e.g., http://localhost:1234/v1)")
@click.option("--model", help="Model name for local LLM")
@click.pass_context
def import_email(ctx, email, password, provider, days, llm_provider, base_url, model):
    """Import transactions from email (Gmail or Outlook).

    For Gmail, you MUST use an App Password, not your regular password.
    Generate one at: https://myaccount.google.com/apppasswords
    """
    budget = ctx.obj["budget"]

    try:
        from budget.importers.email import EmailImporter

        importer = EmailImporter(provider=llm_provider, base_url=base_url, model=model)

        # Connect to email
        click.echo(f"Connecting to {provider}...")
        if provider == "gmail":
            importer.connect_gmail(email, password)
        else:
            importer.connect_outlook(email, password)

        # Scan for transactions
        click.echo(f"Scanning last {days} days for transaction emails...")
        transactions = importer.scan_for_transactions(days=days)

        if not transactions:
            click.echo("No transactions found in emails")
            importer.disconnect()
            return

        # Import with deduplication
        stats = budget.import_transactions(transactions, "email")

        click.echo(f"\nImport Summary:")
        click.echo(f"  Total found:     {stats['total']}")
        click.echo(f"  Imported:        {stats['imported']}")
        click.echo(f"  Duplicates:      {stats['duplicates']}")
        if stats['errors'] > 0:
            click.echo(f"  Errors:          {stats['errors']}", err=True)

        importer.disconnect()

    except Exception as e:
        click.echo(f"Error importing from email: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
