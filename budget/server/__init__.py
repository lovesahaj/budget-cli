"""Server layer - gRPC server implementation and middleware.

This module contains the gRPC server implementation, including servicers,
interceptors, and protocol buffer definitions.
"""

from budget.server.grpc_server import (
    BudgetServiceServicer,
    TransactionServiceServicer,
    get_metrics,
    serve,
)
from budget.server.interceptors import (
    ErrorHandlingInterceptor,
    LoggingInterceptor,
    MetricsInterceptor,
)

__all__ = [
    # Server
    "serve",
    "get_metrics",
    # Servicers
    "TransactionServiceServicer",
    "BudgetServiceServicer",
    # Interceptors
    "LoggingInterceptor",
    "ErrorHandlingInterceptor",
    "MetricsInterceptor",
]
