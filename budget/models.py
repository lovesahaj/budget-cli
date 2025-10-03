from sqlalchemy import (create_engine, Column, Integer, String, Float, DateTime, MetaData, Table)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class DictAccessMixin:
    """Mixin to add dict-like access to SQLAlchemy models."""
    def __getitem__(self, key):
        return getattr(self, key)

class Card(Base, DictAccessMixin):
    __tablename__ = 'cards'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

class Category(Base, DictAccessMixin):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)

class Transaction(Base, DictAccessMixin):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, nullable=False)
    card = Column(String)
    category = Column(String)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=func.now())

class Balance(Base, DictAccessMixin):
    __tablename__ = 'balances'
    type = Column(String, unique=True, nullable=False, primary_key=True)
    amount = Column(Float, nullable=False, default=0.0)

class SpendingLimit(Base, DictAccessMixin):
    __tablename__ = 'spending_limits'
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String)
    source = Column(String)
    limit_amount = Column(Float, nullable=False)
    period = Column(String, nullable=False)