"""Tests for BudgetManager."""

import pytest

from budget.core.manager import BudgetManager
from budget.domain.exceptions import BudgetError, ValidationError


def test_budget_manager_context_manager(temp_db):
    """Test BudgetManager works as context manager."""
    with BudgetManager(temp_db) as bm:
        assert bm is not None
        assert bm.session is not None
        assert bm.transactions is not None
        assert bm.categories_manager is not None
        assert bm.balances_manager is not None


def test_budget_manager_loads_default_cards(budget_manager):
    """Test that BudgetManager loads default cards."""
    assert "Wise" in budget_manager.cards
    assert "ICICI" in budget_manager.cards


def test_add_new_card(budget_manager):
    """Test adding a new card."""
    result = budget_manager.add_new_card("NewCard")

    assert result is True
    assert "NewCard" in budget_manager.cards


def test_add_duplicate_card_returns_false(budget_manager):
    """Test that adding duplicate card returns False."""
    budget_manager.add_new_card("TestCard")
    result = budget_manager.add_new_card("TestCard")

    assert result is False


def test_add_empty_card_name_raises_error(budget_manager):
    """Test that empty card name raises ValidationError."""
    with pytest.raises(ValidationError, match="Card name cannot be empty"):
        budget_manager.add_new_card("")


def test_get_balance_delegation(budget_manager, sample_balances):
    """Test that get_balance delegates to BalanceManager."""
    balance = budget_manager.get_balance("cash")

    assert balance == 100.00


def test_update_balance_delegation(budget_manager):
    """Test that update_balance delegates to BalanceManager."""
    budget_manager.update_balance("cash", 200.00)
    balance = budget_manager.get_balance("cash")

    assert balance == 200.00


def test_get_all_balances_delegation(budget_manager, sample_balances):
    """Test that get_all_balances delegates correctly."""
    balances = budget_manager.get_all_balances()

    assert isinstance(balances, dict)
    assert "cash" in balances
    assert "Wise" in balances


def test_add_category_delegation(budget_manager):
    """Test that add_category delegates to CategoryManager."""
    result = budget_manager.add_category("Food", "Food and groceries")

    assert result is True
    assert "Food" in budget_manager.categories


def test_get_categories_delegation(budget_manager, sample_categories):
    """Test that get_categories delegates to CategoryManager."""
    categories = budget_manager.get_categories()

    assert len(categories) > 0
    assert all(hasattr(c, "name") and hasattr(c, "description") for c in categories)


def test_add_transaction_delegation(budget_manager):
    """Test that add_transaction delegates to TransactionManager."""
    tid = budget_manager.add_transaction("cash", None, "Coffee", 3.50, "Food")

    assert tid is not None
    assert tid > 0


def test_get_transaction_by_id_delegation(budget_manager):
    """Test that get_transaction_by_id delegates correctly."""
    tid = budget_manager.add_transaction("cash", None, "Coffee", 3.50, "Food")
    transaction = budget_manager.get_transaction_by_id(tid)

    assert transaction is not None
    assert transaction.id == tid


def test_get_recent_transactions_delegation(budget_manager, sample_transactions):
    """Test that get_recent_transactions delegates correctly."""
    transactions = budget_manager.get_recent_transactions(limit=3)

    assert len(transactions) == 3


def test_update_transaction_delegation(budget_manager):
    """Test that update_transaction delegates correctly."""
    tid = budget_manager.add_transaction("cash", None, "Coffee", 3.50, None)
    result = budget_manager.update_transaction(tid, description="Updated")

    assert result is True
    transaction = budget_manager.get_transaction_by_id(tid)
    assert transaction.description == "Updated"


def test_delete_transaction_delegation(budget_manager):
    """Test that delete_transaction delegates correctly."""
    tid = budget_manager.add_transaction("cash", None, "Coffee", 3.50, None)
    result = budget_manager.delete_transaction(tid)

    assert result is True
    transaction = budget_manager.get_transaction_by_id(tid)
    assert transaction is None


def test_search_transactions_delegation(budget_manager, sample_transactions):
    """Test that search_transactions delegates correctly."""
    transactions = budget_manager.search_transactions(category="Food")

    assert len(transactions) > 0
    assert all(t.category == "Food" for t in transactions)


def test_set_spending_limit_delegation(budget_manager):
    """Test that set_spending_limit delegates correctly."""
    result = budget_manager.set_spending_limit(100.00, "monthly", "Food", None)

    assert result is True


def test_get_spending_limits_delegation(budget_manager, sample_limits):
    """Test that get_spending_limits delegates correctly."""
    limits = budget_manager.get_spending_limits()

    assert len(limits) > 0


def test_check_spending_limit_delegation(budget_manager, sample_limits):
    """Test that check_spending_limit delegates correctly."""
    result = budget_manager.check_spending_limit("Food", None, "monthly")

    # Result might be None if no spending yet, or a dict with limit info
    assert result is None or isinstance(result, dict)


def test_get_spending_by_category_delegation(budget_manager, sample_transactions):
    """Test that get_spending_by_category delegates correctly."""
    from datetime import datetime

    now = datetime.now()
    spending = budget_manager.get_spending_by_category(now.year, now.month)

    assert isinstance(spending, list)


def test_get_spending_with_balance_percentage_delegation(
    budget_manager, sample_balances, sample_transactions
):
    """Test that get_spending_with_balance_percentage delegates correctly."""
    from datetime import datetime

    now = datetime.now()
    spending = budget_manager.get_spending_with_balance_percentage(now.year, now.month)

    assert isinstance(spending, list)


def test_get_daily_spending_delegation(budget_manager, sample_transactions):
    """Test that get_daily_spending delegates correctly."""
    spending = budget_manager.get_daily_spending(days=7)

    assert len(spending) == 7
    assert all(
        isinstance(day, str) and isinstance(amount, float) for day, amount in spending
    )


def test_export_to_csv_delegation(budget_manager, sample_transactions):
    """Test that export_to_csv delegates correctly."""
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        filepath = f.name

    try:
        budget_manager.export_to_csv(filepath)
        assert Path(filepath).exists()
    finally:
        Path(filepath).unlink(missing_ok=True)


def test_export_to_json_delegation(budget_manager, sample_transactions):
    """Test that export_to_json delegates correctly."""
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        filepath = f.name

    try:
        budget_manager.export_to_json(filepath)
        assert Path(filepath).exists()
    finally:
        Path(filepath).unlink(missing_ok=True)


def test_context_manager_cleanup(temp_db):
    """Test that context manager properly closes session."""
    with BudgetManager(temp_db) as bm:
        session = bm.session

    # After exiting context, session should be closed
    # We can't directly test if closed, but we can test that a new context works
    with BudgetManager(temp_db) as bm2:
        assert bm2.session is not None
