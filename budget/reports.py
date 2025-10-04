"""Budget reporting and analytics module.

This module provides functionality for generating various financial reports
and analytics, including spending breakdowns, trends, and balance analysis.
"""

from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta

from budget.exceptions import DatabaseError
from budget.models import Transaction

class ReportManager:
    """Manages financial reports and analytics.

    The ReportManager provides various reporting capabilities including
    spending breakdowns by source, category, time period, and balance
    percentage analysis.

    Attributes:
        session (Session): SQLAlchemy database session.
        balance_manager: BalanceManager instance for balance information.

    Example:
        >>> with BudgetManager() as bm:
        ...     report_mgr = ReportManager(bm.session, bm.balances_manager)
        ...     # Get monthly spending by category
        ...     spending = report_mgr.get_spending_by_category(2025, 10)
    """

    def __init__(self, session: Session, balance_manager):
        """Initialize the ReportManager.

        Args:
            session: SQLAlchemy database session for database operations.
            balance_manager: BalanceManager instance for retrieving balances.
        """
        self.session = session
        self.balance_manager = balance_manager

    def get_monthly_spending(self, year: int, month: int) -> dict:
        """Get spending breakdown by payment source for a specific month.

        Args:
            year: Year to query (e.g., 2025).
            month: Month to query (1-12).

        Returns:
            dict: Dictionary mapping source names to total spending amounts,
                 ordered by amount (highest first).

        Raises:
            DatabaseError: If retrieving spending data fails.

        Example:
            >>> spending = report_mgr.get_monthly_spending(2025, 10)
            >>> for source, amount in spending.items():
            ...     print(f"{source}: ${amount:.2f}")
        """
        try:
            spending = {}
            results = (
                self.session.query(
                    Transaction.type,
                    Transaction.card,
                    func.sum(Transaction.amount).label("total"),
                )
                .filter(
                    extract("year", Transaction.timestamp) == year,
                    extract("month", Transaction.timestamp) == month,
                    Transaction.amount.isnot(None),
                )
                .group_by(Transaction.type, Transaction.card)
                .order_by(func.sum(Transaction.amount).desc())
                .all()
            )

            for row in results:
                source = row.card if row.card else row.type
                spending[source] = float(row.total)

            return spending
        except Exception as e:
            raise DatabaseError(f"Failed to get monthly spending: {e}")

    def get_spending_by_category(
        self, year: int, month: int
    ) -> List[Tuple[str, float]]:
        """Get spending breakdown by category for a specific month.

        Args:
            year: Year to query (e.g., 2025).
            month: Month to query (1-12).

        Returns:
            List[Tuple[str, float]]: List of (category_name, total_amount)
                                     tuples, ordered by amount (highest first).
                                     Uncategorized transactions are labeled
                                     as "Uncategorized".

        Raises:
            DatabaseError: If retrieving spending data fails.

        Example:
            >>> spending = report_mgr.get_spending_by_category(2025, 10)
            >>> for category, amount in spending:
            ...     print(f"{category}: ${amount:.2f}")
        """
        try:
            results = (
                self.session.query(
                    Transaction.category,
                    func.sum(Transaction.amount).label("total"),
                )
                .filter(
                    extract("year", Transaction.timestamp) == year,
                    extract("month", Transaction.timestamp) == month,
                    Transaction.amount.isnot(None),
                )
                .group_by(Transaction.category)
                .order_by(func.sum(Transaction.amount).desc())
                .all()
            )

            return [(row.category or "Uncategorized", float(row.total)) for row in results]
        except Exception as e:
            raise DatabaseError(f"Failed to get spending by category: {e}")

    def get_spending_with_balance_percentage(
        self, year: int, month: int
    ) -> List[tuple]:
        """Get spending breakdown with percentage of current balance analysis.

        Combines monthly spending data with current balance information to
        show how much of each source's balance was spent in the month.

        Args:
            year: Year to query (e.g., 2025).
            month: Month to query (1-12).

        Returns:
            List[tuple]: List of tuples, each containing:
                        (source_name, amount_spent, current_balance, percentage)
                        Ordered by amount spent (highest first).

        Example:
            >>> data = report_mgr.get_spending_with_balance_percentage(2025, 10)
            >>> for source, spent, balance, pct in data:
            ...     print(f"{source}: ${spent:.2f} / ${balance:.2f} ({pct:.1f}%)")
        """
        spending = self.get_monthly_spending(year, month)
        result = []

        for source, amount_spent in spending.items():
            current_balance = self.balance_manager.get_balance(source)
            if current_balance > 0:
                balance_percentage = (amount_spent / current_balance) * 100
            else:
                balance_percentage = 0 if amount_spent == 0 else float("inf")

            result.append((source, amount_spent, current_balance, balance_percentage))

        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def get_daily_spending(self, days: int = 30) -> List[Tuple[str, float]]:
        """Get daily spending totals for a specified number of recent days.

        Args:
            days: Number of days to include (counting back from today).
                 Defaults to 30.

        Returns:
            List[Tuple[str, float]]: List of (date_string, total_spent) tuples
                                    where date_string is in YYYY-MM-DD format.
                                    Days with no spending show 0.0.
                                    Ordered chronologically.

        Raises:
            DatabaseError: If retrieving spending data fails.

        Example:
            >>> daily = report_mgr.get_daily_spending(days=7)
            >>> for date, amount in daily:
            ...     print(f"{date}: ${amount:.2f}")
        """
        try:
            today = datetime.utcnow().date()
            date_list = [today - timedelta(days=x) for x in range(days)]

            results = (
                self.session.query(
                    func.date(Transaction.timestamp).label("day"),
                    func.sum(Transaction.amount).label("total"),
                )
                .filter(func.date(Transaction.timestamp).in_([d.strftime("%Y-%m-%d") for d in date_list]))
                .group_by(func.date(Transaction.timestamp))
                .all()
            )

            spending_map = {row.day: float(row.total) for row in results}

            return [(d.strftime("%Y-%m-%d"), spending_map.get(d.strftime("%Y-%m-%d"), 0.0)) for d in sorted(date_list)]
        except Exception as e:
            raise DatabaseError(f"Failed to get daily spending: {e}")