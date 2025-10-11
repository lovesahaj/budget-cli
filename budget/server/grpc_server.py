"""gRPC server implementation for budget management.

This module provides the gRPC server implementations for transaction management
and budget viewing services, optimized for web server usage with proper resource
management, connection pooling, and graceful shutdown.
"""

import signal
import sys
from concurrent import futures
from typing import Optional

import grpc
from loguru import logger

from budget.core.manager import BudgetManager
from budget.domain.exceptions import DatabaseError, ValidationError
from budget.infrastructure import database
from budget.infrastructure.config import Config, get_config
from budget.infrastructure.health import get_health_status
from budget.server.interceptors import (
    ErrorHandlingInterceptor,
    LoggingInterceptor,
    MetricsInterceptor,
)
from budget.server.proto import budget_pb2, budget_pb2_grpc

# Global metrics interceptor for monitoring
_metrics_interceptor: Optional[MetricsInterceptor] = None


class TransactionServiceServicer(budget_pb2_grpc.TransactionServiceServicer):
    """gRPC servicer for transaction management operations."""

    def __init__(self, db_name: str = "budget.db"):
        """Initialize the transaction service.

        Args:
            db_name: Name of the database file.
        """
        self.db_name = db_name
        logger.debug(f"TransactionServiceServicer initialized with database: {db_name}")

    def AddTransaction(self, request, context):
        """Add a new transaction.

        Args:
            request: AddTransactionRequest containing transaction details.
            context: gRPC context.

        Returns:
            TransactionResponse with the created transaction.
        """
        logger.debug(
            f"AddTransaction called with type={request.type}, amount={request.amount}, description={request.description}"
        )
        try:
            with BudgetManager(self.db_name) as bm:
                txn_id = bm.add_transaction(
                    t_type=request.type,
                    card=request.card if request.card else None,
                    description=request.description,
                    amount=request.amount,
                    category=request.category if request.category else None,
                )

                txn = bm.get_transaction_by_id(txn_id)
                logger.success(
                    f"Transaction added successfully: ID={txn_id}, amount={request.amount}"
                )
                return budget_pb2.TransactionResponse(
                    success=True,
                    message="Transaction added successfully",
                    transaction=self._transaction_to_proto(txn),
                )
        except ValidationError as e:
            logger.warning(f"Validation error adding transaction: {e}")
            return budget_pb2.TransactionResponse(
                success=False, message=str(e), transaction=None
            )
        except DatabaseError as e:
            logger.error(f"Database error adding transaction: {e}")
            return budget_pb2.TransactionResponse(
                success=False, message=str(e), transaction=None
            )
        except Exception as e:
            logger.exception(f"Unexpected error adding transaction: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.TransactionResponse(
                success=False, message=f"Internal error: {e}", transaction=None
            )

    def UpdateTransaction(self, request, context):
        """Update an existing transaction.

        Args:
            request: UpdateTransactionRequest with fields to update.
            context: gRPC context.

        Returns:
            UpdateTransactionResponse indicating success.
        """
        logger.debug(
            f"UpdateTransaction called for transaction_id={request.transaction_id}"
        )
        try:
            with BudgetManager(self.db_name) as bm:
                # Build kwargs for only the fields that are set
                kwargs = {"transaction_id": request.transaction_id}

                if request.HasField("type"):
                    kwargs["t_type"] = request.type
                if request.HasField("card"):
                    kwargs["card"] = request.card
                if request.HasField("description"):
                    kwargs["description"] = request.description
                if request.HasField("amount"):
                    kwargs["amount"] = request.amount
                if request.HasField("category"):
                    kwargs["category"] = request.category

                logger.debug(f"Updating transaction with fields: {list(kwargs.keys())}")
                success = bm.update_transaction(**kwargs)

                if success:
                    logger.success(
                        f"Transaction {request.transaction_id} updated successfully"
                    )
                    return budget_pb2.UpdateTransactionResponse(
                        success=True, message="Transaction updated successfully"
                    )
                else:
                    logger.warning(
                        f"Transaction {request.transaction_id} not found for update"
                    )
                    return budget_pb2.UpdateTransactionResponse(
                        success=False, message="Transaction not found"
                    )
        except ValidationError as e:
            logger.warning(
                f"Validation error updating transaction {request.transaction_id}: {e}"
            )
            return budget_pb2.UpdateTransactionResponse(success=False, message=str(e))
        except DatabaseError as e:
            logger.error(
                f"Database error updating transaction {request.transaction_id}: {e}"
            )
            return budget_pb2.UpdateTransactionResponse(success=False, message=str(e))
        except Exception as e:
            logger.exception(
                f"Unexpected error updating transaction {request.transaction_id}: {e}"
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.UpdateTransactionResponse(
                success=False, message=f"Internal error: {e}"
            )

    def DeleteTransaction(self, request, context):
        """Delete a transaction.

        Args:
            request: DeleteTransactionRequest with transaction ID.
            context: gRPC context.

        Returns:
            DeleteTransactionResponse indicating success.
        """
        logger.debug(
            f"DeleteTransaction called for transaction_id={request.transaction_id}"
        )
        try:
            with BudgetManager(self.db_name) as bm:
                success = bm.delete_transaction(request.transaction_id)

                if success:
                    logger.success(
                        f"Transaction {request.transaction_id} deleted successfully"
                    )
                    return budget_pb2.DeleteTransactionResponse(
                        success=True, message="Transaction deleted successfully"
                    )
                else:
                    logger.warning(
                        f"Transaction {request.transaction_id} not found for deletion"
                    )
                    return budget_pb2.DeleteTransactionResponse(
                        success=False, message="Transaction not found"
                    )
        except DatabaseError as e:
            logger.error(
                f"Database error deleting transaction {request.transaction_id}: {e}"
            )
            return budget_pb2.DeleteTransactionResponse(success=False, message=str(e))
        except Exception as e:
            logger.exception(
                f"Unexpected error deleting transaction {request.transaction_id}: {e}"
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.DeleteTransactionResponse(
                success=False, message=f"Internal error: {e}"
            )

    def GetTransaction(self, request, context):
        """Get a transaction by ID.

        Args:
            request: GetTransactionRequest with transaction ID.
            context: gRPC context.

        Returns:
            TransactionResponse with the transaction.
        """
        logger.debug(
            f"GetTransaction called for transaction_id={request.transaction_id}"
        )
        try:
            with BudgetManager(self.db_name) as bm:
                txn = bm.get_transaction_by_id(request.transaction_id)

                if txn:
                    logger.debug(f"Transaction {request.transaction_id} found")
                    return budget_pb2.TransactionResponse(
                        success=True,
                        message="Transaction found",
                        transaction=self._transaction_to_proto(txn),
                    )
                else:
                    logger.warning(f"Transaction {request.transaction_id} not found")
                    return budget_pb2.TransactionResponse(
                        success=False, message="Transaction not found", transaction=None
                    )
        except DatabaseError as e:
            logger.error(
                f"Database error getting transaction {request.transaction_id}: {e}"
            )
            return budget_pb2.TransactionResponse(
                success=False, message=str(e), transaction=None
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error getting transaction {request.transaction_id}: {e}"
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.TransactionResponse(
                success=False, message=f"Internal error: {e}", transaction=None
            )

    def GetRecentTransactions(self, request, context):
        """Get recent transactions.

        Args:
            request: GetRecentTransactionsRequest with limit.
            context: gRPC context.

        Returns:
            TransactionListResponse with recent transactions.
        """
        limit = request.limit if request.limit > 0 else 10
        logger.debug(f"GetRecentTransactions called with limit={limit}")
        try:
            with BudgetManager(self.db_name) as bm:
                txns = bm.get_recent_transactions(limit)
                logger.info(f"Retrieved {len(txns)} recent transactions")

                return budget_pb2.TransactionListResponse(
                    success=True,
                    message=f"Found {len(txns)} transactions",
                    transactions=[self._transaction_to_proto(t) for t in txns],
                )
        except DatabaseError as e:
            logger.error(f"Database error getting recent transactions: {e}")
            return budget_pb2.TransactionListResponse(
                success=False, message=str(e), transactions=[]
            )
        except Exception as e:
            logger.exception(f"Unexpected error getting recent transactions: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.TransactionListResponse(
                success=False, message=f"Internal error: {e}", transactions=[]
            )

    def SearchTransactions(self, request, context):
        """Search transactions with filters.

        Args:
            request: SearchTransactionsRequest with filter criteria.
            context: gRPC context.

        Returns:
            TransactionListResponse with matching transactions.
        """
        logger.debug(f"SearchTransactions called with filters")
        try:
            with BudgetManager(self.db_name) as bm:
                kwargs = {}

                if request.query:
                    kwargs["query"] = request.query
                if request.category:
                    kwargs["category"] = request.category
                if request.card:
                    kwargs["card"] = request.card
                if request.start_date:
                    kwargs["start_date"] = request.start_date
                if request.end_date:
                    kwargs["end_date"] = request.end_date
                if request.HasField("min_amount"):
                    kwargs["min_amount"] = request.min_amount
                if request.HasField("max_amount"):
                    kwargs["max_amount"] = request.max_amount

                logger.debug(f"Search parameters: {kwargs}")
                txns = bm.search_transactions(**kwargs)
                logger.info(f"Search found {len(txns)} matching transactions")

                return budget_pb2.TransactionListResponse(
                    success=True,
                    message=f"Found {len(txns)} matching transactions",
                    transactions=[self._transaction_to_proto(t) for t in txns],
                )
        except DatabaseError as e:
            logger.error(f"Database error searching transactions: {e}")
            return budget_pb2.TransactionListResponse(
                success=False, message=str(e), transactions=[]
            )
        except Exception as e:
            logger.exception(f"Unexpected error searching transactions: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.TransactionListResponse(
                success=False, message=f"Internal error: {e}", transactions=[]
            )

    def _transaction_to_proto(self, txn):
        """Convert database transaction to protobuf message.

        Args:
            txn: Transaction model instance.

        Returns:
            budget_pb2.Transaction protobuf message.
        """
        return budget_pb2.Transaction(
            id=txn.id,
            type=txn.type,
            card=txn.card if txn.card else "",
            category=txn.category if txn.category else "",
            description=txn.description,
            amount=txn.amount,
            timestamp=txn.timestamp.isoformat() if txn.timestamp else "",
        )


class BudgetServiceServicer(budget_pb2_grpc.BudgetServiceServicer):
    """gRPC servicer for budget viewing operations."""

    def __init__(self, db_name: str = "budget.db"):
        """Initialize the budget service.

        Args:
            db_name: Name of the database file.
        """
        self.db_name = db_name
        logger.debug(f"BudgetServiceServicer initialized with database: {db_name}")

    def GetAllBalances(self, request, context):
        """Get all balances.

        Args:
            request: GetAllBalancesRequest (empty).
            context: gRPC context.

        Returns:
            BalanceListResponse with all balances.
        """
        logger.debug("GetAllBalances called")
        try:
            with BudgetManager(self.db_name) as bm:
                balances_dict = bm.get_all_balances()

                balances = [
                    budget_pb2.Balance(type=b_type, amount=amount)
                    for b_type, amount in balances_dict.items()
                ]
                logger.info(f"Retrieved {len(balances)} balances")

                return budget_pb2.BalanceListResponse(
                    success=True,
                    message=f"Found {len(balances)} balances",
                    balances=balances,
                )
        except DatabaseError as e:
            logger.error(f"Database error getting all balances: {e}")
            return budget_pb2.BalanceListResponse(
                success=False, message=str(e), balances=[]
            )
        except Exception as e:
            logger.exception(f"Unexpected error getting all balances: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.BalanceListResponse(
                success=False, message=f"Internal error: {e}", balances=[]
            )

    def GetBalance(self, request, context):
        """Get balance for a specific type.

        Args:
            request: GetBalanceRequest with balance type.
            context: gRPC context.

        Returns:
            BalanceResponse with the balance.
        """
        try:
            with BudgetManager(self.db_name) as bm:
                amount = bm.get_balance(request.balance_type)

                return budget_pb2.BalanceResponse(
                    success=True,
                    message="Balance retrieved",
                    balance=budget_pb2.Balance(
                        type=request.balance_type, amount=amount
                    ),
                )
        except DatabaseError as e:
            return budget_pb2.BalanceResponse(
                success=False, message=str(e), balance=None
            )
        except Exception as e:
            logger.exception("Error getting balance")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.BalanceResponse(
                success=False, message=f"Internal error: {e}", balance=None
            )

    def UpdateBalance(self, request, context):
        """Update balance for a specific type.

        Args:
            request: UpdateBalanceRequest with balance type and amount.
            context: gRPC context.

        Returns:
            UpdateBalanceResponse indicating success.
        """
        logger.debug(
            f"UpdateBalance called for type={request.balance_type}, amount={request.amount}"
        )
        try:
            with BudgetManager(self.db_name) as bm:
                bm.update_balance(request.balance_type, request.amount)
                logger.success(
                    f"Balance updated successfully: {request.balance_type}={request.amount}"
                )

                return budget_pb2.UpdateBalanceResponse(
                    success=True, message="Balance updated successfully"
                )
        except ValidationError as e:
            logger.warning(
                f"Validation error updating balance {request.balance_type}: {e}"
            )
            return budget_pb2.UpdateBalanceResponse(success=False, message=str(e))
        except DatabaseError as e:
            logger.error(f"Database error updating balance {request.balance_type}: {e}")
            return budget_pb2.UpdateBalanceResponse(success=False, message=str(e))
        except Exception as e:
            logger.exception(
                f"Unexpected error updating balance {request.balance_type}: {e}"
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.UpdateBalanceResponse(
                success=False, message=f"Internal error: {e}"
            )

    def GetCategories(self, request, context):
        """Get all categories.

        Args:
            request: GetCategoriesRequest (empty).
            context: gRPC context.

        Returns:
            CategoryListResponse with all categories.
        """
        try:
            with BudgetManager(self.db_name) as bm:
                categories = bm.get_categories()

                return budget_pb2.CategoryListResponse(
                    success=True,
                    message=f"Found {len(categories)} categories",
                    categories=[
                        budget_pb2.Category(
                            id=cat.id, name=cat.name, description=cat.description or ""
                        )
                        for cat in categories
                    ],
                )
        except DatabaseError as e:
            return budget_pb2.CategoryListResponse(
                success=False, message=str(e), categories=[]
            )
        except Exception as e:
            logger.exception("Error getting categories")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.CategoryListResponse(
                success=False, message=f"Internal error: {e}", categories=[]
            )

    def AddCategory(self, request, context):
        """Add a new category.

        Args:
            request: AddCategoryRequest with category details.
            context: gRPC context.

        Returns:
            AddCategoryResponse indicating success.
        """
        logger.debug(f"AddCategory called for name={request.name}")
        try:
            with BudgetManager(self.db_name) as bm:
                success = bm.add_category(request.name, request.description)

                if success:
                    logger.success(f"Category '{request.name}' added successfully")
                    return budget_pb2.AddCategoryResponse(
                        success=True, message="Category added successfully"
                    )
                else:
                    logger.warning(f"Category '{request.name}' already exists")
                    return budget_pb2.AddCategoryResponse(
                        success=False, message="Category already exists"
                    )
        except ValidationError as e:
            logger.warning(f"Validation error adding category '{request.name}': {e}")
            return budget_pb2.AddCategoryResponse(success=False, message=str(e))
        except DatabaseError as e:
            logger.error(f"Database error adding category '{request.name}': {e}")
            return budget_pb2.AddCategoryResponse(success=False, message=str(e))
        except Exception as e:
            logger.exception(f"Unexpected error adding category '{request.name}': {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.AddCategoryResponse(
                success=False, message=f"Internal error: {e}"
            )

    def GetSpendingByCategory(self, request, context):
        """Get spending by category for a specific month.

        Args:
            request: GetSpendingByCategoryRequest with year and month.
            context: gRPC context.

        Returns:
            SpendingByCategoryResponse with category breakdown.
        """
        logger.debug(
            f"GetSpendingByCategory called for {request.year}-{request.month:02d}"
        )
        try:
            with BudgetManager(self.db_name) as bm:
                spending_data = bm.get_spending_by_category(request.year, request.month)

                category_spending = []
                total = 0.0

                for category, amount in spending_data.items():
                    total += amount

                for category, amount in spending_data.items():
                    percentage = (amount / total * 100) if total > 0 else 0
                    category_spending.append(
                        budget_pb2.CategorySpending(
                            category=category, amount=amount, percentage=percentage
                        )
                    )

                logger.info(
                    f"Retrieved spending by category for {request.year}-{request.month:02d}: {len(category_spending)} categories, total=${total:.2f}"
                )

                return budget_pb2.SpendingByCategoryResponse(
                    success=True,
                    message=f"Found spending data for {request.year}-{request.month:02d}",
                    category_spending=category_spending,
                    total=total,
                )
        except DatabaseError as e:
            logger.error(
                f"Database error getting spending by category for {request.year}-{request.month:02d}: {e}"
            )
            return budget_pb2.SpendingByCategoryResponse(
                success=False, message=str(e), category_spending=[], total=0.0
            )
        except Exception as e:
            logger.exception(
                f"Unexpected error getting spending by category for {request.year}-{request.month:02d}: {e}"
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.SpendingByCategoryResponse(
                success=False,
                message=f"Internal error: {e}",
                category_spending=[],
                total=0.0,
            )

    def GetDailySpending(self, request, context):
        """Get daily spending for the last N days.

        Args:
            request: GetDailySpendingRequest with number of days.
            context: gRPC context.

        Returns:
            DailySpendingResponse with daily spending data.
        """
        try:
            with BudgetManager(self.db_name) as bm:
                days = request.days if request.days > 0 else 30
                daily_data = bm.get_daily_spending(days)

                daily_spending = [
                    budget_pb2.DailySpendingEntry(date=date, amount=amount)
                    for date, amount in daily_data
                ]

                return budget_pb2.DailySpendingResponse(
                    success=True,
                    message=f"Found daily spending for last {days} days",
                    daily_spending=daily_spending,
                )
        except DatabaseError as e:
            return budget_pb2.DailySpendingResponse(
                success=False, message=str(e), daily_spending=[]
            )
        except Exception as e:
            logger.exception("Error getting daily spending")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.DailySpendingResponse(
                success=False, message=f"Internal error: {e}", daily_spending=[]
            )

    def GetSpendingLimits(self, request, context):
        """Get all spending limits.

        Args:
            request: GetSpendingLimitsRequest (empty).
            context: gRPC context.

        Returns:
            SpendingLimitsResponse with all limits.
        """
        try:
            with BudgetManager(self.db_name) as bm:
                limits_data = bm.get_spending_limits()

                limits = [
                    budget_pb2.SpendingLimit(
                        id=limit.id,
                        category=limit.category or "",
                        source=limit.source or "",
                        limit_amount=limit.limit_amount,
                        period=limit.period,
                    )
                    for limit in limits_data
                ]

                return budget_pb2.SpendingLimitsResponse(
                    success=True, message=f"Found {len(limits)} limits", limits=limits
                )
        except DatabaseError as e:
            return budget_pb2.SpendingLimitsResponse(
                success=False, message=str(e), limits=[]
            )
        except Exception as e:
            logger.exception("Error getting spending limits")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.SpendingLimitsResponse(
                success=False, message=f"Internal error: {e}", limits=[]
            )

    def SetSpendingLimit(self, request, context):
        """Set a spending limit.

        Args:
            request: SetSpendingLimitRequest with limit details.
            context: gRPC context.

        Returns:
            SetSpendingLimitResponse indicating success.
        """
        logger.debug(
            f"SetSpendingLimit called: amount={request.limit_amount}, period={request.period}, category={request.category}, source={request.source}"
        )
        try:
            with BudgetManager(self.db_name) as bm:
                success = bm.set_spending_limit(
                    limit_amount=request.limit_amount,
                    period=request.period,
                    category=request.category if request.category else None,
                    source=request.source if request.source else None,
                )

                if success:
                    logger.success(
                        f"Spending limit set: ${request.limit_amount} ({request.period})"
                    )
                    return budget_pb2.SetSpendingLimitResponse(
                        success=True, message="Spending limit set successfully"
                    )
                else:
                    logger.warning(
                        f"Failed to set spending limit: ${request.limit_amount}"
                    )
                    return budget_pb2.SetSpendingLimitResponse(
                        success=False, message="Failed to set spending limit"
                    )
        except ValidationError as e:
            logger.warning(f"Validation error setting spending limit: {e}")
            return budget_pb2.SetSpendingLimitResponse(success=False, message=str(e))
        except DatabaseError as e:
            logger.error(f"Database error setting spending limit: {e}")
            return budget_pb2.SetSpendingLimitResponse(success=False, message=str(e))
        except Exception as e:
            logger.exception(f"Unexpected error setting spending limit: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.SetSpendingLimitResponse(
                success=False, message=f"Internal error: {e}"
            )

    def CheckSpendingLimit(self, request, context):
        """Check if spending limit is exceeded.

        Args:
            request: CheckSpendingLimitRequest with filter criteria.
            context: gRPC context.

        Returns:
            CheckSpendingLimitResponse with limit check result.
        """
        try:
            with BudgetManager(self.db_name) as bm:
                result = bm.check_spending_limit(
                    category=request.category if request.category else None,
                    source=request.source if request.source else None,
                    period=request.period if request.period else "monthly",
                )

                limit_result = budget_pb2.LimitCheckResult(
                    current_spending=result["spent"],
                    limit_amount=result["limit"],
                    is_exceeded=result["exceeded"],
                    remaining=result["remaining"],
                )

                return budget_pb2.CheckSpendingLimitResponse(
                    success=True, message="Limit check completed", result=limit_result
                )
        except DatabaseError as e:
            return budget_pb2.CheckSpendingLimitResponse(
                success=False, message=str(e), result=None
            )
        except Exception as e:
            logger.exception("Error checking spending limit")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {e}")
            return budget_pb2.CheckSpendingLimitResponse(
                success=False, message=f"Internal error: {e}", result=None
            )


def get_metrics() -> dict:
    """Get current server metrics.

    Returns:
        dict: Server metrics including request counts, error rates, and performance.
    """
    global _metrics_interceptor

    if _metrics_interceptor is None:
        logger.warning("Metrics requested but metrics interceptor not initialized")
        return {"error": "Metrics not available"}

    logger.debug("Retrieving server metrics")
    return _metrics_interceptor.get_metrics()


def serve(
    port: Optional[int] = None,
    db_name: Optional[str] = None,
    config: Optional[Config] = None,
):
    """Start the gRPC server with proper configuration and resource management.

    Args:
        port: Port number to listen on. If None, uses configuration.
        db_name: Name of the database file. If None, uses configuration.
        config: Configuration object. If None, uses global configuration.
    """
    global _metrics_interceptor

    logger.info("Starting gRPC server initialization")

    # Load configuration
    if config is None:
        config = get_config()
        logger.debug("Loaded default configuration")

    if port is None:
        port = config.server.port
        logger.debug(f"Using port from configuration: {port}")

    # Initialize database with configuration
    logger.info(f"Initializing database: {db_name or config.database.db_name}")
    database.get_engine(db_name=db_name, config=config.database)
    database.init_db()
    logger.success("Database initialized successfully")

    # Create interceptors
    logging_interceptor = LoggingInterceptor()
    error_interceptor = ErrorHandlingInterceptor()
    _metrics_interceptor = MetricsInterceptor()

    # Create server with thread pool and interceptors
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=config.server.max_workers),
        interceptors=[
            error_interceptor,
            logging_interceptor,
            _metrics_interceptor,
        ],
    )

    # Add servicers
    budget_pb2_grpc.add_TransactionServiceServicer_to_server(
        TransactionServiceServicer(db_name or config.database.db_name), server
    )
    budget_pb2_grpc.add_BudgetServiceServicer_to_server(
        BudgetServiceServicer(db_name or config.database.db_name), server
    )

    # Bind server to port
    # Note: gRPC requires [::]  or 0.0.0.0 format, not "localhost"
    bind_address = f"[::]:{port}"
    server.add_insecure_port(bind_address)
    logger.info(f"Server bound to {bind_address}")

    # Check health before starting
    health_status = get_health_status()
    if not health_status["healthy"]:
        logger.error(f"Health check failed: {health_status}")
        logger.warning("Starting server anyway, but some functionality may be limited")

    # Start server
    server.start()
    logger.success(f"gRPC server started successfully on {config.server.host}:{port}")
    logger.info(f"Database: {db_name or config.database.db_name}")
    logger.info(f"Workers: {config.server.max_workers}")
    logger.info(f"Health: {'OK' if health_status['healthy'] else 'DEGRADED'}")
    logger.debug("Server registered and ready to accept requests")

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        server.stop(config.server.grace_period)
        database.close_db()
        logger.success("Server stopped")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Wait for termination
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down...")
        server.stop(config.server.grace_period)
        database.close_db()
    finally:
        logger.info("Server terminated")


if __name__ == "__main__":
    # Configure loguru (loguru is already configured via imports)
    config = get_config()

    # Optionally configure loguru's log level based on config
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=config.logging.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    serve()
