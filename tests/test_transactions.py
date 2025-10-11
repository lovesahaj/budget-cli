"""Tests for TransactionManager."""

import pytest

from budget.domain.exceptions import DatabaseError, ValidationError
from budget.domain.models import Transaction


def test_add_transaction_cash(transaction_manager):
    """Test adding a cash transaction."""
    tid = transaction_manager.add_transaction("cash", None, "Coffee", 3.50, "Food")

    assert tid is not None
    assert tid > 0


def test_add_transaction_card(transaction_manager):
    """Test adding a card transaction."""
    tid = transaction_manager.add_transaction(
        "card", "Wise", "Groceries", 25.00, "Food"
    )

    assert tid is not None
    assert tid > 0


def test_add_transaction_without_category(transaction_manager):
    """Test adding a transaction without category."""
    tid = transaction_manager.add_transaction("cash", None, "Bus fare", 2.50, None)

    assert tid is not None
    transaction = transaction_manager.get_transaction_by_id(tid)
    assert transaction.category is None


def test_add_transaction_empty_description_raises_error(transaction_manager):
    """Test that empty description raises ValidationError."""
    with pytest.raises(ValidationError, match="Description cannot be empty"):
        transaction_manager.add_transaction("cash", None, "", 3.50, None)


def test_add_transaction_whitespace_description_raises_error(transaction_manager):
    """Test that whitespace-only description raises ValidationError."""
    with pytest.raises(ValidationError, match="Description cannot be empty"):
        transaction_manager.add_transaction("cash", None, "   ", 3.50, None)


def test_add_transaction_negative_amount_raises_error(transaction_manager):
    """Test that negative amount raises ValidationError."""
    with pytest.raises(ValidationError, match="Amount must be positive"):
        transaction_manager.add_transaction("cash", None, "Test", -5.00, None)


def test_add_transaction_zero_amount_raises_error(transaction_manager):
    """Test that zero amount raises ValidationError."""
    with pytest.raises(ValidationError, match="Amount must be positive"):
        transaction_manager.add_transaction("cash", None, "Test", 0, None)


def test_add_transaction_invalid_type_raises_error(transaction_manager):
    """Test that invalid transaction type raises ValidationError."""
    with pytest.raises(ValidationError, match="Transaction type must be"):
        transaction_manager.add_transaction("invalid", None, "Test", 5.00, None)


def test_get_transaction_by_id(transaction_manager, sample_transactions):
    """Test retrieving a transaction by ID."""
    tid = sample_transactions[0]
    transaction = transaction_manager.get_transaction_by_id(tid)

    assert transaction is not None
    assert isinstance(transaction, Transaction)
    assert transaction.id == tid
    assert transaction.description == "Lunch"
    assert transaction.amount == 10.50


def test_get_transaction_by_id_nonexistent(transaction_manager):
    """Test retrieving nonexistent transaction returns None."""
    transaction = transaction_manager.get_transaction_by_id(99999)

    assert transaction is None


def test_get_recent_transactions(transaction_manager, sample_transactions):
    """Test getting recent transactions."""
    transactions = transaction_manager.get_recent_transactions(limit=3)

    assert len(transactions) == 3
    assert all(isinstance(t, Transaction) for t in transactions)
    # Should be in reverse chronological order (most recent first)
    assert transactions[0].id == sample_transactions[-1]


def test_get_recent_transactions_limit(transaction_manager, sample_transactions):
    """Test that limit parameter works correctly."""
    transactions = transaction_manager.get_recent_transactions(limit=2)

    assert len(transactions) == 2


def test_update_transaction_description(transaction_manager, sample_transactions):
    """Test updating transaction description."""
    tid = sample_transactions[0]
    result = transaction_manager.update_transaction(tid, description="Updated coffee")

    assert result is True
    transaction = transaction_manager.get_transaction_by_id(tid)
    assert transaction.description == "Updated coffee"


def test_update_transaction_amount(transaction_manager, sample_transactions):
    """Test updating transaction amount."""
    tid = sample_transactions[0]
    result = transaction_manager.update_transaction(tid, amount=4.50)

    assert result is True
    transaction = transaction_manager.get_transaction_by_id(tid)
    assert transaction.amount == 4.50


