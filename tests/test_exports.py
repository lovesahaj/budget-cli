"""Tests for ExportManager."""

import csv
import json
import tempfile
from pathlib import Path

import pytest


def test_export_to_csv(export_manager, transaction_manager):
    """Test exporting transactions to CSV."""
    # Add some transactions
    transaction_manager.add_transaction("cash", None, "Coffee", 3.50, "Food")
    transaction_manager.add_transaction("card", "Wise", "Groceries", 25.00, "Food")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        filepath = f.name

    try:
        export_manager.export_to_csv(filepath)

        # Verify file exists and contains data
        assert Path(filepath).exists()

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["description"] == "Groceries"  # Most recent first
        assert rows[0]["amount"] == "25.0"
        assert rows[1]["description"] == "Coffee"

    finally:
        Path(filepath).unlink(missing_ok=True)


def test_export_to_csv_empty(export_manager):
    """Test exporting when no transactions exist."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        filepath = f.name

    try:
        export_manager.export_to_csv(filepath)

        # File should exist but be empty (or only header)
        assert Path(filepath).exists()

    finally:
        Path(filepath).unlink(missing_ok=True)


def test_export_to_csv_with_date_filter(export_manager, transaction_manager):
    """Test exporting transactions with date filters."""
    # Add transaction
    transaction_manager.add_transaction("cash", None, "Coffee", 3.50, "Food")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        filepath = f.name

    try:
        # Export with date range
        export_manager.export_to_csv(
            filepath, start_date="2025-10-01", end_date="2025-10-31"
        )

        assert Path(filepath).exists()

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Should include today's transaction
        assert len(rows) >= 1

    finally:
        Path(filepath).unlink(missing_ok=True)


def test_export_to_json(export_manager, transaction_manager):
    """Test exporting transactions to JSON."""
    # Add some transactions
    transaction_manager.add_transaction("cash", None, "Coffee", 3.50, "Food")
    transaction_manager.add_transaction("card", "Wise", "Groceries", 25.00, "Food")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        filepath = f.name

    try:
        export_manager.export_to_json(filepath)

        # Verify file exists and contains valid JSON
        assert Path(filepath).exists()

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "export_date" in data
        assert "transactions" in data
        assert "summary" in data
        assert len(data["transactions"]) == 2
        assert data["summary"]["total_transactions"] == 2
        assert data["summary"]["total_amount"] == 28.50

    finally:
        Path(filepath).unlink(missing_ok=True)


def test_export_to_json_empty(export_manager):
    """Test exporting to JSON when no transactions exist."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        filepath = f.name

    try:
        export_manager.export_to_json(filepath)

        assert Path(filepath).exists()

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["summary"]["total_transactions"] == 0
        assert data["summary"]["total_amount"] == 0

    finally:
        Path(filepath).unlink(missing_ok=True)


def test_export_to_json_with_date_filter(export_manager, transaction_manager):
    """Test exporting to JSON with date filters."""
    # Add transaction
    transaction_manager.add_transaction("cash", None, "Coffee", 3.50, "Food")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        filepath = f.name

    try:
        # Export with date range
        export_manager.export_to_json(
            filepath, start_date="2025-10-01", end_date="2025-10-31"
        )

        assert Path(filepath).exists()

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Should include today's transaction
        assert data["summary"]["total_transactions"] >= 1

    finally:
        Path(filepath).unlink(missing_ok=True)


def test_export_to_json_transaction_structure(export_manager, transaction_manager):
    """Test that exported JSON has correct transaction structure."""
    transaction_manager.add_transaction("card", "Wise", "Test", 10.00, "Food")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        filepath = f.name

    try:
        export_manager.export_to_json(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        transaction = data["transactions"][0]
        assert "id" in transaction
        assert "type" in transaction
        assert "card" in transaction
        assert "category" in transaction
        assert "description" in transaction
        assert "amount" in transaction
        assert "timestamp" in transaction

    finally:
        Path(filepath).unlink(missing_ok=True)


def test_export_csv_all_fields(export_manager, transaction_manager):
    """Test that CSV export includes all transaction fields."""
    transaction_manager.add_transaction("card", "Wise", "Test", 10.00, "Food")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        filepath = f.name

    try:
        export_manager.export_to_csv(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        row = rows[0]
        assert "id" in row
        assert "type" in row
        assert "card" in row
        assert "category" in row
        assert "description" in row
        assert "amount" in row
        assert "timestamp" in row

    finally:
        Path(filepath).unlink(missing_ok=True)
