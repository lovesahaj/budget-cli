"""Health check functionality for the gRPC server.

This module provides health check endpoints and utilities to monitor
the server's health status, including database connectivity.
"""

from typing import Any, Dict

from loguru import logger
from sqlalchemy import text

from budget.domain.exceptions import DatabaseError
from budget.infrastructure import database


class HealthChecker:
    """Health checker for the budget application.

    Provides methods to check the health of various components including
    database connectivity and system resources.
    """

    @staticmethod
    def check_database() -> Dict[str, Any]:
        """Check database connectivity and health.

        Returns:
            dict: Health status with 'healthy' boolean and optional 'error' message.
        """
        logger.debug("Starting database health check")
        try:
            engine = database.get_engine()
            with engine.connect() as conn:
                # Simple query to verify database is accessible
                conn.execute(text("SELECT 1"))
            logger.info("Database health check passed")
            return {"healthy": True, "message": "Database connection OK"}
        except Exception as e:
            logger.error("Database health check failed: {}", e)
            return {
                "healthy": False,
                "message": "Database connection failed",
                "error": str(e),
            }

    @staticmethod
    def check_all() -> Dict[str, Any]:
        """Perform comprehensive health check.

        Checks all critical components and returns overall health status.

        Returns:
            dict: Comprehensive health status including individual component checks.
        """
        logger.debug("Starting comprehensive health check")
        db_health = HealthChecker.check_database()

        # Overall health is OK only if all components are healthy
        overall_healthy = db_health["healthy"]

        logger.info("Overall health status: {}", "healthy" if overall_healthy else "unhealthy")

        return {
            "healthy": overall_healthy,
            "components": {"database": db_health},
            "version": "0.1.0",
        }


def get_health_status() -> Dict[str, Any]:
    """Get current health status of the application.

    Convenience function to get health status without creating a HealthChecker instance.

    Returns:
        dict: Current health status.
    """
    return HealthChecker.check_all()
