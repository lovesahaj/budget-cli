from __future__ import annotations

import time
from datetime import datetime
from typing import List, Tuple

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
)

from budget.budget_core import BudgetManager


class BalancePanel(Static):
    """Displays current balances for cash and cards with totals."""

    def __init__(self, manager: BudgetManager) -> None:
        super().__init__()
        self.manager = manager

    def on_mount(self) -> None:
        self.render_balances()

    def render_balances(self) -> None:
        balances = self.manager.get_all_balances()
        total = sum(balances.values())

        lines = ["[bold cyan]💰 Account Balances[/bold cyan]", ""]

        # Sort balances - cash first, then alphabetically
        sorted_balances = sorted(balances.items(), key=lambda x: (x[0] != "cash", x[0]))

        for name, amt in sorted_balances:
            icon = "💵" if name == "cash" else "💳"
            color = "green" if amt > 0 else "red" if amt < 0 else "dim"
            lines.append(
                f"{icon} [bold]{name:.<12}[/bold] [{color}]£{amt:>8,.2f}[/{color}]"
            )

        lines.append("")
        lines.append("─" * 28)
        total_color = (
            "bold green" if total > 0 else "bold red" if total < 0 else "bold dim"
        )
        lines.append(
            f"[bold]💎 Total.........[/bold] [{total_color}]£{total:>8,.2f}[/{total_color}]"
        )

        self.update("\n".join(lines))


class SpendingSummaryPanel(Static):
    """Displays monthly spending summary."""

    def __init__(self, manager: BudgetManager) -> None:
        super().__init__()
        self.manager = manager

    def on_mount(self) -> None:
        self.render_summary()

    def render_summary(self) -> None:
        now = datetime.now()
        spending_data = self.manager.get_spending_by_category(now.year, now.month)

        lines = ["[bold magenta]📊 This Month's Spending[/bold magenta]", ""]

        if spending_data:
            total = sum(amt for _, amt in spending_data)
            lines.append(f"[dim]{now.strftime('%B %Y')}[/dim]")
            lines.append("")

            # Show top 5 categories
            for i, (cat, amt) in enumerate(spending_data[:5]):
                percentage = (amt / total * 100) if total > 0 else 0
                bar_length = int(percentage / 5)  # 20 chars max
                bar = "█" * bar_length
                category_display = cat[:12] if cat else "Other"
                lines.append(
                    f"[cyan]{category_display:.<12}[/cyan] [yellow]£{amt:>6.2f}[/yellow]"
                )
                lines.append(f"  [dim]{bar}[/dim] [dim]{percentage:.0f}%[/dim]")

            if len(spending_data) > 5:
                other = sum(amt for _, amt in spending_data[5:])
                lines.append(f"[dim]...and {len(spending_data) - 5} more[/dim]")

            lines.append("")
            lines.append("─" * 28)
            lines.append(
                f"[bold white]Total Spent....[/bold white] [bold red]£{total:>7.2f}[/bold red]"
            )
        else:
            lines.append("[dim]No transactions this month[/dim]")

        self.update("\n".join(lines))


class QuickStatsPanel(Static):
    """Displays quick statistics and limits."""

    def __init__(self, manager: BudgetManager) -> None:
        super().__init__()
        self.manager = manager

    def on_mount(self) -> None:
        self.render_stats()

    def render_stats(self) -> None:
        lines = ["[bold yellow]⚡ Quick Stats[/bold yellow]", ""]

        # Transaction count
        recent = self.manager.get_recent_transactions(1000)
        total_transactions = len(recent)

        # Today's spending
        now = datetime.now()
        today_spending = sum(
            t["amount"] for t in recent if t["timestamp"].date() == now.date()
        )

        # This week's spending
        week_spending = 0
        for t in recent:
            days_diff = (now - t["timestamp"]).days
            if days_diff <= 7:
                week_spending += t["amount"]

        # Check limits
        limits = self.manager.get_spending_limits()
        limits_exceeded = 0
        for limit in limits:
            check = self.manager.check_spending_limit(
                category=limit["category"],
                source=limit["source"],
                period=limit["period"],
            )
            if check and check["exceeded"]:
                limits_exceeded += 1

        lines.append(f"📝 Total Transactions: [bold]{total_transactions}[/bold]")
        lines.append(f"🕐 Today's Spending: [yellow]£{today_spending:.2f}[/yellow]")
        lines.append(f"📅 This Week: [yellow]£{week_spending:.2f}[/yellow]")
        lines.append("")

        if limits:
            status_icon = "⚠️" if limits_exceeded > 0 else "✅"
            status_color = "red" if limits_exceeded > 0 else "green"
            lines.append(
                f"{status_icon} Budget Limits: [{status_color}]{len(limits) - limits_exceeded}/{len(limits)} OK[/{status_color}]"
            )
            if limits_exceeded > 0:
                lines.append(f"   [red]{limits_exceeded} limit(s) exceeded[/red]")
        else:
            lines.append("💡 [dim]No budget limits set[/dim]")

        self.update("\n".join(lines))


