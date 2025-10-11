"""Configuration management for the Budget application.

This module provides centralized configuration management for the application,
including database settings, server settings, and logging configuration.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """Database configuration settings.

    Attributes:
        db_name: Name of the SQLite database file
        pool_size: Connection pool size for database connections
        pool_recycle: Time in seconds to recycle connections
        echo: Enable SQL query logging
    """

    db_name: str = "budget.db"
    pool_size: int = 10
    pool_recycle: int = 3600
    echo: bool = False

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables.

        Returns:
            DatabaseConfig instance populated from environment variables.
        """
        return cls(
            db_name=os.getenv("BUDGET_DB_NAME", "budget.db"),
            pool_size=int(os.getenv("BUDGET_DB_POOL_SIZE", "10")),
            pool_recycle=int(os.getenv("BUDGET_DB_POOL_RECYCLE", "3600")),
            echo=os.getenv("BUDGET_DB_ECHO", "false").lower() == "true",
        )


@dataclass
class ServerConfig:
    """gRPC server configuration settings.

    Attributes:
        host: Host address to bind to
        port: Port number to listen on
        max_workers: Maximum number of thread pool workers
        max_concurrent_rpcs: Maximum number of concurrent RPCs
        grace_period: Grace period in seconds for graceful shutdown
    """

    host: str = "localhost"
    port: int = 50051
    max_workers: int = 10
    max_concurrent_rpcs: Optional[int] = None
    grace_period: int = 10

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create configuration from environment variables.

        Returns:
            ServerConfig instance populated from environment variables.
        """
        max_concurrent_rpcs = os.getenv("BUDGET_MAX_CONCURRENT_RPCS")
        return cls(
            host=os.getenv("BUDGET_HOST", "[::]"),
            port=int(os.getenv("BUDGET_PORT", "50051")),
            max_workers=int(os.getenv("BUDGET_MAX_WORKERS", "10")),
            max_concurrent_rpcs=int(max_concurrent_rpcs)
            if max_concurrent_rpcs
            else None,
            grace_period=int(os.getenv("BUDGET_GRACE_PERIOD", "10")),
        )


@dataclass
class LoggingConfig:
    """Logging configuration settings.

    Attributes:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Log message format string
        date_format: Date format string for log messages
    """

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Create configuration from environment variables.

        Returns:
            LoggingConfig instance populated from environment variables.
        """
        return cls(
            level=os.getenv("BUDGET_LOG_LEVEL", "INFO").upper(),
            format=os.getenv(
                "BUDGET_LOG_FORMAT",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            ),
            date_format=os.getenv("BUDGET_LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S"),
        )


@dataclass
class Config:
    """Main application configuration.

    Attributes:
        database: Database configuration
        server: Server configuration
        logging: Logging configuration
    """

    database: DatabaseConfig
    server: ServerConfig
    logging: LoggingConfig

    @classmethod
    def from_env(cls) -> "Config":
        """Create complete configuration from environment variables.

        Returns:
            Config instance with all sub-configurations populated from environment.
        """
        return cls(
            database=DatabaseConfig.from_env(),
            server=ServerConfig.from_env(),
            logging=LoggingConfig.from_env(),
        )

    @classmethod
    def default(cls) -> "Config":
        """Create configuration with default values.

        Returns:
            Config instance with default values.
        """
        return cls(
            database=DatabaseConfig(),
            server=ServerConfig(),
            logging=LoggingConfig(),
        )


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance.

    Returns:
        Config: The global configuration instance, created from environment if not yet initialized.
    """
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance.

    Args:
        config: Configuration instance to use globally.
    """
    global _config
    _config = config
