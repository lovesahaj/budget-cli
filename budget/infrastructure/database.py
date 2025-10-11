"""Database configuration and initialization module.

This module provides functions for creating and managing SQLAlchemy database connections,
including engine creation, database initialization, and session management with connection pooling.
"""

import os
from contextlib import contextmanager
from typing import Optional

from loguru import logger
from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker

from budget.domain.exceptions import DatabaseError
from budget.domain.models import Base
from budget.infrastructure.config import DatabaseConfig, get_config

# Global session factory
_session_factory: Optional[scoped_session] = None
_engine: Optional[Engine] = None


def get_engine(
    db_name: Optional[str] = None, config: Optional[DatabaseConfig] = None
) -> Engine:
    """Create and return a SQLAlchemy engine for the budget database.

    This function creates a SQLAlchemy engine with connection pooling configured
    for web server usage. The engine is cached globally for reuse.

    Args:
        db_name: Name of the SQLite database file. If None, uses configuration.
        config: Database configuration. If None, uses global configuration.

    Returns:
        sqlalchemy.engine.Engine: Configured SQLAlchemy engine instance.

    Example:
        >>> engine = get_engine("my_budget.db")
        >>> # Or use configuration
        >>> config = DatabaseConfig(db_name="production.db", pool_size=20)
        >>> engine = get_engine(config=config)
    """
    global _engine

    if _engine is not None:
        return _engine

    if config is None:
        config = get_config().database

    if db_name is not None:
        db_path = db_name
    else:
        db_path = os.environ.get("BUDGET_DB_NAME", config.db_name)

    # Configure connection pooling for SQLite
    # SQLite requires special handling for connection pooling
    _engine = create_engine(
        f"sqlite:///{db_path}",
        poolclass=pool.StaticPool if config.pool_size == 1 else pool.QueuePool,
        pool_size=config.pool_size,
        pool_recycle=config.pool_recycle,
        echo=config.echo,
        connect_args={"check_same_thread": False},  # Allow multi-threaded access
    )

    # Configure SQLite for better concurrency
    @event.listens_for(_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite pragmas for better performance and concurrency."""
        cursor = dbapi_conn.cursor()
        cursor.execute(
            "PRAGMA journal_mode=WAL"
        )  # Write-Ahead Logging for better concurrency
        cursor.execute("PRAGMA synchronous=NORMAL")  # Faster but still safe
        cursor.execute("PRAGMA busy_timeout=5000")  # 5 second timeout for locks
        cursor.close()

    logger.info("Database engine created: {} (pool_size={})", db_path, config.pool_size)
    return _engine


def init_db(engine: Optional[Engine] = None) -> None:
    """Initialize the database by creating all tables defined in models.

    Args:
        engine: SQLAlchemy engine instance to use for initialization.
               If None, uses the global engine.

    Raises:
        DatabaseError: If database initialization fails.

    Note:
        This function is idempotent - calling it multiple times will not
        recreate existing tables.

    Example:
        >>> engine = get_engine()
        >>> init_db(engine)
        >>> # Or use global engine
        >>> init_db()
    """
    if engine is None:
        engine = get_engine()

    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database: {}", e)
        raise DatabaseError(f"Failed to initialize database: {e}")


def get_session_factory(engine: Optional[Engine] = None) -> scoped_session:
    """Get or create the global scoped session factory.

    This creates a thread-safe session factory that can be used across
    the application, particularly useful for web server contexts.

    Args:
        engine: SQLAlchemy engine instance. If None, uses global engine.

    Returns:
        scoped_session: Thread-safe session factory.

    Example:
        >>> SessionFactory = get_session_factory()
        >>> session = SessionFactory()
        >>> # Use session...
        >>> SessionFactory.remove()  # Clean up thread-local session
    """
    global _session_factory

    if _session_factory is not None:
        return _session_factory

    if engine is None:
        engine = get_engine()

    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    _session_factory = scoped_session(session_factory)
    logger.info("Session factory created")
    return _session_factory


@contextmanager
def get_db_session(engine: Optional[Engine] = None):
    """Context manager for database sessions with automatic transaction handling.

    Provides a SQLAlchemy session with automatic commit on success and rollback
    on exceptions. The session is always closed when exiting the context.

    This is the recommended way to get a database session for request handling
    in a web server context.

    Args:
        engine: SQLAlchemy engine instance to create the session from.
               If None, uses the scoped session factory.

    Yields:
        sqlalchemy.orm.Session: Database session instance.

    Raises:
        Exception: Re-raises any exception that occurs within the context,
                  after performing a rollback.

    Example:
        >>> with get_db_session() as session:
        ...     transaction = Transaction(description="Coffee", amount=5.0)
        ...     session.add(transaction)
        ...     # Automatically commits on successful exit
    """
    if engine is not None:
        # Legacy mode: create a new session from the provided engine
        Session = sessionmaker(bind=engine)
        session = Session()
    else:
        # Use scoped session factory for better thread safety
        SessionFactory = get_session_factory()
        session = SessionFactory()

    try:
        yield session
        session.commit()
        logger.debug("Database session committed successfully")
    except Exception as e:
        session.rollback()
        logger.error("Database session rolled back due to error: {}", e)
        raise
    finally:
        if engine is None:
            # Remove thread-local session
            SessionFactory.remove()
        else:
            session.close()


def close_db():
    """Close the database engine and clean up resources.

    Should be called during application shutdown to properly clean up
    database connections.
    """
    global _engine, _session_factory

    if _session_factory is not None:
        _session_factory.remove()
        _session_factory = None
        logger.info("Session factory closed")

    if _engine is not None:
        _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")
