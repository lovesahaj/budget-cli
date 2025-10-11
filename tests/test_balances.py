"""Tests for BalanceManager."""

import pytest

from budget.domain.exceptions import ValidationError


def test_get_balance_existing(balance_manager, sample_balances):
    """Test getting an existing balance."""
    balance = balance_manager.get_balance("cash")

    assert balance == 100.00


def test_get_balance_nonexistent(balance_manager):
    """Test getting a nonexistent balance returns 0."""
    balance = balance_manager.get_balance("nonexistent")

    assert balance == 0.0


def test_update_balance(balance_manager):
    """Test updating a balance."""
    balance_manager.update_balance("cash", 150.00)
    balance = balance_manager.get_balance("cash")

    assert balance == 150.00


def test_update_balance_new_account(balance_manager):
    """Test updating a balance for a new account."""
    balance_manager.update_balance("NewCard", 250.00)
    balance = balance_manager.get_balance("NewCard")

    assert balance == 250.00


def test_update_balance_to_zero(balance_manager, sample_balances):
    """Test updating a balance to zero."""
    balance_manager.update_balance("cash", 0.0)
    balance = balance_manager.get_balance("cash")

    assert balance == 0.0


def test_update_balance_negative(balance_manager):
    """Test updating to negative balance (allowed for overdraft)."""
    balance_manager.update_balance("cash", -50.00)
    balance = balance_manager.get_balance("cash")

    assert balance == -50.00


def test_update_balance_invalid_type_raises_error(balance_manager):
    """Test that updating with invalid type raises ValidationError."""
    with pytest.raises(ValidationError, match="Amount must be a number"):
        balance_manager.update_balance("cash", "invalid")


def test_get_all_balances(balance_manager, sample_balances):
    """Test getting all balances."""
    balances = balance_manager.get_all_balances()

    assert isinstance(balances, dict)
    assert len(balances) == len(sample_balances)
    assert balances["cash"] == 100.00
    assert balances["Wise"] == 500.00
    assert balances["ICICI"] == 1000.00


def test_get_all_balances_default(balance_manager):
    """Test getting all balances when none are explicitly set."""
    balances = balance_manager.get_all_balances()

    assert isinstance(balances, dict)
    assert len(balances) == 3
    assert balances["cash"] == 0.0
    assert balances["Wise"] == 0.0
    assert balances["ICICI"] == 0.0


def test_get_all_balances_sorted(balance_manager, sample_balances):
    """Test that balances are returned sorted by type."""
    balances = balance_manager.get_all_balances()
    keys = list(balances.keys())

    assert keys == sorted(keys)


def test_balance_persistence(balance_manager):
    """Test that balance changes persist."""
    balance_manager.update_balance("test", 100.00)
    balance_manager.update_balance("test", 200.00)
    balance = balance_manager.get_balance("test")

    assert balance == 200.00


def test_multiple_balance_updates(balance_manager):
    """Test multiple balance updates."""
    balance_manager.update_balance("cash", 100.00)
    balance_manager.update_balance("Wise", 200.00)
    balance_manager.update_balance("ICICI", 300.00)

    assert balance_manager.get_balance("cash") == 100.00
    assert balance_manager.get_balance("Wise") == 200.00
    assert balance_manager.get_balance("ICICI") == 300.00