def test_update_transaction_category(transaction_manager, sample_transactions):
    """Test updating transaction category."""
    tid = sample_transactions[0]
    result = transaction_manager.update_transaction(tid, category="Drinks")

    assert result is True
    transaction = transaction_manager.get_transaction_by_id(tid)
    assert transaction.category == "Drinks"


def test_update_transaction_type_to_card(transaction_manager, sample_transactions):
    """Test updating transaction type from cash to card."""
    tid = sample_transactions[0]  # Cash transaction
    result = transaction_manager.update_transaction(tid, t_type="card", card="Wise")

    assert result is True
    transaction = transaction_manager.get_transaction_by_id(tid)
    assert transaction.type == "card"
    assert transaction.card == "Wise"


def test_update_transaction_type_to_cash_clears_card(
    transaction_manager, sample_transactions
):
    """Test updating transaction type from card to cash clears card field."""
    tid = sample_transactions[1]  # Card transaction
    result = transaction_manager.update_transaction(tid, t_type="cash")

    assert result is True
    transaction = transaction_manager.get_transaction_by_id(tid)
    assert transaction.type == "cash"
    assert transaction.card is None


def test_update_transaction_no_changes_returns_false(
    transaction_manager, sample_transactions
):
    """Test that updating with no changes returns False."""
    tid = sample_transactions[0]
    result = transaction_manager.update_transaction(tid)

    assert result is False


def test_update_transaction_nonexistent_returns_false(transaction_manager):
    """Test that updating nonexistent transaction returns False."""
    result = transaction_manager.update_transaction(99999, description="Test")

    assert result is False


def test_update_transaction_invalid_amount_raises_error(
    transaction_manager, sample_transactions
):
    """Test that updating with invalid amount raises ValidationError."""
    tid = sample_transactions[0]
    with pytest.raises(ValidationError, match="Amount must be positive"):
        transaction_manager.update_transaction(tid, amount=-5.00)


def test_delete_transaction(transaction_manager, sample_transactions):
    """Test deleting a transaction."""
    tid = sample_transactions[0]
    result = transaction_manager.delete_transaction(tid)

    assert result is True
    transaction = transaction_manager.get_transaction_by_id(tid)
    assert transaction is None


def test_delete_transaction_nonexistent_returns_false(transaction_manager):
    """Test that deleting nonexistent transaction returns False."""
    result = transaction_manager.delete_transaction(99999)

    assert result is False


def test_search_transactions_by_description(transaction_manager, sample_transactions):
    """Test searching transactions by description."""
    transactions = transaction_manager.search_transactions(query="Coffee")

    assert len(transactions) >= 1
    assert all(
        "Coffee" in t.description or "Coffee" in (t.card or "") for t in transactions
    )


def test_search_transactions_by_category(transaction_manager, sample_transactions):
    transactions = transaction_manager.search_transactions(category="Food")

    assert len(transactions) == 2
    assert all(t.category == "Food" for t in transactions)


def test_search_transactions_by_card(transaction_manager, sample_transactions):
    """Test searching transactions by card."""
    transactions = transaction_manager.search_transactions(card="Wise")

    assert len(transactions) == 1
    assert all(t.card == "Wise" for t in transactions)


def test_search_transactions_by_min_amount(transaction_manager, sample_transactions):
    """Test searching transactions by minimum amount."""
    transactions = transaction_manager.search_transactions(min_amount=10.00)

    assert len(transactions) == 2
    assert all(t.amount >= 10.00 for t in transactions)


def test_search_transactions_by_max_amount(transaction_manager, sample_transactions):
    """Test searching transactions by maximum amount."""
    transactions = transaction_manager.search_transactions(max_amount=5.00)

    assert len(transactions) == 1
    assert all(t.amount <= 5.00 for t in transactions)


def test_search_transactions_multiple_filters(transaction_manager, sample_transactions):
    transactions = transaction_manager.search_transactions(
        category="Food", min_amount=20.00
    )

    assert len(transactions) == 1
    assert all(t.category == "Food" and t.amount >= 20.00 for t in transactions)


def test_search_transactions_no_results(transaction_manager, sample_transactions):
    """Test searching with no matching results."""
    transactions = transaction_manager.search_transactions(query="NonexistentItem")

    assert len(transactions) == 0
