"""Custom exception classes for the budget application.

This module defines the exception hierarchy used throughout the budget tracker
to provide clear, specific error handling for different failure scenarios.
"""


class BudgetError(Exception):
    """Base exception for all budget-related errors.

    This is the root exception class that all other budget exceptions inherit from.
    Catching this exception will catch all budget-specific errors.

    Example:
        >>> try:
        ...     # budget operations
        ...     pass
        ... except BudgetError as e:
        ...     print(f"Budget error occurred: {e}")
    """

    pass


class DatabaseError(BudgetError):
    """Exception raised for database operation failures.

    Raised when database operations such as queries, inserts, updates, or
    deletes fail due to connection issues, integrity constraints, or other
    database-related problems.

    Example:
        >>> try:
        ...     session.query(Transaction).all()
        ... except DatabaseError as e:
        ...     print(f"Database operation failed: {e}")
    """

    pass


class ValidationError(BudgetError):
    """Exception raised for data validation failures.

    Raised when user input or data fails validation checks, such as:
    - Empty required fields
    - Invalid data types
    - Out-of-range values
    - Invalid format

    Example:
        >>> try:
        ...     if amount <= 0:
        ...         raise ValidationError("Amount must be positive")
        ... except ValidationError as e:
        ...     print(f"Invalid input: {e}")
    """

    pass