class RecentTransactionsTable(DataTable):
    """Table showing recent transactions with enhanced styling."""

    def __init__(self, manager: BudgetManager, limit: int = 30) -> None:
        super().__init__()
        self.manager = manager
        self.limit = limit
        self._column_keys: list[str] = []

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True

        # Only add columns if they don't exist yet
        if not self.columns:
            columns = [
                ("ID", 5),
                ("Type", 8),
                ("Card", 10),
                ("Category", 15),
                ("Description", 30),
                ("Amount", 10),
                ("Date", 19),
            ]
            self._column_keys = [label.lower() for label, _ in columns]
            for key, (label, width) in zip(self._column_keys, columns):
                self.add_column(label, key=key, width=width)

        try:
            transactions = self.manager.get_recent_transactions(self.limit)
            for t in transactions:
                card_display = t["card"] or "-"
                category_display = t["category"] or "-"
                amount_display = (
                    f"£{t['amount']:,.2f}" if t["amount"] is not None else "-"
                )

                # Truncate long descriptions
                desc = t["description"]
                if len(desc) > 30:
                    desc = desc[:27] + "..."

                self.add_row(
                    str(t["id"]),
                    t["type"],
                    card_display,
                    category_display,
                    desc,
                    amount_display,
                    t["timestamp"].strftime("%Y-%m-%d %H:%M"),
                )
        except Exception as e:
            pass


