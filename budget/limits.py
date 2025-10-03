from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta

from budget.exceptions import DatabaseError, ValidationError
from budget.models import SpendingLimit, Transaction

class LimitManager:
    def __init__(self, session: Session):
        self.session = session

    def set_spending_limit(
        self,
        limit_amount: float,
        period: str = "monthly",
        category: Optional[str] = None,
        source: Optional[str] = None,
    ) -> bool:
        """Set a spending limit for a category, source, or overall"""
        try:
            if limit_amount <= 0:
                raise ValidationError("Limit amount must be positive")
            if period not in ["daily", "weekly", "monthly", "yearly"]:
                raise ValidationError(
                    "Period must be daily, weekly, monthly, or yearly"
                )

            limit = self.session.query(SpendingLimit).filter_by(
                category=category, source=source, period=period
            ).first()

            if limit:
                limit.limit_amount = float(limit_amount)
            else:
                limit = SpendingLimit(
                    category=category,
                    source=source,
                    limit_amount=float(limit_amount),
                    period=period,
                )
                self.session.add(limit)
            self.session.commit()
            return True
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Failed to set spending limit: {e}")

    def get_spending_limits(self) -> List[SpendingLimit]:
        """Get all spending limits"""
        try:
            return self.session.query(SpendingLimit).order_by(SpendingLimit.period, SpendingLimit.category, SpendingLimit.source).all()
        except Exception as e:
            raise DatabaseError(f"Failed to get spending limits: {e}")

    def check_spending_limit(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        period: str = "monthly",
    ) -> Optional[Dict]:
        """Check if spending limit is exceeded"""
        try:
            limit = self.session.query(SpendingLimit).filter_by(
                category=category, source=source, period=period
            ).first()

            if not limit:
                return None

            limit_amount = limit.limit_amount

            today = datetime.utcnow().date()
            if period == "monthly":
                start_date = datetime.combine(today.replace(day=1), datetime.min.time())
                end_date = datetime.combine((start_date.date() + timedelta(days=32)).replace(day=1) - timedelta(days=1), datetime.max.time())
            elif period == "weekly":
                start_date = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
                end_date = datetime.combine(start_date.date() + timedelta(days=6), datetime.max.time())
            elif period == "daily":
                start_date = datetime.combine(today, datetime.min.time())
                end_date = datetime.combine(today, datetime.max.time())
            elif period == "yearly":
                start_date = datetime.combine(today.replace(month=1, day=1), datetime.min.time())
                end_date = datetime.combine(today.replace(month=12, day=31), datetime.max.time())
            else:
                return None

            q = self.session.query(func.sum(Transaction.amount)).filter(
                Transaction.timestamp >= start_date, Transaction.timestamp <= end_date
            )

            if category:
                q = q.filter(Transaction.category == category)

            if source:
                if source == "cash":
                    q = q.filter(Transaction.type == 'cash')
                else:
                    q = q.filter(Transaction.card == source)

            current_spending = q.scalar() or 0

            return {
                "limit": limit_amount,
                "spent": current_spending,
                "remaining": limit_amount - current_spending,
                "percentage": (current_spending / limit_amount * 100)
                if limit_amount > 0
                else 0,
                "exceeded": current_spending > limit_amount,
            }
        except Exception as e:
            raise DatabaseError(f"Failed to check spending limit: {e}")