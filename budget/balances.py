from typing import Dict
from sqlalchemy.orm import Session

from budget.exceptions import DatabaseError, ValidationError
from budget.models import Balance

class BalanceManager:
    def __init__(self, session: Session):
        self.session = session

    def get_balance(self, balance_type: str) -> float:
        """Get current balance for a given type (cash or card name)"""
        try:
            balance = self.session.query(Balance).filter_by(type=balance_type).first()
            return float(balance.amount) if balance else 0.0
        except Exception as e:
            raise DatabaseError(f"Failed to get balance: {e}")

    def update_balance(self, balance_type: str, amount: float):
        """Update balance for a given type"""
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
        """Return mapping of balance type to current amount"""
        try:
            balances = self.session.query(Balance).order_by(Balance.type).all()
            return {b.type: float(b.amount) for b in balances}
        except Exception as e:
            raise DatabaseError(f"Failed to get all balances: {e}")