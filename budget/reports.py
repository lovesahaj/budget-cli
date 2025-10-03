from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta

from budget.exceptions import DatabaseError
from budget.models import Transaction

class ReportManager:
    def __init__(self, session: Session, balance_manager):
        self.session = session
        self.balance_manager = balance_manager

    def get_monthly_spending(self, year: int, month: int) -> dict:
        """Get spending breakdown by source for a specific month"""
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
        """Get spending breakdown by category for a specific month"""
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
        """Get spending breakdown with percentage of current balance spent"""
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
        """Return list of (YYYY-MM-DD, total_spent) for the last `days` days"""
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