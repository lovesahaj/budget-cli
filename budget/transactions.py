"""Transaction management module.

This module provides comprehensive functionality for managing financial
transactions, including creation, updates, deletion, retrieval, and searching.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from budget.exceptions import DatabaseError, ValidationError
from budget.models import Transaction

class TransactionManager:
    """Manages financial transactions in the budget tracker.

    The TransactionManager handles all CRUD operations for transactions,
    including advanced search and filtering capabilities.

    Attributes:
        session (Session): SQLAlchemy database session.

    Example:
        >>> with BudgetManager() as bm:
        ...     txn_mgr = TransactionManager(bm.session)
        ...     txn_id = txn_mgr.add_transaction(
        ...         "card", "Visa", "Coffee", 5.0, "Food"
        ...     )
    """

    def __init__(self, session: Session):
        """Initialize the TransactionManager.

        Args:
            session: SQLAlchemy database session for database operations.
        """
        self.session = session

    def add_transaction(
        self,
        t_type: str,
        card: Optional[str],
        description: str,
        amount: float,
        category: Optional[str] = None,
    ):
        """Add a new financial transaction.

        Args:
            t_type: Type of transaction - must be either "cash" or "card".
            card: Name of the card used (required for card transactions,
                 null for cash).
            description: Description of the transaction.
            amount: Transaction amount (must be positive).
            category: Optional category for the transaction.

        Returns:
            int: ID of the newly created transaction.

        Raises:
            ValidationError: If description is empty, amount is not positive,
                           or transaction type is invalid.
            DatabaseError: If adding the transaction fails.

        Example:
            >>> txn_id = txn_mgr.add_transaction(
            ...     "card", "Visa", "Lunch at cafe", 25.50, "Food"
            ... )
        """
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
        """Update an existing transaction.

        Updates one or more fields of an existing transaction. Only fields
        that are provided (not None) will be updated.

        Args:
            transaction_id: ID of the transaction to update.
            t_type: New transaction type ("cash" or "card"), if updating.
            card: New card name, if updating.
            description: New description, if updating.
            amount: New amount (must be positive), if updating.
            category: New category, if updating.

        Returns:
            bool: True if the transaction was updated, False if transaction
                 doesn't exist or no updates were made.

        Raises:
            ValidationError: If amount is not positive or transaction type
                           is invalid.
            DatabaseError: If updating the transaction fails.

        Example:
            >>> success = txn_mgr.update_transaction(
            ...     123, amount=30.0, category="Entertainment"
            ... )
        """
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
        """Delete a transaction by its ID.

        Args:
            transaction_id: ID of the transaction to delete.

        Returns:
            bool: True if the transaction was deleted, False if the
                 transaction doesn't exist.

        Raises:
            DatabaseError: If deleting the transaction fails.

        Example:
            >>> success = txn_mgr.delete_transaction(123)
            >>> if success:
            ...     print("Transaction deleted")
        """
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
        """Retrieve a single transaction by its ID.

        Args:
            transaction_id: ID of the transaction to retrieve.

        Returns:
            Optional[Transaction]: Transaction object if found, None otherwise.

        Raises:
            DatabaseError: If retrieving the transaction fails.

        Example:
            >>> txn = txn_mgr.get_transaction_by_id(123)
            >>> if txn:
            ...     print(f"{txn.description}: ${txn.amount}")
        """
        try:
            return self.session.query(Transaction).filter_by(id=transaction_id).first()
        except Exception as e:
            raise DatabaseError(f"Failed to get transaction: {e}")

    def get_recent_transactions(self, limit: int = 10) -> List[Transaction]:
        """Get the most recent transactions.

        Args:
            limit: Maximum number of transactions to retrieve. Defaults to 10.

        Returns:
            List[Transaction]: List of transactions ordered by timestamp
                              (newest first).

        Raises:
            DatabaseError: If retrieving transactions fails.

        Example:
            >>> recent = txn_mgr.get_recent_transactions(limit=5)
            >>> for txn in recent:
            ...     print(f"{txn.description}: ${txn.amount}")
        """
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
        """Search and filter transactions with multiple criteria.

        Performs a comprehensive search across transactions with support for
        multiple filters. All filters are combined with AND logic.

        Args:
            query: Text to search in description and card fields (case-insensitive).
            category: Filter by specific category.
            card: Filter by specific card name.
            start_date: Filter for transactions on or after this date.
            end_date: Filter for transactions on or before this date.
            min_amount: Filter for transactions with amount >= this value.
            max_amount: Filter for transactions with amount <= this value.

        Returns:
            List[Transaction]: List of matching transactions ordered by
                              timestamp (newest first).

        Raises:
            DatabaseError: If searching transactions fails.

        Example:
            >>> # Search for food transactions over $20
            >>> results = txn_mgr.search_transactions(
            ...     category="Food",
            ...     min_amount=20.0
            ... )
            >>> # Search by text in description
            >>> results = txn_mgr.search_transactions(query="coffee")
        """
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