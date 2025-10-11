"""Domain layer - Business models and domain exceptions.

This module contains the core domain models (entities) and domain-specific
exceptions used throughout the application.
"""

from budget.domain.exceptions import BudgetError, DatabaseError, ValidationError
from budget.domain.models import (
    Balance,
    Base,
    Card,
    Category,
    DictAccessMixin,
    SpendingLimit,
    Transaction,
)

__all__ = [
    # Models
    "Base",
    "Card",
    "Category",
    "Transaction",
    "Balance",
    "SpendingLimit",
    "DictAccessMixin",
    # Exceptions
    "BudgetError",
    "DatabaseError",
    "ValidationError",
]
