from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from budget.exceptions import DatabaseError, ValidationError
from budget.models import Transaction

class TransactionManager:
    def __init__(self, session: Session):
        self.session = session

    def add_transaction(
        self,
        t_type: str,
        card: Optional[str],
        description: str,
        amount: float,
        category: Optional[str] = None,
    ):
        """Add a new transaction"""
        try:
            if not description or not description.strip():
                raise ValidationError("Description cannot be empty")
            if amount <= 0:
                raise ValidationError("Amount must be positive")
            if t_type not in ["cash", "card"]:
                raise ValidationError("Transaction type must be 'cash' or 'card'")

            new_transaction = Transaction(
                type=t_type,
                card=card,
                category=category,
                description=description.strip(),
                amount=float(amount),
            )
            self.session.add(new_transaction)
            self.session.commit()
            return new_transaction.id
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to add transaction: {e}")

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
        try:
            transaction = self.session.query(Transaction).filter_by(id=transaction_id).first()

            if not transaction:
                return False

            updated = False

            if t_type is not None and t_type.strip():
                if t_type not in ["cash", "card"]:
                    raise ValidationError("Transaction type must be 'cash' or 'card'")
                transaction.type = t_type.strip()
                if t_type.strip() == "cash":
                    transaction.card = None
                updated = True

            if card is not None and transaction.type != 'cash':
                transaction.card = card
                updated = True

            if description is not None and description.strip():
                transaction.description = description.strip()
                updated = True

            if amount is not None:
                if amount <= 0:
                    raise ValidationError("Amount must be positive")
                transaction.amount = float(amount)
                updated = True

            if category is not None:
                transaction.category = category
                updated = True

            if updated:
                self.session.commit()
            return updated
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to edit transaction: {e}")

    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction by ID"""
        try:
            transaction = self.session.query(Transaction).filter_by(id=transaction_id).first()
            if transaction:
                self.session.delete(transaction)
                self.session.commit()
                return True
            return False
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to delete transaction: {e}")

    def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Get a single transaction by ID"""
        try:
            return self.session.query(Transaction).filter_by(id=transaction_id).first()
        except Exception as e:
            raise DatabaseError(f"Failed to get transaction: {e}")

    def get_recent_transactions(self, limit: int = 10) -> List[Transaction]:
        """Get recent transactions"""
        try:
            return self.session.query(Transaction).order_by(desc(Transaction.timestamp), desc(Transaction.id)).limit(limit).all()
        except Exception as e:
            raise DatabaseError(f"Failed to get recent transactions: {e}")

    def search_transactions(
        self,
        query: str = "",
        category: Optional[str] = None,
        card: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
    ) -> List[Transaction]:
        """Search and filter transactions"""
        try:
            q = self.session.query(Transaction)

            if query:
                search_term = f"%{query}%"
                q = q.filter(Transaction.description.like(search_term) | Transaction.card.like(search_term))

            if category:
                q = q.filter(Transaction.category == category)

            if card:
                q = q.filter(Transaction.card == card)

            if start_date:
                q = q.filter(Transaction.timestamp >= start_date)

            if end_date:
                q = q.filter(Transaction.timestamp <= end_date)

            if min_amount is not None:
                q = q.filter(Transaction.amount >= min_amount)

            if max_amount is not None:
                q = q.filter(Transaction.amount <= max_amount)

            return q.order_by(desc(Transaction.timestamp), desc(Transaction.id)).all()
        except Exception as e:
            raise DatabaseError(f"Failed to search transactions: {e}")