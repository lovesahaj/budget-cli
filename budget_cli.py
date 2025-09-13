import sqlite3
import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint

app = typer.Typer(help="Personal Budget Tracker - Track your daily transactions and account balances")
console = Console()

class BudgetManager:
    def __init__(self, db_name: str = 'budget.db'):
        self.db_name = db_name
        self.conn = None
        self.cards = []

    def connect_db(self):
        self.conn = sqlite3.connect(self.db_name)
        cur = self.conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)')
        cur.execute('CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, card TEXT, description TEXT, amount REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
        cur.execute('CREATE TABLE IF NOT EXISTS balances (type TEXT UNIQUE, amount REAL)')
        self.conn.commit()

    def load_cards(self):
        cur = self.conn.cursor()
        # Load existing cards from database
        cur.execute('SELECT name FROM cards ORDER BY name')
        self.cards = [row[0] for row in cur.fetchall()]
        
        # If no cards exist, add some default ones
        if not self.cards:
            default_cards = ['Wise', 'ICICI']
            for card in default_cards:
                cur.execute('INSERT INTO cards (name) VALUES (?)', (card,))
                cur.execute('INSERT INTO balances (type, amount) VALUES (?, ?)', (card, 0.0))
            self.cards = default_cards
        else:
            # Ensure balances exist for all cards
            for card in self.cards:
                cur.execute('INSERT OR IGNORE INTO balances (type, amount) VALUES (?, ?)', (card, 0.0))
        
        # Ensure cash balance exists
        cur.execute('INSERT OR IGNORE INTO balances (type, amount) VALUES (?, ?)', ('cash', 0.0))
        self.conn.commit()

    def get_balance(self, balance_type: str) -> float:
        cur = self.conn.cursor()
        cur.execute('SELECT amount FROM balances WHERE type = ?', (balance_type,))
        res = cur.fetchone()
        return res[0] if res else 0.0

    def update_balance(self, balance_type: str, amount: float):
        cur = self.conn.cursor()
        cur.execute('UPDATE balances SET amount = ? WHERE type = ?', (amount, balance_type))
        self.conn.commit()

    def add_transaction(self, t_type: str, card: Optional[str], description: str, amount: float):
        cur = self.conn.cursor()
        cur.execute('INSERT INTO transactions (type, card, description, amount) VALUES (?, ?, ?, ?)',
                    (t_type, card, description, amount))
        self.conn.commit()

    def add_new_card(self, card_name: str) -> bool:
        """Add a new card to the system"""
        cur = self.conn.cursor()
        try:
            cur.execute('INSERT INTO cards (name) VALUES (?)', (card_name,))
            cur.execute('INSERT INTO balances (type, amount) VALUES (?, ?)', (card_name, 0.0))
            self.conn.commit()
            self.cards.append(card_name)
            self.cards.sort()  # Keep cards sorted
            return True
        except sqlite3.IntegrityError:
            return False

    def get_recent_transactions(self, limit: int = 10) -> List[tuple]:
        """Get recent transactions"""
        cur = self.conn.cursor()
        cur.execute('SELECT type, card, description, amount, timestamp FROM transactions ORDER BY timestamp DESC LIMIT ?', (limit,))
        return cur.fetchall()

    def get_monthly_spending(self, year: int, month: int) -> dict:
        """Get spending breakdown by source for a specific month"""
        cur = self.conn.cursor()
        cur.execute('''
            SELECT type, card, SUM(amount) as total
            FROM transactions 
            WHERE strftime('%Y', timestamp) = ? AND strftime('%m', timestamp) = ?
            AND amount IS NOT NULL
            GROUP BY type, card
            ORDER BY total DESC
        ''', (str(year), f"{month:02d}"))
        
        spending = {}
        for t_type, card, total in cur.fetchall():
            source = card if card else t_type
            spending[source] = total
        
        return spending

    def get_spending_with_balance_percentage(self, year: int, month: int) -> List[tuple]:
        """Get spending breakdown with percentage of current balance spent"""
        spending = self.get_monthly_spending(year, month)
        result = []
        
        for source, amount_spent in spending.items():
            current_balance = self.get_balance(source)
            if current_balance > 0:
                # Calculate what percentage of current balance was spent this month
                balance_percentage = (amount_spent / current_balance) * 100
            else:
                balance_percentage = 0 if amount_spent == 0 else float('inf')
            
            result.append((source, amount_spent, current_balance, balance_percentage))
        
        # Sort by amount spent (descending)
        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def close(self):
        if self.conn:
            self.conn.close()

# Global budget manager instance
budget_manager = BudgetManager()

def _add_funds_interactive():
    """Internal function for interactive fund addition"""
    budget_manager.connect_db()
    budget_manager.load_cards()
    
    rprint("\n[bold blue]=== Adding Funds ===[/bold blue]")
    rprint("Enter amounts to add to your accounts (leave blank for 0):")
    
    cash_input = Prompt.ask("Money added to cash", default="0")
    try:
        cash_val = float(cash_input)
        if cash_val > 0:
            cur_cash = budget_manager.get_balance('cash')
            budget_manager.update_balance('cash', cur_cash + cash_val)
            rprint(f"[green]Added £{cash_val:.2f} to cash. New balance: £{cur_cash + cash_val:.2f}[/green]")
    except ValueError:
        rprint("[red]Invalid amount entered for cash, ignoring[/red]")

    for card_name in budget_manager.cards:
        card_input = Prompt.ask(f"Money added to {card_name}", default="0")
        try:
            card_val = float(card_input)
            if card_val > 0:
                cur_card = budget_manager.get_balance(card_name)
                budget_manager.update_balance(card_name, cur_card + card_val)
                rprint(f"[green]Added £{card_val:.2f} to {card_name}. New balance: £{cur_card + card_val:.2f}[/green]")
        except ValueError:
            rprint(f"[red]Invalid amount entered for {card_name}, ignoring[/red]")

@app.command()
def add_funds(
    cash: Optional[float] = typer.Option(None, "--cash", "-c", help="Amount to add to cash"),
    card: Optional[str] = typer.Option(None, "--card", help="Card name to add funds to"),
    amount: Optional[float] = typer.Option(None, "--amount", "-a", help="Amount to add to the specified card")
):
    """Add funds to your accounts"""
    budget_manager.connect_db()
    budget_manager.load_cards()
    
    if cash is not None:
        if cash < 0:
            rprint("[red]Warning: Negative amount entered for cash, ignoring[/red]")
        else:
            cur_cash = budget_manager.get_balance('cash')
            budget_manager.update_balance('cash', cur_cash + cash)
            rprint(f"[green]Added £{cash:.2f} to cash. New balance: £{cur_cash + cash:.2f}[/green]")
    
    if card and amount is not None:
        if card not in budget_manager.cards:
            rprint(f"[red]Card '{card}' not found. Available cards: {', '.join(budget_manager.cards)}[/red]")
            return
        
        if amount < 0:
            rprint(f"[red]Warning: Negative amount entered for {card}, ignoring[/red]")
        else:
            cur_card = budget_manager.get_balance(card)
            budget_manager.update_balance(card, cur_card + amount)
            rprint(f"[green]Added £{amount:.2f} to {card}. New balance: £{cur_card + amount:.2f}[/green]")
    
    if cash is None and (card is None or amount is None):
        # Interactive mode
        _add_funds_interactive()

@app.command()
def add_transaction(
    type: str = typer.Argument(..., help="Transaction type: cash or card"),
    description: str = typer.Argument(..., help="Description of the transaction"),
    amount: float = typer.Argument(..., help="Amount of the transaction"),
    card: Optional[str] = typer.Option(None, "--card", "-c", help="Card name (required if type is 'card')")
):
    """Add a new transaction"""
    budget_manager.connect_db()
    budget_manager.load_cards()
    
    if type not in ['cash', 'card']:
        rprint("[red]Invalid transaction type. Please use 'cash' or 'card'[/red]")
        raise typer.Exit(1)
    
    if type == 'card' and not card:
        rprint("[red]Card name is required when transaction type is 'card'[/red]")
        rprint(f"Available cards: {', '.join(budget_manager.cards)}")
        raise typer.Exit(1)
    
    if type == 'card' and card not in budget_manager.cards:
        rprint(f"[red]Card '{card}' not found. Available cards: {', '.join(budget_manager.cards)}[/red]")
        raise typer.Exit(1)
    
    if amount <= 0:
        rprint("[red]Amount must be positive[/red]")
        raise typer.Exit(1)
    
    # Process the transaction
    if type == 'cash':
        current_cash = budget_manager.get_balance('cash')
        new_cash = current_cash - amount
        if new_cash < 0:
            rprint(f"[yellow]Warning: Cash balance will go negative (£{new_cash:.2f})[/yellow]")
            if not Confirm.ask("Continue anyway?"):
                rprint("[red]Transaction cancelled[/red]")
                raise typer.Exit(0)
        budget_manager.update_balance('cash', new_cash)
        rprint(f"[green]Transaction recorded. Cash balance: £{new_cash:.2f}[/green]")
    else:
        current_card = budget_manager.get_balance(card)
        new_card = current_card - amount
        if new_card < 0:
            rprint(f"[yellow]Warning: {card} balance will go negative (£{new_card:.2f})[/yellow]")
            if not Confirm.ask("Continue anyway?"):
                rprint("[red]Transaction cancelled[/red]")
                raise typer.Exit(0)
        budget_manager.update_balance(card, new_card)
        rprint(f"[green]Transaction recorded. {card} balance: £{new_card:.2f}[/green]")
    
    budget_manager.add_transaction(type, card, description, amount)

@app.command()
def add_card(name: str = typer.Argument(..., help="Name of the new card")):
    """Add a new payment card"""
    budget_manager.connect_db()
    budget_manager.load_cards()
    
    if budget_manager.add_new_card(name):
        rprint(f"[green]Added new card: {name}[/green]")
    else:
        rprint(f"[red]Card '{name}' already exists[/red]")
        raise typer.Exit(1)

@app.command()
def balance():
    """Show current account balances"""
    budget_manager.connect_db()
    budget_manager.load_cards()
    
    table = Table(title="Account Balances")
    table.add_column("Account", style="cyan", no_wrap=True)
    table.add_column("Balance", justify="right", style="green")
    
    cash_balance = budget_manager.get_balance('cash')
    table.add_row("Cash", f"£{cash_balance:.2f}")
    
    for card in budget_manager.cards:
        card_balance = budget_manager.get_balance(card)
        table.add_row(card, f"£{card_balance:.2f}")
    
    console.print(table)

@app.command()
def list_transactions(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of recent transactions to show")
):
    """Show recent transactions"""
    budget_manager.connect_db()
    budget_manager.load_cards()
    
    transactions = budget_manager.get_recent_transactions(limit)
    
    if not transactions:
        rprint("[yellow]No transactions found[/yellow]")
        return
    
    table = Table(title=f"Recent Transactions (Last {len(transactions)})")
    table.add_column("Type", style="cyan")
    table.add_column("Card", style="blue")
    table.add_column("Description", style="white")
    table.add_column("Amount", justify="right", style="red")
    table.add_column("Date", style="dim")
    
    for t_type, card, description, amount, timestamp in transactions:
        card_display = card if card else "N/A"
        amount_display = f"£{amount:.2f}" if amount is not None else "N/A"
        table.add_row(t_type, card_display, description, amount_display, timestamp)
    
    console.print(table)

@app.command()
def monthly_spending(
    year: int = typer.Option(None, "--year", "-y", help="Year (defaults to current year)"),
    month: int = typer.Option(None, "--month", "-m", help="Month (1-12, defaults to current month)")
):
    """Show monthly spending breakdown by source (cash/cards)"""
    from datetime import datetime
    
    # Use current date if not specified
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    if not (1 <= month <= 12):
        rprint("[red]Month must be between 1 and 12[/red]")
        raise typer.Exit(1)
    
    budget_manager.connect_db()
    budget_manager.load_cards()
    
    spending_data = budget_manager.get_spending_with_balance_percentage(year, month)
    
    if not spending_data:
        rprint(f"[yellow]No transactions found for {year}-{month:02d}[/yellow]")
        return
    
    # Create month name
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month_name = month_names[month - 1]
    
    table = Table(title=f"Monthly Spending - {month_name} {year}")
    table.add_column("Source", style="cyan", no_wrap=True)
    table.add_column("Amount Spent", justify="right", style="red")
    table.add_column("Current Balance", justify="right", style="green")
    table.add_column("% of Balance Spent", justify="right", style="blue")
    
    total_spent = sum(amount for _, amount, _, _ in spending_data)
    total_balance = sum(balance for _, _, balance, _ in spending_data)
    
    for source, amount_spent, current_balance, balance_percentage in spending_data:
        if balance_percentage == float('inf'):
            percentage_display = "∞%"
        else:
            percentage_display = f"{balance_percentage:.1f}%"
        
        table.add_row(
            source, 
            f"£{amount_spent:.2f}", 
            f"£{current_balance:.2f}",
            percentage_display
        )
    
    # Add total row
    table.add_section()
    total_percentage = (total_spent / total_balance * 100) if total_balance > 0 else 0
    table.add_row(
        "[bold]Total[/bold]", 
        f"[bold]£{total_spent:.2f}[/bold]", 
        f"[bold]£{total_balance:.2f}[/bold]",
        f"[bold]{total_percentage:.1f}%[/bold]"
    )
    
    console.print(table)

@app.command()
def interactive():
    """Start interactive mode for adding multiple transactions"""
    budget_manager.connect_db()
    budget_manager.load_cards()
    
    rprint("\n[bold blue]=== Personal Budget Tracker - Interactive Mode ===[/bold blue]")
    rprint("Welcome to your personal budget tracking application!")
    rprint("This app will help you track your daily transactions and account balances.\n")
    
    # Add funds first
    _add_funds_interactive()
    
    try:
        while True:
            rprint("\n[bold]New transaction entry (or type 'exit' to finish):[/bold]")
            ttype = Prompt.ask("Transaction type", choices=["cash", "card", "exit"], default="cash")
            
            if ttype == 'exit':
                break
            
            card = None
            if ttype == 'card':
                rprint(f"Available cards: {', '.join(budget_manager.cards)}")
                card_choice = Prompt.ask("Which card did you use? (or type 'new' to add a card)")
                
                if card_choice.lower() == 'new':
                    new_card_name = Prompt.ask("Enter the name of the new card")
                    if new_card_name:
                        if budget_manager.add_new_card(new_card_name):
                            card = new_card_name
                        else:
                            rprint(f"[red]Card '{new_card_name}' already exists[/red]")
                            continue
                    else:
                        rprint("[red]Card name cannot be empty[/red]")
                        continue
                elif card_choice not in budget_manager.cards:
                    rprint(f"[red]Invalid card name. Available cards: {', '.join(budget_manager.cards)}[/red]")
                    continue
                else:
                    card = card_choice
            
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
            if ttype == 'cash':
                current_cash = budget_manager.get_balance('cash')
                new_cash = current_cash - amount
                if new_cash < 0:
                    rprint(f"[yellow]Warning: Cash balance will go negative (£{new_cash:.2f})[/yellow]")
                    if not Confirm.ask("Continue anyway?"):
                        continue
                budget_manager.update_balance('cash', new_cash)
                rprint(f"[green]Transaction recorded. Cash balance: £{new_cash:.2f}[/green]")
            else:
                current_card = budget_manager.get_balance(card)
                new_card = current_card - amount
                if new_card < 0:
                    rprint(f"[yellow]Warning: {card} balance will go negative (£{new_card:.2f})[/yellow]")
                    if not Confirm.ask("Continue anyway?"):
                        continue
                budget_manager.update_balance(card, new_card)
                rprint(f"[green]Transaction recorded. {card} balance: £{new_card:.2f}[/green]")
            
            budget_manager.add_transaction(ttype, card, description, amount)
    
    finally:
        rprint("\n[bold blue]=== Final Account Balances ===[/bold blue]")
        balance()
        rprint("\n[green]Thank you for using the Budget Tracker![/green]")
        budget_manager.close()

@app.callback()
def main():
    """Personal Budget Tracker - Track your daily transactions and account balances"""
    pass

if __name__ == "__main__":
    app()