class DailySpendBars(Static):
    """ASCII bar chart for daily spending over a time window."""

    days = reactive(30)
    data: List[Tuple[str, float]] = reactive([])

    def __init__(self, manager: BudgetManager, days: int = 30) -> None:
        super().__init__()
        self.manager = manager
        self.days = days

    def on_mount(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        self.data = self.manager.get_daily_spending(self.days)
        self.render_chart()

    def render_chart(self) -> None:
        if not self.data:
            self.update("[dim]No spending data available[/dim]")
            return

        max_val = max((v for _, v in self.data), default=0.0)
        max_val = max_val or 1.0
        width = max(10, self.size.width - 15)

        lines: List[str] = [
            f"[bold cyan]📈 Daily Spending[/bold cyan] [dim](last {self.days} days)[/dim]",
            "",
        ]

        # Only show last 15 days to avoid clutter
        display_data = self.data[-15:]

        for day, total in display_data:
            bar_len = int((total / max_val) * width)

            # Color based on amount
            if total == 0:
                bar = "[dim]" + "▪" * 1 + "[/dim]"
                amount_color = "dim"
            elif total < max_val * 0.3:
                bar = "[green]" + "█" * bar_len + "[/green]"
                amount_color = "green"
            elif total < max_val * 0.7:
                bar = "[yellow]" + "█" * bar_len + "[/yellow]"
                amount_color = "yellow"
            else:
                bar = "[red]" + "█" * bar_len + "[/red]"
                amount_color = "red"

            ymd = day[5:]  # MM-DD for brevity
            lines.append(
                f"[dim]{ymd}[/dim] {bar} [{amount_color}]£{total:>6.2f}[/{amount_color}]"
            )

        lines.append("")
        lines.append(
            f"[dim]Max: £{max_val:.2f} | Avg: £{sum(v for _, v in self.data) / len(self.data):.2f}[/dim]"
        )

        self.update("\n".join(lines))

    def on_resize(self) -> None:
        self.render_chart()


class AddTransactionScreen(ModalScreen):
    """Screen for adding a new transaction."""

    CSS = """
    AddTransactionScreen {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: auto;
        background: $panel;
        padding: 1 2;
        border: thick $primary;
    }

    #dialog > * {
        margin-bottom: 1;
    }

    .label {
        width: 15;
    }

    Input, Select {
        width: 1fr;
    }

    #buttons {
        align: right middle;
        margin-top: 1;
    }
    """

    def __init__(self, manager: BudgetManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.cards = self.manager.cards
        self.categories = self.manager.categories

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Add New Transaction", id="title")

            with Horizontal():
                yield Label("Type", classes="label")
                yield Select(
                    [("Card", "card"), ("Cash", "cash")], value="card", id="type"
                )

            with Horizontal():
                yield Label("Card", classes="label")
                yield Select([(c, c) for c in self.cards], allow_blank=True, id="card")

            with Horizontal():
                yield Label("Description", classes="label")
                yield Input(placeholder="e.g., Coffee", id="description")

            with Horizontal():
                yield Label("Amount", classes="label")
                yield Input(placeholder="e.g., 3.50", id="amount")

            with Horizontal():
                yield Label("Category", classes="label")
                yield Select(
                    [(c, c) for c in self.categories], allow_blank=True, id="category"
                )

            with Horizontal(id="buttons"):
                yield Button("Add", variant="primary", id="add")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            self.add_transaction()
        else:
            self.app.pop_screen()

    def add_transaction(self) -> None:
        try:
            type = self.query_one("#type", Select).value
            card = self.query_one("#card", Select).value
            description = self.query_one("#description", Input).value
            amount_str = self.query_one("#amount", Input).value
            category = self.query_one("#category", Select).value

            if not all([type, description, amount_str]):
                self.app.notify(
                    "Type, description, and amount are required.", severity="error"
                )
                return

            try:
                amount = float(amount_str)
            except ValueError:
                self.app.notify("Invalid amount.", severity="error")
                return

            # Convert Select.BLANK to None
            card_value = None if card == Select.BLANK else card
            category_value = None if category == Select.BLANK else category

            self.manager.add_transaction(
                t_type=type,
                card=card_value if type == "card" else None,
                description=description,
                amount=amount,
                category=category_value,
            )
            self.app.pop_screen()
            self.app.action_refresh()
            self.app.notify("Transaction added successfully.", severity="information")
        except Exception as e:
            self.app.notify(f"Error adding transaction: {e}", severity="error")


class DeleteTransactionScreen(ModalScreen):
    """Screen to confirm transaction deletion."""

    CSS = """
    DeleteTransactionScreen {
        align: center middle;
    }

    #delete-dialog {
        width: 50;
        height: auto;
        background: $panel;
        padding: 1 2;
        border: thick $error;
    }

    #delete-dialog > * {
        margin-bottom: 1;
    }
    """

    def __init__(self, transaction_id: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.transaction_id = transaction_id

    def compose(self) -> ComposeResult:
        with Vertical(id="delete-dialog"):
            yield Label("Are you sure you want to delete this transaction?")
            with Horizontal(id="buttons"):
                yield Button("Delete", variant="error", id="delete")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete":
            self.app.delete_transaction(self.transaction_id)
            self.app.pop_screen()
        else:
            self.app.pop_screen()


class EditTransactionScreen(ModalScreen):
    """Screen for editing an existing transaction."""

    CSS = """
    EditTransactionScreen {
        align: center middle;
    }

    #edit-dialog {
        width: 60;
        height: auto;
        background: $panel;
        padding: 1 2;
        border: thick $primary;
    }

    #edit-dialog > * {
        margin-bottom: 1;
    }

    .label {
        width: 15;
    }

    Input, Select {
        width: 1fr;
    }

    #buttons {
        align: right middle;
        margin-top: 1;
    }
    """

    def __init__(self, manager: BudgetManager, transaction: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager
        self.transaction = transaction
        self.cards = self.manager.cards
        self.categories = self.manager.categories

    def compose(self) -> ComposeResult:
        with Vertical(id="edit-dialog"):
            yield Label("Edit Transaction", id="title")

            with Horizontal():
                yield Label("Type", classes="label")
                yield Select(
                    [("Card", "card"), ("Cash", "cash")],
                    value=self.transaction["type"],
                    id="type",
                )

            with Horizontal():
                yield Label("Card", classes="label")
                card_value = (
                    self.transaction["card"]
                    if self.transaction["card"]
                    else Select.BLANK
                )
                yield Select(
                    [(c, c) for c in self.cards],
                    value=card_value,
                    allow_blank=True,
                    id="card",
                )

            with Horizontal():
                yield Label("Description", classes="label")
                yield Input(value=self.transaction["description"], id="description")

            with Horizontal():
                yield Label("Amount", classes="label")
                yield Input(value=str(self.transaction["amount"]), id="amount")

            with Horizontal():
                yield Label("Category", classes="label")
                category_value = (
                    self.transaction["category"]
                    if self.transaction["category"]
                    else Select.BLANK
                )
                yield Select(
                    [(c, c) for c in self.categories],
                    value=category_value,
                    allow_blank=True,
                    id="category",
                )

            with Horizontal(id="buttons"):
                yield Button("Update", variant="primary", id="update")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "update":
            self.update_transaction()
        else:
            self.app.pop_screen()

    def update_transaction(self) -> None:
        try:
            type = self.query_one("#type", Select).value
            card = self.query_one("#card", Select).value
            description = self.query_one("#description", Input).value
            amount_str = self.query_one("#amount", Input).value
            category = self.query_one("#category", Select).value

            if not all([type, description, amount_str]):
                self.app.notify(
                    "Type, description, and amount are required.", severity="error"
                )
                return

            try:
                amount = float(amount_str)
            except ValueError:
                self.app.notify("Invalid amount.", severity="error")
                return

            # Convert Select.BLANK to None
            card_value = None if card == Select.BLANK else card
            category_value = None if category == Select.BLANK else category

            self.manager.update_transaction(
                transaction_id=self.transaction["id"],
                t_type=type,
                card=card_value if type == "card" else None,
                description=description,
                amount=amount,
                category=category_value,
            )
            self.app.pop_screen()
            self.app.action_refresh()
            self.app.notify("Transaction updated successfully.", severity="information")
        except Exception as e:
            self.app.notify(f"Error updating transaction: {e}", severity="error")


class BudgetTUI(App):
    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    .body {
        height: 1fr;
        layout: horizontal;
    }

    .left-sidebar {
        width: 32;
        layout: vertical;
        background: $panel;
        border-right: thick $primary;
        padding: 0;
    }

    .main-content {
        width: 1fr;
        layout: vertical;
        padding: 0;
    }

    .balance-panel {
        height: auto;
        padding: 1 2;
        background: $boost;
        border-bottom: solid $primary-darken-2;
        margin-bottom: 1;
    }

    .spending-panel {
        height: auto;
        padding: 1 2;
        background: $boost;
        border-bottom: solid $primary-darken-2;
        margin-bottom: 1;
    }

    .stats-panel {
        height: auto;
        padding: 1 2;
        background: $boost;
    }

    .chart-panel {
        height: 24;
        padding: 1 2;
        background: $panel;
        border: solid $primary-darken-1;
        margin: 1 2 0 2;
    }

    .table-panel {
        height: 1fr;
        padding: 0 2 1 2;
        background: $panel;
    }

    DataTable {
        background: $surface;
        height: 1fr;
    }

    DataTable > .datatable--header {
        background: $primary;
        color: $text;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: $secondary;
    }

    *:focus {
        border: heavy $secondary;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("a", "add_transaction", "Add"),
        ("e", "edit_transaction", "Edit"),
        ("d", "delete_transaction", "Delete"),
        ("?", "show_help", "Help"),
    ]

    def __init__(self, db_path: str = "budget.db") -> None:
        super().__init__()
        self.manager = BudgetManager(db_path)
        self.manager.__enter__()
        self.title = "Budget Tracker"
        self.sub_title = "Personal Finance Manager"

    def on_unmount(self) -> None:
        """Cleanup database connection when app closes."""
        self.manager.__exit__(None, None, None)

    def on_mount(self) -> None:
        """Show welcome message on startup."""
        self.notify("Welcome! Press ? for help, a to add transaction, q to quit", timeout=5)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(classes="body"):
            with Vertical(classes="left-sidebar"):
                balance_panel = BalancePanel(self.manager)
                balance_panel.add_class("balance-panel")
                balance_panel.id = "balances"
                yield balance_panel

                spending_panel = SpendingSummaryPanel(self.manager)
                spending_panel.add_class("spending-panel")
                spending_panel.id = "spending"
                yield spending_panel

                stats_panel = QuickStatsPanel(self.manager)
                stats_panel.add_class("stats-panel")
                stats_panel.id = "stats"
                yield stats_panel
            with Vertical(classes="main-content"):
                daily_chart = DailySpendBars(self.manager, days=30)
                daily_chart.add_class("chart-panel")
                daily_chart.id = "daily"
                yield daily_chart

                recent_table = RecentTransactionsTable(self.manager, limit=30)
                recent_table.add_class("table-panel")
                recent_table.id = "recent"
                yield recent_table
        yield Footer()

    def action_refresh(self) -> None:
        try:
            self.manager.__enter__()
            self.manager.load_cards()

            # Refresh all panels
            self.query_one("#balances", BalancePanel).render_balances()
            self.query_one("#spending", SpendingSummaryPanel).render_summary()
            self.query_one("#stats", QuickStatsPanel).render_stats()
            self.query_one("#daily", DailySpendBars).refresh_data()

            table = self.query_one("#recent", RecentTransactionsTable)
            table.clear()
            table.on_mount()

            self.notify("Data refreshed!", severity="information")
        except Exception as e:
            self.notify(f"Error refreshing: {str(e)}", severity="error")

    def action_show_help(self) -> None:
        """Show help dialog."""
        help_text = """
[bold cyan]Budget Tracker - Keyboard Shortcuts[/bold cyan]

[bold yellow]Navigation:[/bold yellow]
  ↑/↓         Navigate transactions
  PgUp/PgDn   Scroll page
  Home/End    Jump to start/end

[bold yellow]Actions:[/bold yellow]
  a           Add new transaction
  e           Edit selected transaction
  d           Delete selected transaction
  r           Refresh data

[bold yellow]Other:[/bold yellow]
  ?           Show this help
  q           Quit application

[dim]Use arrow keys to navigate the transaction table.
Click on input fields to enter data in forms.[/dim]
"""
        self.notify(help_text, timeout=10)

    def action_add_transaction(self) -> None:
        """Shows the add transaction screen."""
        self.push_screen(AddTransactionScreen(self.manager))

    def action_delete_transaction(self) -> None:
        """Deletes the selected transaction."""
        table = self.query_one("#recent", RecentTransactionsTable)
        if table.cursor_row is not None:
            try:
                row_key = table.get_row_at(table.cursor_row)[0]
                transaction_id = int(row_key)
                self.push_screen(DeleteTransactionScreen(transaction_id))
            except Exception as e:
                self.notify(f"No transaction selected: {e}", severity="error")

    def delete_transaction(self, transaction_id: int) -> None:
        """Deletes a transaction and refreshes the UI."""
        try:
            self.manager.delete_transaction(transaction_id)
            self.action_refresh()
            self.notify(
                f"Transaction {transaction_id} deleted.", severity="information"
            )
        except Exception as e:
            self.notify(f"Error deleting transaction: {e}", severity="error")

    def action_edit_transaction(self) -> None:
        """Edits the selected transaction."""
        table = self.query_one("#recent", RecentTransactionsTable)
        if table.cursor_row is not None:
            try:
                row_key = table.get_row_at(table.cursor_row)[0]
                transaction_id = int(row_key)
                transaction = self.manager.get_transaction_by_id(transaction_id)
                if transaction:
                    self.push_screen(EditTransactionScreen(self.manager, transaction))
                else:
                    self.notify("Transaction not found.", severity="error")
            except Exception as e:
                self.notify(f"No transaction selected: {e}", severity="error")



def run_tui(db_path: str = "budget.db") -> None:
    app = BudgetTUI(db_path)
    app.run()
