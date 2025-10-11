"""Tests for CategoryManager."""

import pytest

from budget.domain.exceptions import ValidationError
from budget.domain.models import Category


def test_add_category(category_manager):
    """Test adding a new category."""
    result = category_manager.add_category("Food", "Food and groceries")

    assert result is True


def test_add_category_without_description(category_manager):
    """Test adding a category without description."""
    result = category_manager.add_category("Transport", "")

    assert result is True
    categories = category_manager.get_categories()
    transport = next((c for c in categories if c.name == "Transport"), None)
    assert transport is not None
    assert transport.description == ""


def test_add_category_duplicate_returns_false(category_manager, sample_categories):
    """Test that adding duplicate category returns False."""
    result = category_manager.add_category("Food", "Duplicate")

    assert result is False


def test_add_category_empty_name_raises_error(category_manager):
    """Test that empty category name raises ValidationError."""
    with pytest.raises(ValidationError, match="Category name cannot be empty"):
        category_manager.add_category("", "Description")


def test_add_category_whitespace_name_raises_error(category_manager):
    """Test that whitespace-only name raises ValidationError."""
    with pytest.raises(ValidationError, match="Category name cannot be empty"):
        category_manager.add_category("   ", "Description")


def test_load_categories(category_manager, sample_categories):
    """Test loading category names."""
    categories = category_manager.load_categories()

    assert len(categories) == len(sample_categories)
    assert all(isinstance(c, str) for c in categories)
    assert set(categories) == {c[0] for c in sample_categories}


def test_load_categories_empty(category_manager):
    """Test loading categories when none exist."""
    categories = category_manager.load_categories()

    assert len(categories) == 0


def test_get_categories(category_manager, sample_categories):
    """Test getting all categories with descriptions."""
    categories = category_manager.get_categories()

    assert len(categories) == len(sample_categories)
    assert all(isinstance(c, Category) for c in categories)
    assert all(
        hasattr(c, "id") and hasattr(c, "name") and hasattr(c, "description")
        for c in categories
    )


def test_get_categories_sorted(category_manager, sample_categories):
    """Test that categories are returned sorted by name."""
    categories = category_manager.get_categories()
    names = [c.name for c in categories]

    assert names == sorted(names)


def test_category_dict_access(category_manager, sample_categories):
    """Test that returned Category objects support dict access."""
    categories = category_manager.get_categories()
    category = categories[0]

    assert category["id"] is not None
    assert category["name"] in [c[0] for c in sample_categories]
    assert category["description"] is not None
