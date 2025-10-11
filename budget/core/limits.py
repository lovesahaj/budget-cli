"""Spending limit management module.

This module provides functionality for setting, retrieving, and checking
spending limits across different time periods, categories, and payment sources.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from budget.domain.exceptions import DatabaseError, ValidationError
from budget.domain.models import SpendingLimit, Transaction


class LimitManager:
    """Manages spending limits and monitors spending against those limits.

    The LimitManager handles operations related to spending limits, including
    setting limits for different periods/categories/sources and checking
    current spending against those limits.

    Attributes:
        session (Session): SQLAlchemy database session.

    Example:
        >>> with BudgetManager() as bm:
        ...     limit_mgr = LimitManager(bm.session)
        ...     # Set a monthly food budget
        ...     limit_mgr.set_spending_limit(500.0, "monthly", category="Food")
        ...     # Check current spending
        ...     status = limit_mgr.check_spending_limit(category="Food")
    """

    def __init__(self, session: Session):
        """Initialize the LimitManager.

        Args:
            session: SQLAlchemy database session for database operations.
        """
        logger.debug("Initializing LimitManager with session: {}", session)
        self.session = session

    def set_spending_limit(
        self,
        limit_amount: float,
        period: str = "monthly",
        category: Optional[str] = None,
        source: Optional[str] = None,
    ) -> bool:
        """Set or update a spending limit.

        Creates a new spending limit or updates an existing one. Limits can be
        set for specific categories, payment sources, time periods, or any
        combination thereof.

        Args:
            limit_amount: Maximum spending amount (must be positive).
            period: Time period - "daily", "weekly", "monthly", or "yearly".
                   Defaults to "monthly".
            category: Optional category to limit (None = all categories).
            source: Optional payment source to limit (None = all sources).

        Returns:
            bool: True if the limit was set successfully.

        Raises:
            ValidationError: If limit_amount is not positive or period is invalid.
            DatabaseError: If setting the limit fails.

        Example:
            >>> # Monthly food budget
            >>> limit_mgr.set_spending_limit(500.0, "monthly", category="Food")
            >>> # Weekly limit for a specific card
            >>> limit_mgr.set_spending_limit(200.0, "weekly", source="Visa")
            >>> # Daily overall spending limit
            >>> limit_mgr.set_spending_limit(50.0, "daily")
        """
        logger.info(
            "Setting spending limit: amount={}, period={}, category={}, source={}",
            limit_amount,
            period,
            category,
            source,
        )
        try:
            if limit_amount <= 0:
                logger.warning(
                    "Validation failed: limit_amount ({}) must be positive", limit_amount
                )
                raise ValidationError("Limit amount must be positive")
            if period not in ["daily", "weekly", "monthly", "yearly"]:
                logger.warning(
                    "Validation failed: invalid period '{}', must be daily/weekly/monthly/yearly",
                    period,
                )
                raise ValidationError(
                    "Period must be daily, weekly, monthly, or yearly"
                )

            limit = (
                self.session.query(SpendingLimit)
                .filter_by(category=category, source=source, period=period)
                .first()
            )

            if limit:
                logger.debug(
                    "Updating existing limit: id={}, old_amount={}, new_amount={}",
                    limit.id,
                    limit.limit_amount,
                    limit_amount,
                )
                limit.limit_amount = float(limit_amount)
            else:
                logger.debug(
                    "Creating new spending limit for period={}, category={}, source={}",
                    period,
                    category,
                    source,
                )
                limit = SpendingLimit(
                    category=category,
                    source=source,
                    limit_amount=float(limit_amount),
                    period=period,
                )
                self.session.add(limit)
            self.session.flush()
            logger.info(
                "Successfully set spending limit: period={}, category={}, source={}, amount={}",
                period,
                category,
                source,
                limit_amount,
            )
            return True
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            logger.error("Failed to set spending limit: {}", e)
            raise DatabaseError(f"Failed to set spending limit: {e}")

    def get_spending_limits(self) -> List[SpendingLimit]:
        """Get all configured spending limits.

        Returns:
            List[SpendingLimit]: List of all spending limit records, sorted by
                                period, category, and source.

        Raises:
            DatabaseError: If retrieving limits fails.

        Example:
            >>> limits = limit_mgr.get_spending_limits()
            >>> for limit in limits:
            ...     print(f"{limit.period} {limit.category}: ${limit.limit_amount}")
        """
        logger.debug("Retrieving all spending limits")
        try:
            limits = (
                self.session.query(SpendingLimit)
                .order_by(
                    SpendingLimit.period, SpendingLimit.category, SpendingLimit.source
                )
                .all()
            )
            logger.info("Retrieved {} spending limit(s)", len(limits))
            return limits
        except Exception as e:
            logger.error("Failed to get spending limits: {}", e)
            raise DatabaseError(f"Failed to get spending limits: {e}")

    def check_spending_limit(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        period: str = "monthly",
    ) -> Optional[Dict]:
        """Check current spending against a configured limit.

        Calculates the current spending for the specified period and compares
        it against the configured limit. Returns detailed information about
        the limit status.

        Args:
            category: Category to check (None = all categories).
            source: Payment source to check (None = all sources).
            period: Time period - "daily", "weekly", "monthly", or "yearly".
                   Defaults to "monthly".

        Returns:
            Optional[Dict]: Dictionary with limit information if a limit is
                           configured, None if no limit exists. The dictionary
                           contains:
                           - limit (float): The configured limit amount
                           - spent (float): Current spending in the period
                           - remaining (float): Amount remaining before limit
                           - percentage (float): Percentage of limit used
                           - exceeded (bool): Whether the limit is exceeded

        Raises:
            DatabaseError: If checking the limit fails.

        Example:
            >>> status = limit_mgr.check_spending_limit(category="Food")
            >>> if status and status['exceeded']:
            ...     print(f"Over budget by ${-status['remaining']:.2f}")
            >>> elif status:
            ...     print(f"{status['percentage']:.1f}% of budget used")
        """
        logger.debug(
            "Checking spending limit: category={}, source={}, period={}",
            category,
            source,
            period,
        )
        try:
            limit = (
                self.session.query(SpendingLimit)
                .filter_by(category=category, source=source, period=period)
                .first()
            )

            if not limit:
                logger.debug(
                    "No spending limit found for category={}, source={}, period={}",
                    category,
                    source,
                    period,
                )
                return None

            limit_amount = limit.limit_amount

            today = datetime.utcnow().date()
            if period == "monthly":
                start_date = datetime.combine(today.replace(day=1), datetime.min.time())
                end_date = datetime.combine(
                    (start_date.date() + timedelta(days=32)).replace(day=1)
                    - timedelta(days=1),
                    datetime.max.time(),
                )
            elif period == "weekly":
                start_date = datetime.combine(
                    today - timedelta(days=today.weekday()), datetime.min.time()
                )
                end_date = datetime.combine(
                    start_date.date() + timedelta(days=6), datetime.max.time()
                )
            elif period == "daily":
                start_date = datetime.combine(today, datetime.min.time())
                end_date = datetime.combine(today, datetime.max.time())
            elif period == "yearly":
                start_date = datetime.combine(
                    today.replace(month=1, day=1), datetime.min.time()
                )
                end_date = datetime.combine(
                    today.replace(month=12, day=31), datetime.max.time()
                )
            else:
                return None

            q = self.session.query(func.sum(Transaction.amount)).filter(
                Transaction.timestamp >= start_date, Transaction.timestamp <= end_date
            )

            if category:
                q = q.filter(Transaction.category == category)

            if source:
                if source == "cash":
                    q = q.filter(Transaction.type == "cash")
                else:
                    q = q.filter(Transaction.card == source)

            current_spending = q.scalar() or 0

            result = {
                "limit": limit_amount,
                "spent": current_spending,
                "remaining": limit_amount - current_spending,
                "percentage": (current_spending / limit_amount * 100)
                if limit_amount > 0
                else 0,
                "exceeded": current_spending > limit_amount,
            }

            if result["exceeded"]:
                logger.warning(
                    "Spending limit EXCEEDED: category={}, source={}, period={}, "
                    "limit={:.2f}, spent={:.2f}, over_by={:.2f}",
                    category,
                    source,
                    period,
                    limit_amount,
                    current_spending,
                    current_spending - limit_amount,
                )
            else:
                logger.info(
                    "Spending limit check: category={}, source={}, period={}, "
                    "limit={:.2f}, spent={:.2f}, remaining={:.2f}, percentage={:.1f}%",
                    category,
                    source,
                    period,
                    limit_amount,
                    current_spending,
                    result["remaining"],
                    result["percentage"],
                )

            return result
        except Exception as e:
            logger.error("Failed to check spending limit: {}", e)
            raise DatabaseError(f"Failed to check spending limit: {e}")
