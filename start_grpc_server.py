#!/usr/bin/env python3
"""Standalone script to start the gRPC server.

Usage:
    python start_grpc_server.py [OPTIONS]

Options:
    --port PORT         Port to listen on
    --db DB_NAME        Database file name
    --workers N         Number of worker threads
    --log-level LEVEL   Logging level (DEBUG, INFO, WARNING, ERROR)
    -v, --verbose       Enable verbose logging (DEBUG level)
    --help             Show this help message

Environment Variables:
    BUDGET_PORT                 Server port (default: 50051)
    BUDGET_DB_NAME              Database file name (default: budget.db)
    BUDGET_MAX_WORKERS          Worker thread count (default: 10)
    BUDGET_LOG_LEVEL            Logging level (default: INFO)
    BUDGET_DB_POOL_SIZE         Database connection pool size (default: 10)
    BUDGET_MAX_CONCURRENT_RPCS  Max concurrent RPCs (default: unlimited)
"""

import argparse
import sys

from loguru import logger

from budget.infrastructure.config import (
    Config,
    set_config,
)
from budget.server.grpc_server import serve


def main():
    """Parse arguments and start the gRPC server with configuration."""
    parser = argparse.ArgumentParser(
        description="Start the Budget gRPC server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  BUDGET_PORT                 Server port (default: 50051)
  BUDGET_DB_NAME              Database file name (default: budget.db)
  BUDGET_MAX_WORKERS          Worker thread count (default: 10)
  BUDGET_LOG_LEVEL            Logging level (default: INFO)
  BUDGET_DB_POOL_SIZE         Database connection pool size (default: 10)
  BUDGET_MAX_CONCURRENT_RPCS  Max concurrent RPCs (default: unlimited)
  BUDGET_GRACE_PERIOD         Graceful shutdown period in seconds (default: 10)

Examples:
  python start_grpc_server.py
  python start_grpc_server.py --port 8080 --workers 20
  python start_grpc_server.py --db production.db --log-level DEBUG
  BUDGET_PORT=8080 python start_grpc_server.py
        """,
    )

    # Server options
    parser.add_argument(
        "--port", type=int, help="Port to listen on (default: from config or 50051)"
    )
    parser.add_argument(
        "--host", type=str, help="Host address to bind to (default: [::])"
    )
    parser.add_argument(
        "--workers", type=int, help="Number of worker threads (default: 10)"
    )
    parser.add_argument(
        "--max-concurrent-rpcs",
        type=int,
        help="Maximum concurrent RPCs (default: unlimited)",
    )

    # Database options
    parser.add_argument(
        "--db", type=str, help="Database file name (default: budget.db)"
    )
    parser.add_argument(
        "--db-pool-size", type=int, help="Database connection pool size (default: 10)"
    )

    # Logging options
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Log to file (in addition to console). Example: --log-file server.log",
    )

    args = parser.parse_args()

    # Build configuration from environment and arguments
    config = Config.from_env()

    # Override with command-line arguments
    if args.port:
        config.server.port = args.port
    if args.host:
        config.server.host = args.host
    if args.workers:
        config.server.max_workers = args.workers
    if args.max_concurrent_rpcs:
        config.server.max_concurrent_rpcs = args.max_concurrent_rpcs
    if args.db:
        config.database.db_name = args.db
    if args.db_pool_size:
        config.database.pool_size = args.db_pool_size
    if args.log_level:
        config.logging.level = args.log_level
    elif args.verbose:
        config.logging.level = "DEBUG"

    # Set global configuration
    set_config(config)

    # Configure loguru
    logger.remove()  # Remove default handler

    # Add console handler
    logger.add(
        sys.stderr,
        level=config.logging.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # Add file handler if specified
    if args.log_file:
        logger.add(
            args.log_file,
            level=config.logging.level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",  # Rotate when file reaches 10MB
            retention="7 days",  # Keep logs for 7 days
        )
        logger.info(f"Logging to file: {args.log_file}")

    logger.info("=" * 60)
    logger.info("Budget gRPC Server Configuration")
    logger.info("=" * 60)
    logger.info(f"Server: {config.server.host}:{config.server.port}")
    logger.info(f"Database: {config.database.db_name}")
    logger.info(f"Workers: {config.server.max_workers}")
    logger.info(f"DB Pool Size: {config.database.pool_size}")
    logger.info(f"Log Level: {config.logging.level}")
    if config.server.max_concurrent_rpcs:
        logger.info(f"Max Concurrent RPCs: {config.server.max_concurrent_rpcs}")
    logger.info("=" * 60)

    try:
        serve(config=config)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
