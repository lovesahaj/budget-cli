"""Transaction category management module.

This module provides functionality for managing transaction categories,
including loading, creating, and retrieving categories with their descriptions.
"""

from typing import List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from budget.exceptions import DatabaseError, ValidationError
from budget.models import Category


class CategoryManager:
    """Manages transaction categories for budget classification.

    The CategoryManager handles all operations related to transaction categories,
    including loading, adding, and retrieving categories.

    Attributes:
        session (Session): SQLAlchemy database session.
        categories (List[str]): List of category names currently loaded in memory.

    Example:
        >>> with BudgetManager() as bm:
        ...     cat_manager = CategoryManager(bm.session)
        ...     categories = cat_manager.load_categories()
        ...     cat_manager.add_category("Food", "Groceries and dining")
    """

    def __init__(self, session: Session):
        """Initialize the CategoryManager.

        Args:
            session: SQLAlchemy database session for database operations.
        """
        self.session = session
        self.categories: List[str] = []

    def load_categories(self) -> List[str]:
        """Load all category names from database.

        Returns:
            List[str]: List of category names sorted alphabetically.

        Raises:
            DatabaseError: If loading categories fails.

        Example:
            >>> categories = cat_manager.load_categories()
            >>> print(categories)  # ['Entertainment', 'Food', 'Transport']
        """
        try:
            categories: List[str] = [
                category.name
                for category in self.session.query(Category)
                .order_by(Category.name)
                .all()
            ]
            self.categories = categories
            return self.categories
        except Exception as e:
            raise DatabaseError(f"Failed to load categories: {e}")

    def add_category(self, name: str, description: str = "") -> bool:
        """Add a new transaction category.

        Creates a new category with an optional description. The category name
        is trimmed of whitespace and checked for uniqueness.

        Args:
            name: Name of the category to add (will be trimmed).
            description: Optional description of the category. Defaults to "".

        Returns:
            bool: True if the category was added successfully, False if a
                 category with that name already exists.

        Raises:
            ValidationError: If the category name is empty or whitespace-only.
            DatabaseError: If the database operation fails.

        Example:
            >>> success = cat_manager.add_category("Food", "Dining and groceries")
            >>> if success:
            ...     print("Category added")
        """
        try:
            if not name or not name.strip():
                raise ValidationError("Category name cannot be empty")

            new_category = Category(name=name.strip(), description=description.strip())
            self.session.add(new_category)
            self.session.commit()
            self.categories.append(name.strip())
            self.categories.sort()
            return True
        except IntegrityError:
            self.session.rollback()
            return False
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to add category: {e}")

    def get_categories(self) -> List[Category]:
        """Get all categories with their descriptions.

        Returns:
            List[Category]: List of Category model objects sorted by name,
                           including both names and descriptions.

        Raises:
            DatabaseError: If retrieving categories fails.

        Example:
            >>> categories = cat_manager.get_categories()
            >>> for cat in categories:
            ...     print(f"{cat.name}: {cat.description}")
        """
        try:
            return self.session.query(Category).order_by(Category.name).all()
        except Exception as e:
            raise DatabaseError(f"Failed to get categories: {e}")
