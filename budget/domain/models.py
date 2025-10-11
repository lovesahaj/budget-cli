"""SQLAlchemy ORM models for the budget application.

This module defines the database schema and model classes for all entities
in the budget tracker, including cards, categories, transactions, balances,
and spending limits.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


class DictAccessMixin:
    """Mixin to add dictionary-like attribute access to SQLAlchemy models.

    This mixin enables accessing model attributes using dictionary-style
    bracket notation in addition to the standard dot notation.

    Example:
        >>> transaction = Transaction(description="Coffee", amount=5.0)
        >>> # Both notations work:
        >>> transaction.description  # Returns "Coffee"
        >>> transaction["description"]  # Also returns "Coffee"
    """

    def __getitem__(self, key):
        """Get attribute value using dictionary-style access.

        Args:
            key: Name of the attribute to retrieve.

        Returns:
            The value of the requested attribute.

        Raises:
            AttributeError: If the attribute does not exist.
        """
        return getattr(self, key)


class Card(Base, DictAccessMixin):
    """Payment card entity model.

    Represents a payment card (credit card, debit card, etc.) that can be
    used for transactions.

    Attributes:
        id (int): Unique identifier (auto-incremented).
        name (str): Unique name of the card (e.g., "Visa", "ICICI").
    """

    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)


class Category(Base, DictAccessMixin):
    """Transaction category model.

    Represents a category for organizing and classifying transactions
    (e.g., "Food", "Transport", "Entertainment").

    Attributes:
        id (int): Unique identifier (auto-incremented).
        name (str): Unique name of the category.
        description (str): Optional description of the category.
    """

    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)


class Transaction(Base, DictAccessMixin):
    """Financial transaction model.

    Represents a single financial transaction, including both cash and
    card-based transactions.

    Attributes:
        id (int): Unique identifier (auto-incremented).
        type (str): Transaction type - either "cash" or "card".
        card (str): Name of the card used (null for cash transactions).
        category (str): Category of the transaction (optional).
        description (str): Description of the transaction.
        amount (float): Transaction amount (must be positive).
        timestamp (datetime): When the transaction was created (auto-set).
    """

    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, nullable=False)
    card = Column(String)
    category = Column(String)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=func.now())


class Balance(Base, DictAccessMixin):
    """Account balance model.

    Tracks the current balance for different payment sources (cash or
    specific cards).

    Attributes:
        type (str): Type/name of the balance (e.g., "cash", card name).
                   This is the primary key.
        amount (float): Current balance amount. Defaults to 0.0.
    """

    __tablename__ = "balances"
    type = Column(String, unique=True, nullable=False, primary_key=True)
    amount = Column(Float, nullable=False, default=0.0)


class SpendingLimit(Base, DictAccessMixin):
    """Spending limit configuration model.

    Defines spending limits that can be set for specific categories,
    payment sources, or overall spending for different time periods.

    Attributes:
        id (int): Unique identifier (auto-incremented).
        category (str): Category to limit (null for all categories).
        source (str): Payment source to limit (null for all sources).
        limit_amount (float): Maximum allowed spending amount.
        period (str): Time period - "daily", "weekly", "monthly", or "yearly".
    """

    __tablename__ = "spending_limits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String)
    source = Column(String)
    limit_amount = Column(Float, nullable=False)
    period = Column(String, nullable=False)
