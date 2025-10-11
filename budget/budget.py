"""Simple personal budget tracker."""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import create_engine, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from budget.models import Balance, Card, Category, SpendingLimit, Transaction
from budget.utils import generate_transaction_hash, serialize_import_metadata


class Budget:
    """Simple budget tracker for managing transactions, balances, and spending limits."""

    def __init__(self, db_name: str = "budget.db"):
        """Initialize budget tracker with database.

        Args:
            db_name: Name of the SQLite database file
        """
        self.db_name = os.environ.get("BUDGET_DB_NAME", db_name)
        self.engine = create_engine(f"sqlite:///{self.db_name}")
        self.Session = sessionmaker(bind=self.engine)
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        from budget.models import Base

        Base.metadata.create_all(self.engine)

    # Transaction operations
    def add_transaction(
        self,
        type: str,
        description: str,
        amount: float,
        card: Optional[str] = None,
        category: Optional[str] = None,
    ) -> int:
        """Add a new transaction.

        Args:
            type: "cash" or "card"
            description: Transaction description
            amount: Amount (must be positive)
            card: Card name (for card transactions)
            category: Optional category

        Returns:
            Transaction ID

        Raises:
            ValueError: If validation fails
        """
        if not description.strip():
            raise ValueError("Description cannot be empty")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if type not in ["cash", "card"]:
            raise ValueError("Type must be 'cash' or 'card'")

        with self.Session() as session:
            txn = Transaction(
                type=type,
                card=card,
                category=category,
                description=description.strip(),
                amount=float(amount),
                import_source="manual",
            )
            session.add(txn)
            session.commit()
            return txn.id

    def add_transaction_safe(
        self,
        type: str,
        description: str,
        amount: float,
        date: Optional[datetime] = None,
        card: Optional[str] = None,
        category: Optional[str] = None,
        import_source: str = "manual",
        import_metadata: Optional[dict] = None,
    ) -> Tuple[Optional[int], bool]:
        """Add a transaction with deduplication check.

        Args:
            type: "cash" or "card"
            description: Transaction description
            amount: Transaction amount
            date: Transaction date (defaults to now)
            card: Card name (for card transactions)
            category: Optional category
            import_source: Source of import ("manual", "pdf", "image", "email")
            import_metadata: Additional metadata about the import

        Returns:
            Tuple of (transaction_id, is_new) where is_new indicates if it was added
        """
        if not description.strip():
            raise ValueError("Description cannot be empty")
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if type not in ["cash", "card"]:
            raise ValueError("Type must be 'cash' or 'card'")

        if date is None:
            date = datetime.now()

        # Generate hash for deduplication
        txn_hash = generate_transaction_hash(date, amount, description, card)

        with self.Session() as session:
            # Check if transaction already exists
            existing = session.query(Transaction).filter_by(hash=txn_hash).first()
            if existing:
                return (existing.id, False)

            # Create new transaction
            txn = Transaction(
                type=type,
                card=card,
                category=category,
                description=description.strip(),
                amount=float(amount),
                timestamp=date,
                hash=txn_hash,
                import_source=import_source,
                import_metadata=serialize_import_metadata(import_metadata or {}),
            )

            try:
                session.add(txn)
                session.commit()
                return (txn.id, True)
            except IntegrityError:
                # Race condition: transaction was added between check and insert
                session.rollback()
                existing = session.query(Transaction).filter_by(hash=txn_hash).first()
                return (existing.id if existing else None, False)

    def import_transactions(
        self,
        transactions: List[dict],
        import_source: str,
    ) -> Dict[str, int]:
        """Import multiple transactions with deduplication.

        Args:
            transactions: List of transaction dicts with keys:
                - type: str
                - description: str
                - amount: float
                - date: datetime (optional)
                - card: str (optional)
                - category: str (optional)
                - metadata: dict (optional)
            import_source: Source of import ("pdf", "image", "email")

        Returns:
            Dict with statistics: {
                "total": int,
                "imported": int,
                "duplicates": int,
                "errors": int
            }
        """
        stats = {
            "total": len(transactions),
            "imported": 0,
            "duplicates": 0,
            "errors": 0,
        }

        for txn_data in transactions:
            try:
                _, is_new = self.add_transaction_safe(
                    type=txn_data.get("type", "card"),
                    description=txn_data["description"],
                    amount=txn_data["amount"],
                    date=txn_data.get("date"),
                    card=txn_data.get("card"),
                    category=txn_data.get("category"),
                    import_source=import_source,
                    import_metadata=txn_data.get("metadata"),
                )

                if is_new:
                    stats["imported"] += 1
                else:
                    stats["duplicates"] += 1

            except Exception as e:
                stats["errors"] += 1
                # Log error but continue processing
                print(f"Error importing transaction: {e}")

        return stats

    def update_transaction(
        self,
        transaction_id: int,
        type: Optional[str] = None,
        card: Optional[str] = None,
        description: Optional[str] = None,
        amount: Optional[float] = None,
        category: Optional[str] = None,
    ) -> bool:
        """Update an existing transaction.

        Args:
            transaction_id: ID of transaction to update
            type: New type (optional)
            card: New card (optional)
            description: New description (optional)
            amount: New amount (optional)
            category: New category (optional)

        Returns:
            True if updated, False if not found
        """
        with self.Session() as session:
            txn = session.query(Transaction).filter_by(id=transaction_id).first()
            if not txn:
                return False

            if type is not None:
                if type not in ["cash", "card"]:
                    raise ValueError("Type must be 'cash' or 'card'")
                txn.type = type
                if type == "cash":
                    txn.card = None

            if card is not None and txn.type != "cash":
                txn.card = card
            if description is not None and description.strip():
                txn.description = description.strip()
            if amount is not None:
                if amount <= 0:
                    raise ValueError("Amount must be positive")
                txn.amount = float(amount)
            if category is not None:
                txn.category = category

            session.commit()
            return True

    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction.

        Args:
            transaction_id: ID of transaction to delete

        Returns:
            True if deleted, False if not found
        """
        with self.Session() as session:
            txn = session.query(Transaction).filter_by(id=transaction_id).first()
            if txn:
                session.delete(txn)
                session.commit()
                return True
            return False

    def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        """Get a transaction by ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction or None if not found
        """
        with self.Session() as session:
            return session.query(Transaction).filter_by(id=transaction_id).first()

    def get_recent_transactions(self, limit: int = 10) -> List[Transaction]:
        """Get recent transactions.

        Args:
            limit: Maximum number of transactions

        Returns:
            List of transactions (newest first)
        """
        with self.Session() as session:
            return (
                session.query(Transaction)
                .order_by(desc(Transaction.timestamp), desc(Transaction.id))
                .limit(limit)
                .all()
            )

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
        """Search transactions with filters.

        Args:
            query: Text to search in description/card
            category: Filter by category
            card: Filter by card
            start_date: Start date filter
            end_date: End date filter
            min_amount: Minimum amount
            max_amount: Maximum amount

        Returns:
            List of matching transactions
        """
        with self.Session() as session:
            q = session.query(Transaction)

            if query:
                search = f"%{query}%"
                q = q.filter(
                    Transaction.description.like(search) | Transaction.card.like(search)
                )
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

    # Category operations
    def add_category(self, name: str, description: str = "") -> bool:
        """Add a new category.

        Args:
            name: Category name
            description: Category description

        Returns:
            True if added, False if already exists
        """
        with self.Session() as session:
            existing = session.query(Category).filter_by(name=name).first()
            if existing:
                return False

            category = Category(name=name, description=description)
            session.add(category)
            session.commit()
            return True

    def get_categories(self) -> List[Category]:
        """Get all categories.

        Returns:
            List of categories
        """
        with self.Session() as session:
            return session.query(Category).all()

    # Card operations
    def add_card(self, name: str) -> bool:
        """Add a new card.

        Args:
            name: Card name

        Returns:
            True if added, False if already exists
        """
        with self.Session() as session:
            existing = session.query(Card).filter_by(name=name).first()
            if existing:
                return False

            card = Card(name=name)
            session.add(card)
            session.commit()
            return True

    def get_cards(self) -> List[Card]:
        """Get all cards.

        Returns:
            List of cards
        """
        with self.Session() as session:
            return session.query(Card).all()

    # Balance operations
    def get_balance(self, type: str) -> float:
        """Get balance for a type.

        Args:
            type: Balance type (e.g., "cash", card name)

        Returns:
            Current balance (0.0 if not found)
        """
        with self.Session() as session:
            balance = session.query(Balance).filter_by(type=type).first()
            return balance.amount if balance else 0.0

    def get_all_balances(self) -> Dict[str, float]:
        """Get all balances.

        Returns:
            Dict mapping balance type to amount
        """
        with self.Session() as session:
            balances = session.query(Balance).all()
            return {b.type: b.amount for b in balances}

    def update_balance(self, type: str, amount: float):
        """Update balance for a type.

        Args:
            type: Balance type
            amount: New balance amount
        """
        with self.Session() as session:
            balance = session.query(Balance).filter_by(type=type).first()
            if balance:
                balance.amount = float(amount)
            else:
                balance = Balance(type=type, amount=float(amount))
                session.add(balance)
            session.commit()

    # Spending limit operations
    def set_spending_limit(
        self,
        limit_amount: float,
        period: str = "monthly",
        category: Optional[str] = None,
        source: Optional[str] = None,
    ) -> bool:
        """Set a spending limit.

        Args:
            limit_amount: Maximum spending amount
            period: "daily", "weekly", "monthly", or "yearly"
            category: Optional category to limit
            source: Optional source to limit

        Returns:
            True if set successfully
        """
        if period not in ["daily", "weekly", "monthly", "yearly"]:
            raise ValueError("Period must be daily, weekly, monthly, or yearly")

        with self.Session() as session:
            limit = SpendingLimit(
                category=category,
                source=source,
                limit_amount=float(limit_amount),
                period=period,
            )
            session.add(limit)
            session.commit()
            return True

    def get_spending_limits(self) -> List[SpendingLimit]:
        """Get all spending limits.

        Returns:
            List of spending limits
        """
        with self.Session() as session:
            return session.query(SpendingLimit).all()

    def check_spending_limit(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        period: str = "monthly",
    ) -> Dict[str, float]:
        """Check if spending limit is exceeded.

        Args:
            category: Category to check
            source: Source to check
            period: Time period

        Returns:
            Dict with spent, limit, exceeded, and remaining amounts
        """
        with self.Session() as session:
            # Find matching limit
            limit_query = session.query(SpendingLimit).filter_by(period=period)
            if category:
                limit_query = limit_query.filter_by(category=category)
            if source:
                limit_query = limit_query.filter_by(source=source)

            limit = limit_query.first()
            if not limit:
                return {
                    "spent": 0.0,
                    "limit": 0.0,
                    "exceeded": False,
                    "remaining": 0.0,
                }

            # Calculate date range for period
            now = datetime.now()
            if period == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "weekly":
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            elif period == "monthly":
                start_date = now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
            else:  # yearly
                start_date = now.replace(
                    month=1, day=1, hour=0, minute=0, second=0, microsecond=0
                )

            # Calculate spending
            txn_query = session.query(Transaction).filter(
                Transaction.timestamp >= start_date
            )
            if category:
                txn_query = txn_query.filter(Transaction.category == category)
            if source:
                if source == "cash":
                    txn_query = txn_query.filter(Transaction.type == "cash")
                else:
                    txn_query = txn_query.filter(Transaction.card == source)

            spent = sum(txn.amount for txn in txn_query.all())
            exceeded = spent > limit.limit_amount
            remaining = max(0.0, limit.limit_amount - spent)

            return {
                "spent": spent,
                "limit": limit.limit_amount,
                "exceeded": exceeded,
                "remaining": remaining,
            }

    # Report operations
    def get_daily_spending(self, days: int = 30) -> List[Tuple[str, float]]:
        """Get daily spending for the last N days.

        Args:
            days: Number of days to include

        Returns:
            List of (date, total_spent) tuples
        """
        with self.Session() as session:
            start_date = datetime.now() - timedelta(days=days)
            txns = (
                session.query(Transaction)
                .filter(Transaction.timestamp >= start_date)
                .all()
            )

            # Group by date
            daily = {}
            for txn in txns:
                date_str = txn.timestamp.strftime("%Y-%m-%d")
                daily[date_str] = daily.get(date_str, 0.0) + txn.amount

            # Return sorted list
            return sorted(daily.items())

    def get_spending_by_category(self, year: int, month: int) -> Dict[str, float]:
        """Get spending breakdown by category for a month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Dict mapping category to total spent
        """
        with self.Session() as session:
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            txns = (
                session.query(Transaction)
                .filter(
                    Transaction.timestamp >= start_date,
                    Transaction.timestamp < end_date,
                )
                .all()
            )

            # Group by category
            by_category = {}
            for txn in txns:
                cat = txn.category or "Uncategorized"
                by_category[cat] = by_category.get(cat, 0.0) + txn.amount

            return by_category
