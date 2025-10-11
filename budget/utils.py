"""Utility functions for the budget tracker."""

import hashlib
import json
from datetime import datetime
from typing import Optional


def generate_transaction_hash(
    date: datetime,
    amount: float,
    description: str,
    card: Optional[str] = None,
) -> str:
    """Generate a unique hash for transaction deduplication.

    Args:
        date: Transaction date
        amount: Transaction amount
        description: Transaction description
        card: Optional card name

    Returns:
        SHA256 hash string
    """
    # Normalize inputs for consistent hashing
    date_str = date.strftime("%Y-%m-%d")  # Ignore time component
    amount_str = f"{float(amount):.2f}"  # Normalize to 2 decimal places
    desc_normalized = description.lower().strip()
    card_normalized = card.lower().strip() if card else ""

    # Create hash input
    hash_input = f"{date_str}|{amount_str}|{desc_normalized}|{card_normalized}"

    # Generate SHA256 hash
    return hashlib.sha256(hash_input.encode()).hexdigest()


def normalize_description(description: str) -> str:
    """Normalize transaction description for matching.

    Args:
        description: Raw description

    Returns:
        Normalized description
    """
    return " ".join(description.lower().strip().split())


def serialize_import_metadata(metadata: dict) -> str:
    """Serialize import metadata to JSON string.

    Args:
        metadata: Metadata dictionary

    Returns:
        JSON string
    """
    return json.dumps(metadata, sort_keys=True)


def deserialize_import_metadata(metadata_str: Optional[str]) -> dict:
    """Deserialize import metadata from JSON string.

    Args:
        metadata_str: JSON string or None

    Returns:
        Metadata dictionary
    """
    if not metadata_str:
        return {}
    try:
        return json.loads(metadata_str)
    except json.JSONDecodeError:
        return {}
