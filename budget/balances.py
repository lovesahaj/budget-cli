"""Account balance management module.

This module provides functionality for tracking and managing account balances
for different payment sources (cash and various cards).
"""

from typing import Dict
from sqlalchemy.orm import Session

from budget.exceptions import DatabaseError, ValidationError
from budget.models import Balance

class BalanceManager:
    """Manages account balances for different payment sources.

    The BalanceManager handles all operations related to tracking balances
    for cash and card accounts, including retrieval and updates.

    Attributes:
        session (Session): SQLAlchemy database session.

    Example:
        >>> with BudgetManager() as bm:
        ...     balance_mgr = BalanceManager(bm.session)
        ...     cash = balance_mgr.get_balance("cash")
        ...     balance_mgr.update_balance("cash", 1000.0)
    """

    def __init__(self, session: Session):
        """Initialize the BalanceManager.

        Args:
            session: SQLAlchemy database session for database operations.
        """
        self.session = session

    def get_balance(self, balance_type: str) -> float:
        """Get current balance for a specific account type.

        Args:
            balance_type: Type of balance to retrieve (e.g., "cash" or card name).

        Returns:
            float: Current balance amount, or 0.0 if no balance record exists.

        Raises:
            DatabaseError: If retrieving the balance fails.

        Example:
            >>> cash_balance = balance_mgr.get_balance("cash")
            >>> card_balance = balance_mgr.get_balance("Visa")
        """
        try:
            balance = self.session.query(Balance).filter_by(type=balance_type).first()
            return float(balance.amount) if balance else 0.0
        except Exception as e:
            raise DatabaseError(f"Failed to get balance: {e}")

    def update_balance(self, balance_type: str, amount: float):
        """Update the balance for a specific account type.

        Sets the balance to the specified amount. If no balance record exists
        for the given type, a new one is created.

        Args:
            balance_type: Type of balance to update (e.g., "cash" or card name).
            amount: New balance amount to set.

        Raises:
            ValidationError: If amount is not a number.
            DatabaseError: If updating the balance fails.

        Example:
            >>> balance_mgr.update_balance("cash", 500.0)
            >>> balance_mgr.update_balance("Visa", 2000.0)
        """
        try:
            if not isinstance(amount, (int, float)):
                raise ValidationError("Amount must be a number")

            balance = self.session.query(Balance).filter_by(type=balance_type).first()
            if balance:
                balance.amount = float(amount)
            else:
                balance = Balance(type=balance_type, amount=float(amount))
                self.session.add(balance)
            self.session.commit()
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to update balance: {e}")

    def get_all_balances(self) -> Dict[str, float]:
        """Get all balances across all account types.

        Returns:
            Dict[str, float]: Dictionary mapping balance type names to their
                             current amounts, sorted by type name.

        Raises:
            DatabaseError: If retrieving balances fails.

        Example:
            >>> balances = balance_mgr.get_all_balances()
            >>> print(balances)  # {'cash': 500.0, 'ICICI': 1000.0, 'Visa': 2000.0}
        """
        try:
            balances = self.session.query(Balance).order_by(Balance.type).all()
            return {b.type: float(b.amount) for b in balances}
        except Exception as e:
            raise DatabaseError(f"Failed to get all balances: {e}")