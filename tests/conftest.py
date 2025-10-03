"""Pytest fixtures for budget tests."""

import os
import tempfile
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from budget.balances import BalanceManager
from budget.budget_core import BudgetManager
from budget.cards import CardManager
from budget.categories import CategoryManager
from budget.exports import ExportManager
from budget.limits import LimitManager
from budget.models import Base
from budget.reports import ReportManager
from budget.transactions import TransactionManager


@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite engine for testing."""
    return create_engine("sqlite:///:memory:")


@pytest.fixture(scope="session")
def tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine, tables):
    """Returns a SQLAlchemy session, and after the test tears down everything properly."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# Individual manager fixtures
@pytest.fixture
def transaction_manager(db_session):
    """Create a TransactionManager instance."""
    return TransactionManager(db_session)


@pytest.fixture
def balance_manager(db_session, card_manager):
    """Create a BalanceManager instance."""
    # Load cards to ensure default balances are created
    card_manager.load_cards()
    return BalanceManager(db_session)


@pytest.fixture
def category_manager(db_session):
    """Create a CategoryManager instance."""
    return CategoryManager(db_session)


@pytest.fixture
def card_manager(db_session):
    """Create a CardManager instance."""
    return CardManager(db_session)


@pytest.fixture
def limit_manager(db_session):
    """Create a LimitManager instance."""
    return LimitManager(db_session)


@pytest.fixture
def report_manager(db_session, balance_manager):
    """Create a ReportManager instance."""
    return ReportManager(db_session, balance_manager)


@pytest.fixture
def export_manager(transaction_manager):
    """Create an ExportManager instance."""
    return ExportManager(transaction_manager)


# Sample data fixtures
@pytest.fixture
def sample_cards(card_manager):
    """Create sample cards and return them."""
    card_manager.add_new_card("Wise")
    card_manager.add_new_card("ICICI")
    return card_manager.load_cards()


@pytest.fixture
def sample_categories(category_manager):
    """Create sample categories and return them as tuples (name, description)."""
    categories = [
        ("Food", "Food and dining"),
        ("Transport", "Transportation"),
        ("Entertainment", "Entertainment and leisure"),
    ]
    for name, description in categories:
        category_manager.add_category(name, description)
    return categories


@pytest.fixture
def sample_balances(balance_manager):
    """Create sample balances and return the balance dictionary."""
    balance_manager.update_balance("cash", 100.00)
    balance_manager.update_balance("Wise", 500.00)
    balance_manager.update_balance("ICICI", 1000.00)
    return {"cash": 100.00, "Wise": 500.00, "ICICI": 1000.00}


@pytest.fixture
def sample_transactions(transaction_manager):
    """Create sample transactions and return their IDs."""
    ids = []

    # Add transactions with different types and categories
    # Designed to match test expectations:
    # - 2 Food transactions (Lunch, Groceries)
    # - 1 Wise transaction (Groceries)
    # - 2 transactions >= 10.00 (Lunch 10.50, Groceries 25.00)
    # - 1 transaction <= 5.00 (Bus fare 2.50)
    # - Movie ticket and Coffee both < 10.00
    ids.append(transaction_manager.add_transaction("cash", None, "Lunch", 10.50, "Food"))
    ids.append(transaction_manager.add_transaction("card", "Wise", "Groceries", 25.00, "Food"))
    ids.append(transaction_manager.add_transaction("card", "ICICI", "Movie ticket", 8.00, "Entertainment"))
    ids.append(transaction_manager.add_transaction("cash", None, "Bus fare", 2.50, "Transport"))
    ids.append(transaction_manager.add_transaction("cash", None, "Coffee", 5.50, "Entertainment"))

    return ids


@pytest.fixture
def sample_limits(limit_manager):
    """Create sample spending limits and return them."""
    limit_manager.set_spending_limit(100.00, "monthly", "Food", None)
    limit_manager.set_spending_limit(50.00, "weekly", None, "cash")
    limit_manager.set_spending_limit(500.00, "monthly", None, "Wise")
    return limit_manager.get_spending_limits()


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def budget_manager(db_session, sample_cards):
    """Create a BudgetManager instance with all managers initialized."""
    # Create a temporary BudgetManager without using context manager
    bm = BudgetManager.__new__(BudgetManager)
    bm.session = db_session
    bm.cards = []
    bm.categories = []

    # Initialize all managers with the test session
    bm.transactions = TransactionManager(db_session)
    bm.card_manager = CardManager(db_session)
    bm.categories_manager = CategoryManager(db_session)
    bm.balances_manager = BalanceManager(db_session)
    bm.limits_manager = LimitManager(db_session)
    bm.reports_manager = ReportManager(db_session, bm.balances_manager)
    bm.export_manager = ExportManager(bm.transactions)

    # Load initial data
    bm.cards = bm.card_manager.load_cards()
    bm.categories = bm.categories_manager.load_categories()

    return bm
