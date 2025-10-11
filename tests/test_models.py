"""Tests for models module."""

import pytest

from budget.domain.models import Balance, Card, Category, SpendingLimit, Transaction


def test_transaction_creation():
    """Test creating a Transaction instance."""
    transaction = Transaction(
        id=1,
        type="cash",
        card=None,
        category="Food",
        description="Coffee",
        amount=3.50,
        timestamp="2025-10-02 10:30:00",
    )

    assert transaction.id == 1
    assert transaction.type == "cash"
    assert transaction.card is None
    assert transaction.category == "Food"
    assert transaction.description == "Coffee"
    assert transaction.amount == 3.50
    assert transaction.timestamp == "2025-10-02 10:30:00"


def test_transaction_dict_access():
    """Test that Transaction supports dict-like access."""
    transaction = Transaction(
        id=1,
        type="card",
        card="Wise",
        category="Food",
        description="Groceries",
        amount=25.00,
        timestamp="2025-10-02 10:30:00",
    )

    # Test dict-like access
    assert transaction["id"] == 1
    assert transaction["type"] == "card"
    assert transaction["card"] == "Wise"
    assert transaction["category"] == "Food"
    assert transaction["description"] == "Groceries"
    assert transaction["amount"] == 25.00
    assert transaction["timestamp"] == "2025-10-02 10:30:00"


def test_category_creation():
    """Test creating a Category instance."""
    category = Category(id=1, name="Food", description="Food and groceries")

    assert category.id == 1
    assert category.name == "Food"
    assert category.description == "Food and groceries"


def test_category_dict_access():
    """Test that Category supports dict-like access."""
    category = Category(id=1, name="Transport", description="Bus, taxi, etc.")

    assert category["id"] == 1
    assert category["name"] == "Transport"
    assert category["description"] == "Bus, taxi, etc."


def test_card_creation():
    """Test creating a Card instance."""
    card = Card(id=1, name="Wise")

    assert card.id == 1
    assert card.name == "Wise"


def test_card_dict_access():
    """Test that Card supports dict-like access."""
    card = Card(id=2, name="ICICI")

    assert card["id"] == 2
    assert card["name"] == "ICICI"


def test_balance_creation():
    """Test creating a Balance instance."""
    balance = Balance(type="cash", amount=100.00)

    assert balance.type == "cash"
    assert balance.amount == 100.00


def test_balance_dict_access():
    """Test that Balance supports dict-like access."""
    balance = Balance(type="Wise", amount=500.00)

    assert balance["type"] == "Wise"
    assert balance["amount"] == 500.00


def test_spending_limit_creation():
    """Test creating a SpendingLimit instance."""
    limit = SpendingLimit(
        id=1, category="Food", source=None, limit_amount=100.00, period="monthly"
    )

    assert limit.id == 1
    assert limit.category == "Food"
    assert limit.source is None
    assert limit.limit_amount == 100.00
    assert limit.period == "monthly"


def test_spending_limit_dict_access():
    """Test that SpendingLimit supports dict-like access."""
    limit = SpendingLimit(
        id=2, category=None, source="cash", limit_amount=50.00, period="weekly"
    )

    assert limit["id"] == 2
    assert limit["category"] is None
    assert limit["source"] == "cash"
    assert limit["limit_amount"] == 50.00
    assert limit["period"] == "weekly"


def test_transaction_with_optional_fields():
    """Test Transaction with optional fields as None."""
    transaction = Transaction(
        id=5,
        type="cash",
        card=None,
        category=None,
        description="Random purchase",
        amount=10.00,
        timestamp="2025-10-02 15:00:00",
    )

    assert transaction.card is None
    assert transaction.category is None
    assert transaction["card"] is None
    assert transaction["category"] is None
