"""Tests for ReportManager."""

from datetime import datetime

import pytest


def test_get_daily_spending(report_manager, transaction_manager):
    """Test getting daily spending data."""
    # Add some transactions
    transaction_manager.add_transaction("cash", None, "Coffee", 3.50, "Food")
    transaction_manager.add_transaction("cash", None, "Bus", 2.50, "Transport")

    spending = report_manager.get_daily_spending(days=7)

    assert len(spending) == 7
    assert all(
        isinstance(day, str) and isinstance(amount, float) for day, amount in spending
    )
    # Today should have spending
    today_spending = spending[-1][1]  # Last day in the list
    assert today_spending == 6.00


def test_get_daily_spending_empty(report_manager):
    """Test getting daily spending with no transactions."""
    spending = report_manager.get_daily_spending(days=5)

    assert len(spending) == 5
    # All days should have 0 spending
    assert all(amount == 0.0 for _, amount in spending)


def test_get_daily_spending_custom_days(report_manager):
    """Test getting daily spending for custom number of days."""
    spending = report_manager.get_daily_spending(days=30)

    assert len(spending) == 30


def test_get_monthly_spending(report_manager, transaction_manager, sample_balances):
    """Test getting monthly spending breakdown."""
    # Add transactions for current month
    transaction_manager.add_transaction("cash", None, "Coffee", 10.00, "Food")
    transaction_manager.add_transaction("card", "Wise", "Groceries", 50.00, "Food")
    transaction_manager.add_transaction(
        "card", "ICICI", "Movie", 20.00, "Entertainment"
    )

    now = datetime.now()
    spending = report_manager.get_monthly_spending(now.year, now.month)

    assert isinstance(spending, dict)
    assert "cash" in spending
    assert spending["cash"] == 10.00
    assert spending["Wise"] == 50.00
    assert spending["ICICI"] == 20.00


def test_get_monthly_spending_empty(report_manager):
    """Test getting monthly spending with no transactions."""
    now = datetime.now()
    spending = report_manager.get_monthly_spending(now.year, now.month)

    assert isinstance(spending, dict)
    assert len(spending) == 0


def test_get_spending_by_category(report_manager, transaction_manager):
    """Test getting spending breakdown by category."""
    # Add transactions with categories
    transaction_manager.add_transaction("cash", None, "Coffee", 5.00, "Food")
    transaction_manager.add_transaction("cash", None, "Lunch", 15.00, "Food")
    transaction_manager.add_transaction("cash", None, "Bus", 3.00, "Transport")
    transaction_manager.add_transaction("cash", None, "Movie", 12.00, "Entertainment")

    now = datetime.now()
    spending = report_manager.get_spending_by_category(now.year, now.month)

    assert len(spending) >= 3
    # Check Food category
    food_spending = next((amount for cat, amount in spending if cat == "Food"), None)
    assert food_spending == 20.00
    # Check Transport category
    transport_spending = next(
        (amount for cat, amount in spending if cat == "Transport"), None
    )
    assert transport_spending == 3.00


def test_get_spending_by_category_uncategorized(report_manager, transaction_manager):
    """Test that uncategorized transactions are labeled correctly."""
    transaction_manager.add_transaction("cash", None, "Random", 10.00, None)

    now = datetime.now()
    spending = report_manager.get_spending_by_category(now.year, now.month)

    # Should have Uncategorized
    uncategorized = next(
        (amount for cat, amount in spending if cat == "Uncategorized"), None
    )
    assert uncategorized is not None
    assert uncategorized == 10.00


def test_get_spending_by_category_sorted(report_manager, transaction_manager):
    """Test that spending by category is sorted by amount descending."""
    transaction_manager.add_transaction("cash", None, "Small", 5.00, "A")
    transaction_manager.add_transaction("cash", None, "Large", 50.00, "B")
    transaction_manager.add_transaction("cash", None, "Medium", 20.00, "C")

    now = datetime.now()
    spending = report_manager.get_spending_by_category(now.year, now.month)

    amounts = [amount for _, amount in spending]
    assert amounts == sorted(amounts, reverse=True)


def test_get_spending_with_balance_percentage(
    report_manager, transaction_manager, sample_balances
):
    """Test getting spending with balance percentage."""
    # Add transactions
    transaction_manager.add_transaction("cash", None, "Coffee", 10.00, "Food")
    transaction_manager.add_transaction("card", "Wise", "Groceries", 50.00, "Food")

    now = datetime.now()
    spending = report_manager.get_spending_with_balance_percentage(now.year, now.month)

    assert len(spending) >= 2
    # Each entry should have: (source, amount_spent, current_balance, percentage)
    for source, amount_spent, current_balance, percentage in spending:
        assert isinstance(source, str)
        assert isinstance(amount_spent, float)
        assert isinstance(current_balance, float)
        assert isinstance(percentage, float) or percentage == float("inf")


def test_get_spending_with_balance_percentage_calculation(
    report_manager, transaction_manager, sample_balances
):
    """Test that balance percentage is calculated correctly."""
    # Cash balance is 100, add 50 spending = 50%
    transaction_manager.add_transaction("cash", None, "Purchase", 50.00, None)

    now = datetime.now()
    spending = report_manager.get_spending_with_balance_percentage(now.year, now.month)

    cash_data = next((data for data in spending if data[0] == "cash"), None)
    assert cash_data is not None
    source, amount_spent, current_balance, percentage = cash_data
    assert amount_spent == 50.00
    assert current_balance == 100.00
    assert percentage == 50.0


def test_get_spending_with_balance_percentage_zero_balance(
    report_manager, transaction_manager, balance_manager
):
    """Test spending percentage with zero balance."""
    # Set balance to 0 and add spending
    balance_manager.update_balance("Broke", 0.0)
    transaction_manager.add_transaction("card", "Broke", "Purchase", 10.00, None)

    now = datetime.now()
    spending = report_manager.get_spending_with_balance_percentage(now.year, now.month)

    broke_data = next((data for data in spending if data[0] == "Broke"), None)
    if broke_data:
        source, amount_spent, current_balance, percentage = broke_data
        assert percentage == float("inf")


def test_get_spending_with_balance_percentage_sorted(
    report_manager, transaction_manager, sample_balances
):
    """Test that results are sorted by amount spent descending."""
    transaction_manager.add_transaction("cash", None, "Small", 5.00, None)
    transaction_manager.add_transaction("card", "Wise", "Large", 100.00, None)
    transaction_manager.add_transaction("card", "ICICI", "Medium", 30.00, None)

    now = datetime.now()
    spending = report_manager.get_spending_with_balance_percentage(now.year, now.month)

    amounts = [amount for _, amount, _, _ in spending]
    assert amounts == sorted(amounts, reverse=True)
