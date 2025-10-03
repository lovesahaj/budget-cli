import os
from typing import Dict, List, Optional, Tuple

from budget import database
from budget.balances import BalanceManager
from budget.cards import CardManager
from budget.categories import CategoryManager
from budget.exports import ExportManager
from budget.limits import LimitManager
from budget.reports import ReportManager
from budget.transactions import TransactionManager


class BudgetManager:
    """Manages budget tracking with support for transactions, categories, and spending limits"""

    def __init__(self, db_name: str = "budget.db"):
        self.db_name = os.environ.get("BUDGET_DB_NAME", db_name)
        self.engine = database.get_engine(self.db_name)
        database.init_db(self.engine)
        self.cards = []
        self.categories = []
        self.transactions = None
        self.card_manager = None
        self.categories_manager = None
        self.balances_manager = None
        self.limits_manager = None
        self.reports_manager = None
        self.export_manager = None

    def load_cards(self):
        """Load cards from database and ensure default setup"""
        self.cards = self.card_manager.load_cards()

    def get_daily_spending(self, days: int = 30) -> List[Tuple[str, float]]:
        """Return list of (YYYY-MM-DD, total_spent) for the last `days` days"""
        return self.reports_manager.get_daily_spending(days)

    def get_all_balances(self) -> Dict[str, float]:
        """Return mapping of balance type to current amount"""
        return self.balances_manager.get_all_balances()

    # Card management delegation
    def add_new_card(self, name: str) -> bool:
        """Add a new payment card"""
        result = self.card_manager.add_new_card(name)
        if result:
            self.cards = self.card_manager.cards
        return result

    # Category management delegation
    def add_category(self, name: str, description: str = "") -> bool:
        """Add a new transaction category"""
        result = self.categories_manager.add_category(name, description)
        if result:
            self.categories = self.categories_manager.categories
        return result

    def get_categories(self):
        """Get all categories with descriptions"""
        return self.categories_manager.get_categories()

    # Balance management delegation
    def get_balance(self, balance_type: str) -> float:
        """Get current balance for a given type"""
        return self.balances_manager.get_balance(balance_type)

    def update_balance(self, balance_type: str, amount: float):
        """Update balance for a given type"""
        return self.balances_manager.update_balance(balance_type, amount)

    # Transaction management delegation
    def add_transaction(
        self,
        t_type: str,
        card: Optional[str],
        description: str,
        amount: float,
        category: Optional[str] = None,
    ):
        """Add a new transaction"""
        return self.transactions.add_transaction(
            t_type, card, description, amount, category
        )

    def update_transaction(
        self,
        transaction_id: int,
        t_type: Optional[str] = None,
        card: Optional[str] = None,
        description: Optional[str] = None,
        amount: Optional[float] = None,
        category: Optional[str] = None,
    ) -> bool:
        """Update an existing transaction"""
        return self.transactions.update_transaction(
            transaction_id, t_type, card, description, amount, category
        )

    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction by ID"""
        return self.transactions.delete_transaction(transaction_id)

    def get_transaction_by_id(self, transaction_id: int):
        """Get a single transaction by ID"""
        return self.transactions.get_transaction_by_id(transaction_id)

    def get_recent_transactions(self, limit: int = 10):
        """Get recent transactions"""
        return self.transactions.get_recent_transactions(limit)

    def search_transactions(
        self,
        query: str = "",
        category: Optional[str] = None,
        card: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
    ):
        """Search and filter transactions"""
        return self.transactions.search_transactions(
            query, category, card, start_date, end_date, min_amount, max_amount
        )

    # Reports delegation
    def get_spending_by_category(self, year: int, month: int):
        """Get spending breakdown by category for a specific month"""
        return self.reports_manager.get_spending_by_category(year, month)

    def get_spending_with_balance_percentage(self, year: int, month: int):
        """Get spending breakdown with percentage of current balance spent"""
        return self.reports_manager.get_spending_with_balance_percentage(year, month)

    # Spending limits delegation
    def set_spending_limit(
        self,
        limit_amount: float,
        period: str = "monthly",
        category: Optional[str] = None,
        source: Optional[str] = None,
    ) -> bool:
        """Set a spending limit"""
        return self.limits_manager.set_spending_limit(
            limit_amount, period, category, source
        )

    def get_spending_limits(self):
        """Get all spending limits"""
        return self.limits_manager.get_spending_limits()

    def check_spending_limit(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        period: str = "monthly",
    ):
        """Check if spending limit is exceeded"""
        return self.limits_manager.check_spending_limit(category, source, period)

    # Export delegation
    def export_to_csv(
        self,
        filepath: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """Export transactions to CSV file"""
        return self.export_manager.export_to_csv(filepath, start_date, end_date)

    def export_to_json(
        self,
        filepath: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """Export transactions to JSON file"""
        return self.export_manager.export_to_json(filepath, start_date, end_date)

    def __enter__(self):
        """Context manager entry"""
        # Create a session using the sessionmaker
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.transactions = TransactionManager(self.session)
        self.card_manager = CardManager(self.session)
        self.categories_manager = CategoryManager(self.session)
        self.balances_manager = BalanceManager(self.session)
        self.limits_manager = LimitManager(self.session)
        self.reports_manager = ReportManager(self.session, self.balances_manager)
        self.export_manager = ExportManager(self.transactions)
        self.load_cards()
        self.categories = self.categories_manager.load_categories()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if hasattr(self, 'session') and self.session:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
            self.session.close()
