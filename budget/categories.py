from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from budget.exceptions import DatabaseError, ValidationError
from budget.models import Category

class CategoryManager:
    def __init__(self, session: Session):
        self.session = session
        self.categories: List[str] = []

    def load_categories(self) -> List[str]:
        """Load categories from database"""
        try:
            self.categories = [category.name for category in self.session.query(Category).order_by(Category.name).all()]
            return self.categories
        except Exception as e:
            raise DatabaseError(f"Failed to load categories: {e}")

    def add_category(self, name: str, description: str = "") -> bool:
        """Add a new transaction category"""
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
        """Get all categories with descriptions"""
        try:
            return self.session.query(Category).order_by(Category.name).all()
        except Exception as e:
            raise DatabaseError(f"Failed to get categories: {e}")