"""Transaction export module.

This module provides functionality for exporting transaction data to
various file formats including CSV and JSON.
"""

import csv
import json
from datetime import datetime
from typing import Optional

from budget.exceptions import BudgetError


class ExportManager:
    """Manages exporting transaction data to different file formats.

    The ExportManager provides methods to export transactions to CSV and
    JSON formats with optional date range filtering.

    Attributes:
        transaction_manager: TransactionManager instance for accessing transactions.

    Example:
        >>> with BudgetManager() as bm:
        ...     export_mgr = ExportManager(bm.transactions)
        ...     # Export all transactions to CSV
        ...     export_mgr.export_to_csv("transactions.csv")
        ...     # Export with date filter to JSON
        ...     export_mgr.export_to_json(
        ...         "october.json",
        ...         start_date="2025-10-01",
        ...         end_date="2025-10-31"
        ...     )
    """

    def __init__(self, transaction_manager):
        """Initialize the ExportManager.

        Args:
            transaction_manager: TransactionManager instance for retrieving
                               transaction data.
        """
        self.transaction_manager = transaction_manager

    def export_to_csv(
        self,
        filepath: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """Export transactions to a CSV file.

        Creates a CSV file with all transaction data including id, type, card,
        category, description, amount, and timestamp. If no transactions match
        the date range, an empty file is created.

        Args:
            filepath: Path where the CSV file should be created.
            start_date: Optional start date filter (YYYY-MM-DD format).
            end_date: Optional end date filter (YYYY-MM-DD format).

        Raises:
            BudgetError: If writing the CSV file fails.

        Example:
            >>> export_mgr.export_to_csv("all_transactions.csv")
            >>> # Export specific date range
            >>> export_mgr.export_to_csv(
            ...     "october.csv",
            ...     start_date="2025-10-01",
            ...     end_date="2025-10-31"
            ... )
        """
        try:
            transactions = self.transaction_manager.search_transactions(
                start_date=start_date, end_date=end_date
            )

            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                if not transactions:
                    return

                fieldnames = [
                    "id",
                    "type",
                    "card",
                    "category",
                    "description",
                    "amount",
                    "timestamp",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for transaction in transactions:
                    row = {field: getattr(transaction, field) for field in fieldnames}
                    # Convert timestamp to string for CSV
                    if row.get('timestamp'):
                        row['timestamp'] = str(row['timestamp'])
                    writer.writerow(row)
        except IOError as e:
            raise BudgetError(f"Failed to export to CSV: {e}")

    def export_to_json(
        self,
        filepath: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """Export transactions to a JSON file with summary statistics.

        Creates a JSON file containing transaction data along with export
        metadata and summary statistics (total transactions and total amount).

        Args:
            filepath: Path where the JSON file should be created.
            start_date: Optional start date filter (YYYY-MM-DD format).
            end_date: Optional end date filter (YYYY-MM-DD format).

        Raises:
            BudgetError: If writing the JSON file fails.

        Example:
            >>> export_mgr.export_to_json("transactions.json")
            >>> # The JSON structure includes:
            >>> # {
            >>> #   "export_date": "2025-10-04T12:00:00",
            >>> #   "transactions": [...],
            >>> #   "summary": {
            >>> #     "total_transactions": 100,
            >>> #     "total_amount": 1250.75
            >>> #   }
            >>> # }
        """
        try:
            transactions = self.transaction_manager.search_transactions(
                start_date=start_date, end_date=end_date
            )

            with open(filepath, "w", encoding="utf-8") as jsonfile:
                # Convert transactions to clean dicts
                transaction_dicts = []
                for t in transactions:
                    transaction_dicts.append({
                        "id": t.id,
                        "type": t.type,
                        "card": t.card,
                        "category": t.category,
                        "description": t.description,
                        "amount": t.amount,
                        "timestamp": str(t.timestamp) if t.timestamp else None,
                    })

                json.dump(
                    {
                        "export_date": datetime.now().isoformat(),
                        "transactions": transaction_dicts,
                        "summary": {
                            "total_transactions": len(transactions),
                            "total_amount": sum(t.amount for t in transactions),
                        },
                    },
                    jsonfile,
                    indent=2,
                )
        except IOError as e:
            raise BudgetError(f"Failed to export to JSON: {e}")
