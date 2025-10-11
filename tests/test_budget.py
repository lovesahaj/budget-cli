"""Tests for the Budget class."""

import os
import tempfile
from datetime import datetime

import pytest

from budget import Budget


@pytest.fixture
def budget():
    """Create a temporary budget tracker for testing."""
    # Use a temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    budget = Budget(db_path)
    yield budget

    # Clean up
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestTransactions:
    """Test transaction operations."""

    def test_add_transaction(self, budget):
        """Test adding a transaction."""
        txn_id = budget.add_transaction("cash", "Coffee", 5.50, category="Food")
        assert txn_id is not None

        txn = budget.get_transaction(txn_id)
        assert txn.description == "Coffee"
        assert txn.amount == 5.50
        assert txn.type == "cash"
        assert txn.category == "Food"

    def test_add_card_transaction(self, budget):
        """Test adding a card transaction."""
        txn_id = budget.add_transaction(
            "card", "Lunch", 12.50, card="Visa", category="Food"
        )

        txn = budget.get_transaction(txn_id)
        assert txn.card == "Visa"
        assert txn.type == "card"

    def test_add_transaction_validation(self, budget):
        """Test transaction validation."""
        with pytest.raises(ValueError, match="Description cannot be empty"):
            budget.add_transaction("cash", "", 5.0)

        with pytest.raises(ValueError, match="Amount must be positive"):
            budget.add_transaction("cash", "Test", -5.0)

        with pytest.raises(ValueError, match="Type must be"):
            budget.add_transaction("invalid", "Test", 5.0)

    def test_update_transaction(self, budget):
        """Test updating a transaction."""
        txn_id = budget.add_transaction("cash", "Coffee", 5.50)

        assert budget.update_transaction(txn_id, description="Tea", amount=3.50)

        txn = budget.get_transaction(txn_id)
        assert txn.description == "Tea"
        assert txn.amount == 3.50

    def test_update_nonexistent_transaction(self, budget):
        """Test updating a transaction that doesn't exist."""
        assert not budget.update_transaction(9999, description="Test")

    def test_delete_transaction(self, budget):
        """Test deleting a transaction."""
        txn_id = budget.add_transaction("cash", "Coffee", 5.50)

        assert budget.delete_transaction(txn_id)
        assert budget.get_transaction(txn_id) is None

    def test_delete_nonexistent_transaction(self, budget):
        """Test deleting a transaction that doesn't exist."""
        assert not budget.delete_transaction(9999)

    def test_get_recent_transactions(self, budget):
        """Test getting recent transactions."""
        budget.add_transaction("cash", "Coffee", 5.50)
        budget.add_transaction("cash", "Lunch", 12.50)
        budget.add_transaction("cash", "Dinner", 20.00)

        recent = budget.get_recent_transactions(2)
        assert len(recent) == 2
        assert recent[0].description == "Dinner"
        assert recent[1].description == "Lunch"

    def test_search_transactions(self, budget):
        """Test searching transactions."""
        budget.add_transaction("cash", "Coffee shop", 5.50, category="Food")
        budget.add_transaction("card", "Coffee beans", 15.00, card="Visa", category="Groceries")
        budget.add_transaction("cash", "Lunch", 12.50, category="Food")

        # Search by query
        results = budget.search_transactions(query="Coffee")
        assert len(results) == 2

        # Search by category
        results = budget.search_transactions(category="Food")
        assert len(results) == 2

        # Search by amount range
        results = budget.search_transactions(min_amount=10.0)
        assert len(results) == 2


class TestCategories:
    """Test category operations."""

    def test_add_category(self, budget):
        """Test adding a category."""
        assert budget.add_category("Food", "Food and dining")

        categories = budget.get_categories()
        assert len(categories) == 1
        assert categories[0].name == "Food"
        assert categories[0].description == "Food and dining"

    def test_add_duplicate_category(self, budget):
        """Test adding a duplicate category."""
        budget.add_category("Food")
        assert not budget.add_category("Food")

    def test_get_categories(self, budget):
        """Test getting all categories."""
        budget.add_category("Food")
        budget.add_category("Transport")

        categories = budget.get_categories()
        assert len(categories) == 2


class TestCards:
    """Test card operations."""

    def test_add_card(self, budget):
        """Test adding a card."""
        assert budget.add_card("Visa")

        cards = budget.get_cards()
        assert len(cards) == 1
        assert cards[0].name == "Visa"

    def test_add_duplicate_card(self, budget):
        """Test adding a duplicate card."""
        budget.add_card("Visa")
        assert not budget.add_card("Visa")


class TestBalances:
    """Test balance operations."""

    def test_get_balance(self, budget):
        """Test getting a balance."""
        balance = budget.get_balance("cash")
        assert balance == 0.0

    def test_update_balance(self, budget):
        """Test updating a balance."""
        budget.update_balance("cash", 100.0)
        assert budget.get_balance("cash") == 100.0

    def test_get_all_balances(self, budget):
        """Test getting all balances."""
        budget.update_balance("cash", 100.0)
        budget.update_balance("Visa", 500.0)

        balances = budget.get_all_balances()
        assert len(balances) == 2
        assert balances["cash"] == 100.0
        assert balances["Visa"] == 500.0


class TestSpendingLimits:
    """Test spending limit operations."""

    def test_set_spending_limit(self, budget):
        """Test setting a spending limit."""
        assert budget.set_spending_limit(500.0, "monthly", category="Food")

        limits = budget.get_spending_limits()
        assert len(limits) == 1
        assert limits[0].limit_amount == 500.0
        assert limits[0].period == "monthly"

    def test_check_spending_limit(self, budget):
        """Test checking spending against limits."""
        budget.set_spending_limit(100.0, "monthly", category="Food")
        budget.add_transaction("cash", "Lunch", 30.0, category="Food")
        budget.add_transaction("cash", "Dinner", 40.0, category="Food")

        result = budget.check_spending_limit(category="Food", period="monthly")
        assert result["limit"] == 100.0
        assert result["spent"] == 70.0
        assert result["remaining"] == 30.0
        assert not result["exceeded"]

    def test_check_exceeded_limit(self, budget):
        """Test checking an exceeded limit."""
        budget.set_spending_limit(50.0, "monthly", category="Food")
        budget.add_transaction("cash", "Lunch", 30.0, category="Food")
        budget.add_transaction("cash", "Dinner", 40.0, category="Food")

        result = budget.check_spending_limit(category="Food", period="monthly")
        assert result["exceeded"]


class TestReports:
    """Test reporting operations."""

    def test_get_daily_spending(self, budget):
        """Test getting daily spending."""
        budget.add_transaction("cash", "Coffee", 5.50)
        budget.add_transaction("cash", "Lunch", 12.50)

        daily = budget.get_daily_spending(7)
        assert len(daily) > 0

    def test_get_spending_by_category(self, budget):
        """Test getting spending by category."""
        now = datetime.now()
        budget.add_transaction("cash", "Coffee", 10.0, category="Food")
        budget.add_transaction("cash", "Lunch", 20.0, category="Food")
        budget.add_transaction("cash", "Bus", 5.0, category="Transport")

        spending = budget.get_spending_by_category(now.year, now.month)
        assert spending["Food"] == 30.0
        assert spending["Transport"] == 5.0
