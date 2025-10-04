"""Database configuration and initialization module.

This module provides functions for creating and managing SQLAlchemy database connections,
including engine creation, database initialization, and session management.
"""

from contextlib import contextmanager
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from budget.exceptions import DatabaseError
from budget.models import Base


def get_engine(db_name: str = 'budget.db'):
    """Create and return a SQLAlchemy engine for the budget database.

    Args:
        db_name: Name of the SQLite database file. Defaults to 'budget.db'.
                Can be overridden by the BUDGET_DB_NAME environment variable.

    Returns:
        sqlalchemy.engine.Engine: Configured SQLAlchemy engine instance.

    Example:
        >>> engine = get_engine("my_budget.db")
        >>> # Or use environment variable
        >>> os.environ["BUDGET_DB_NAME"] = "production.db"
        >>> engine = get_engine()
    """
    db_path = os.environ.get("BUDGET_DB_NAME", db_name)
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine):
    """Initialize the database by creating all tables defined in models.

    Args:
        engine: SQLAlchemy engine instance to use for initialization.

    Raises:
        DatabaseError: If database initialization fails.

    Note:
        This function is idempotent - calling it multiple times will not
        recreate existing tables.

    Example:
        >>> engine = get_engine()
        >>> init_db(engine)
    """
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        raise DatabaseError(f"Failed to initialize database: {e}")

@contextmanager
def get_db_session(engine):
    """Context manager for database sessions with automatic transaction handling.

    Provides a SQLAlchemy session with automatic commit on success and rollback
    on exceptions. The session is always closed when exiting the context.

    Args:
        engine: SQLAlchemy engine instance to create the session from.

    Yields:
        sqlalchemy.orm.Session: Database session instance.

    Raises:
        Exception: Re-raises any exception that occurs within the context,
                  after performing a rollback.

    Example:
        >>> engine = get_engine()
        >>> with get_db_session(engine) as session:
        ...     transaction = Transaction(description="Coffee", amount=5.0)
        ...     session.add(transaction)
        ...     # Automatically commits on successful exit
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()