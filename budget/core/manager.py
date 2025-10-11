"""Core budget management module.

This module provides the main BudgetManager class, which serves as the
primary facade for all budget operations. It coordinates all specialized
managers and handles database session management via context manager protocol.
"""

import os
from typing import Dict, List, Optional, Tuple

from loguru import logger

from budget.core.balances import BalanceManager
from budget.core.cards import CardManager
from budget.core.categories import CategoryManager
from budget.core.exports import ExportManager
from budget.core.limits import LimitManager
from budget.core.reports import ReportManager
from budget.core.transactions import TransactionManager
from budget.infrastructure import database


class BudgetManager:
    """Main facade for budget tracking operations.

    BudgetManager is the primary entry point for all budget operations. It
    implements the Facade pattern, providing a unified interface to all
    subsystems (transactions, cards, categories, balances, limits, reports,
    and exports). It also implements the Context Manager protocol for proper
    database session management.

    The manager should be used as a context manager to ensure proper database
    session handling with automatic commit/rollback.

    Attributes:
        db_name (str): Name of the database file.
        engine: SQLAlchemy engine instance.
        cards (List[str]): List of available card names.
        categories (List[str]): List of available category names.
        transactions (TransactionManager): Transaction operations manager.
        card_manager (CardManager): Card operations manager.
        categories_manager (CategoryManager): Category operations manager.
        balances_manager (BalanceManager): Balance operations manager.
        limits_manager (LimitManager): Spending limit operations manager.
        reports_manager (ReportManager): Reporting and analytics manager.
        export_manager (ExportManager): Data export manager.

    Example:
        >>> # Using as context manager (recommended)
        >>> with BudgetManager() as bm:
        ...     bm.add_transaction("card", "Visa", "Coffee", 5.0, "Food")
        ...     recent = bm.get_recent_transactions(10)
        ...     balances = bm.get_all_balances()
        ...
        >>> # Custom database name
        >>> with BudgetManager("my_budget.db") as bm:
        ...     bm.add_category("Entertainment", "Movies, games, etc")
    """

    def __init__(self, db_name: str = "budget.db"):
        """Initialize the BudgetManager.

        Args:
            db_name: Name of the SQLite database file. Defaults to "budget.db".
                    Can be overridden by BUDGET_DB_NAME environment variable.
        """
        self.db_name = os.environ.get("BUDGET_DB_NAME", db_name)
        logger.debug(f"Initializing BudgetManager with database: {self.db_name}")
        self.engine = database.get_engine(self.db_name)
        # Note: init_db is called during server startup, no need to call it here
        # database.init_db(self.engine)
        self.cards = []
        self.categories = []
        self.transactions: Optional[TransactionManager] = None
        self.card_manager: Optional[CardManager] = None
        self.categories_manager: Optional[CategoryManager] = None
        self.balances_manager: Optional[BalanceManager] = None
        self.limits_manager: Optional[LimitManager] = None
        self.reports_manager: Optional[ReportManager] = None
        self.export_manager: Optional[ExportManager] = None

    def load_cards(self):
        """Load cards from database and ensure default setup.

        Delegates to the CardManager to load all payment cards from the
        database and initialize default cards if none exist.
        """
        if self.card_manager is not None:
            self.cards = self.card_manager.load_cards()

    def get_daily_spending(self, days: int = 30) -> List[Tuple[str, float]]:
        """Return list of (YYYY-MM-DD, total_spent) for the last `days` days"""
        assert self.reports_manager is not None
        return self.reports_manager.get_daily_spending(days)

    def get_all_balances(self) -> Dict[str, float]:
        """Return mapping of balance type to current amount"""
        assert self.balances_manager is not None
        return self.balances_manager.get_all_balances()

    # Card management delegation
    def add_new_card(self, name: str) -> bool:
        """Add a new payment card"""
        assert self.card_manager is not None
        result = self.card_manager.add_new_card(name)
        if result:
            self.cards = self.card_manager.cards
        return result

    # Category management delegation
    def add_category(self, name: str, description: str = "") -> bool:
        """Add a new transaction category"""
        assert self.categories_manager is not None
        result = self.categories_manager.add_category(name, description)
        if result:
            self.categories = self.categories_manager.categories
        return result

    def get_categories(self):
        """Get all categories with descriptions"""
        assert self.categories_manager is not None
        return self.categories_manager.get_categories()

    # Balance management delegation
    def get_balance(self, balance_type: str) -> float:
        """Get current balance for a given type"""
        assert self.balances_manager is not None
        return self.balances_manager.get_balance(balance_type)

    def update_balance(self, balance_type: str, amount: float):
        """Update balance for a given type"""
        assert self.balances_manager is not None
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
        assert self.transactions is not None
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
        assert self.transactions is not None
        return self.transactions.update_transaction(
            transaction_id, t_type, card, description, amount, category
        )

    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction by ID"""
        assert self.transactions is not None
        return self.transactions.delete_transaction(transaction_id)

    def get_transaction_by_id(self, transaction_id: int):
        """Get a single transaction by ID"""
        assert self.transactions is not None
        return self.transactions.get_transaction_by_id(transaction_id)

    def get_recent_transactions(self, limit: int = 10):
        """Get recent transactions"""
        assert self.transactions is not None
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
        assert self.transactions is not None
        return self.transactions.search_transactions(
            query, category, card, start_date, end_date, min_amount, max_amount
        )

    # Reports delegation
    def get_spending_by_category(self, year: int, month: int):
        """Get spending breakdown by category for a specific month"""
        assert self.reports_manager is not None
        return self.reports_manager.get_spending_by_category(year, month)

    def get_spending_with_balance_percentage(self, year: int, month: int):
        """Get spending breakdown with percentage of current balance spent"""
        assert self.reports_manager is not None
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
        assert self.limits_manager is not None
        return self.limits_manager.set_spending_limit(
            limit_amount, period, category, source
        )

    def get_spending_limits(self):
        """Get all spending limits"""
        assert self.limits_manager is not None
        return self.limits_manager.get_spending_limits()

    def check_spending_limit(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        period: str = "monthly",
    ):
        """Check if spending limit is exceeded"""
        assert self.limits_manager is not None
        return self.limits_manager.check_spending_limit(category, source, period)

    # Export delegation
    def export_to_csv(
        self,
        filepath: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """Export transactions to CSV file"""
        assert self.export_manager is not None
        return self.export_manager.export_to_csv(filepath, start_date, end_date)

    def export_to_json(
        self,
        filepath: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """Export transactions to JSON file"""
        assert self.export_manager is not None
        return self.export_manager.export_to_json(filepath, start_date, end_date)

    def __enter__(self):
        """Enter the context manager and initialize database session.

        Creates a new database session and initializes all manager instances.
        This method is called automatically when entering a 'with' block.

        Returns:
            BudgetManager: Returns self for use in the 'with' statement.

        Example:
            >>> with BudgetManager() as bm:
            ...     # bm is now ready to use with active session
            ...     bm.add_transaction("card", "Visa", "Coffee", 5.0)
        """
        logger.debug("Entering BudgetManager context")
        # Use the scoped session factory for better thread safety
        SessionFactory = database.get_session_factory(self.engine)
        self.session = SessionFactory()

        logger.debug("Initializing all manager instances")
        self.transactions = TransactionManager(self.session)
        self.card_manager = CardManager(self.session)
        self.categories_manager = CategoryManager(self.session)
        self.balances_manager = BalanceManager(self.session)
        self.limits_manager = LimitManager(self.session)
        self.reports_manager = ReportManager(self.session, self.balances_manager)
        self.export_manager = ExportManager(self.transactions)
        self.load_cards()
        self.categories = self.categories_manager.load_categories()
        logger.info("BudgetManager context initialized successfully")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: ARG002
        """Exit the context manager and handle session cleanup.

        Commits the database session if no exceptions occurred, otherwise
        rolls back. The session is always closed.

        Args:
            exc_type: Exception type if an exception occurred, None otherwise.
            exc_val: Exception value if an exception occurred, None otherwise.
            exc_tb: Exception traceback if an exception occurred, None otherwise.

        Example:
            >>> with BudgetManager() as bm:
            ...     bm.add_transaction("card", "Visa", "Coffee", 5.0)
            ...     # Session automatically committed here if no errors
            ...
            >>> # If an exception occurs, session is rolled back
            >>> with BudgetManager() as bm:
            ...     bm.add_transaction("invalid", None, "", -5.0)
            ...     # ValidationError raised, session rolled back
        """
        logger.debug("Exiting BudgetManager context")
        if hasattr(self, "session") and self.session:
            if exc_type is None:
                logger.debug("Committing session")
                self.session.commit()
            else:
                logger.warning(f"Rolling back session due to exception: {exc_type.__name__}")
                self.session.rollback()
            # For scoped sessions, we should use remove() instead of close()
            SessionFactory = database.get_session_factory(self.engine)
            SessionFactory.remove()
        logger.info("BudgetManager context closed")
