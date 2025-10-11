"""SQLAlchemy ORM models for the budget tracker."""

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Card(Base):
    """Payment card model."""

    __tablename__ = "cards"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)


class Category(Base):
    """Transaction category model."""

    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)


class Transaction(Base):
    """Financial transaction model."""

    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, nullable=False)  # "cash" or "card"
    card = Column(String)
    category = Column(String)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=func.now())

    # Deduplication and import tracking
    hash = Column(String, unique=True, index=True)  # SHA256 hash for deduplication
    import_source = Column(String)  # "manual", "pdf", "image", "email"
    import_metadata = Column(String)  # JSON string with additional import info


class Balance(Base):
    """Account balance model."""

    __tablename__ = "balances"
    type = Column(String, unique=True, nullable=False, primary_key=True)
    amount = Column(Float, nullable=False, default=0.0)


class SpendingLimit(Base):
    """Spending limit model."""

    __tablename__ = "spending_limits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String)
    source = Column(String)
    limit_amount = Column(Float, nullable=False)
    period = Column(String, nullable=False)  # "daily", "weekly", "monthly", "yearly"
