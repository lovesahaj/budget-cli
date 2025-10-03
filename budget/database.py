from contextlib import contextmanager
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from budget.exceptions import DatabaseError
from budget.models import Base


def get_engine(db_name: str = 'budget.db'):
    db_path = os.environ.get("BUDGET_DB_NAME", db_name)
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine):
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        raise DatabaseError(f"Failed to initialize database: {e}")

@contextmanager
def get_db_session(engine):
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