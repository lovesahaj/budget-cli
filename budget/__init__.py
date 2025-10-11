"""Budget Tracker - Personal finance management application.

A modular gRPC-based application for tracking daily transactions, account balances,
spending limits, and financial analytics.

## Module Organization

The application is organized into four main layers:

### Domain Layer (`budget.domain`)
Core business entities and domain-specific exceptions.
- Models: Card, Category, Transaction, Balance, SpendingLimit
- Exceptions: BudgetError, DatabaseError, ValidationError

### Infrastructure Layer (`budget.infrastructure`)
Technical infrastructure and external dependencies.
- Database: Connection pooling, session management
- Configuration: Environment-based configuration
- Health: Health checking utilities

### Core Layer (`budget.core`)
Business logic and application services.
- Managers: Transaction, Card, Category, Balance, Limit, Report, Export
- BudgetManager: Main facade for all operations

### Server Layer (`budget.server`)
gRPC server implementation and middleware.
- gRPC Servicers: Transaction and Budget services
- Interceptors: Logging, error handling, metrics
- Protocol Buffers: Service definitions

## Quick Start

```python
from budget.core import BudgetManager
from budget.server import serve

# Using BudgetManager directly
with BudgetManager() as bm:
    bm.add_transaction("card", "Visa", "Coffee", 5.50, "Food")
    transactions = bm.get_recent_transactions(10)

# Starting the gRPC server
serve(port=50051)
```

## Public API

This module re-exports commonly used classes and functions for convenience.
"""

# Core
from budget.core import BudgetManager

# Domain
from budget.domain import (
    Balance,
    BudgetError,
    Card,  # Models; Exceptions
    Category,
    DatabaseError,
    SpendingLimit,
    Transaction,
    ValidationError,
)

# Infrastructure
from budget.infrastructure import (
    Config,  # Configuration; Database; Health
    DatabaseConfig,
    LoggingConfig,
    ServerConfig,
    get_config,
    get_db_session,
    get_engine,
    get_health_status,
    init_db,
)

# Server
from budget.server import get_metrics, serve

__version__ = "0.1.0"

__all__ = [
    # Domain Models
    "Card",
    "Category",
    "Transaction",
    "Balance",
    "SpendingLimit",
    # Exceptions
    "BudgetError",
    "DatabaseError",
    "ValidationError",
    # Configuration
    "Config",
    "DatabaseConfig",
    "ServerConfig",
    "LoggingConfig",
    "get_config",
    # Database
    "get_engine",
    "init_db",
    "get_db_session",
    # Health
    "get_health_status",
    # Core
    "BudgetManager",
    # Server
    "serve",
    "get_metrics",
    # Version
    "__version__",
]
