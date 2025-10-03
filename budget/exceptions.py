class BudgetError(Exception):
    """Base exception for budget-related errors"""

    pass


class DatabaseError(BudgetError):
    """Database operation errors"""

    pass


class ValidationError(BudgetError):
    """Data validation errors"""

    pass
