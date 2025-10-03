import csv
import json
from datetime import datetime
from typing import Optional

from budget.exceptions import BudgetError


class ExportManager:
    def __init__(self, transaction_manager):
        self.transaction_manager = transaction_manager

    def export_to_csv(
        self,
        filepath: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """Export transactions to CSV file"""
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
        """Export transactions to JSON file"""
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
