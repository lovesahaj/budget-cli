"""LLM-based transaction extraction using Claude API."""

import json
import os
from datetime import datetime
from typing import List, Optional

import anthropic


class LLMExtractor:
    """Extract structured transaction data from text using Claude."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the LLM extractor.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable must be set or pass api_key parameter"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def extract_transactions(
        self,
        text: str,
        context: str = "",
        source_type: str = "document",
    ) -> List[dict]:
        """Extract transactions from text using Claude.

        Args:
            text: Text to extract transactions from
            context: Additional context (e.g., "bank statement", "receipt")
            source_type: Type of source ("pdf", "image", "email")

        Returns:
            List of transaction dicts with keys:
                - description: str
                - amount: float
                - date: datetime
                - type: str ("card" or "cash")
                - card: str (optional)
                - category: str (optional)
                - metadata: dict (optional)
        """
        prompt = self._build_extraction_prompt(text, context, source_type)

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract JSON from response
            response_text = message.content[0].text
            transactions_data = self._parse_response(response_text)

            # Convert to standard format
            return self._normalize_transactions(transactions_data)

        except Exception as e:
            print(f"Error extracting transactions with LLM: {e}")
            return []

    def _build_extraction_prompt(
        self, text: str, context: str, source_type: str
    ) -> str:
        """Build the prompt for Claude."""
        return f"""Extract all financial transactions from the following {context or source_type}.

For each transaction, extract:
- description: Brief description of the transaction
- amount: Transaction amount (positive number)
- date: Transaction date (YYYY-MM-DD format, or estimate based on context)
- type: "card" or "cash" (guess based on context if not specified)
- card: Card name or last 4 digits if mentioned (optional)
- category: Transaction category like "Food", "Transport", "Entertainment" etc. (optional)

Return ONLY a JSON array of transactions. No additional text.
Example format:
[
  {{
    "description": "Coffee at Starbucks",
    "amount": 5.50,
    "date": "2025-10-11",
    "type": "card",
    "card": "Visa",
    "category": "Food"
  }}
]

Text to analyze:
{text}

Return the JSON array:"""

    def _parse_response(self, response_text: str) -> List[dict]:
        """Parse Claude's response to extract JSON."""
        # Try to find JSON array in response
        start_idx = response_text.find("[")
        end_idx = response_text.rfind("]") + 1

        if start_idx == -1 or end_idx == 0:
            return []

        json_str = response_text[start_idx:end_idx]

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return []

    def _normalize_transactions(self, transactions_data: List[dict]) -> List[dict]:
        """Normalize extracted transactions to standard format."""
        normalized = []

        for txn in transactions_data:
            try:
                # Parse date
                date_str = txn.get("date")
                if date_str:
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        # Try other common formats
                        for fmt in ["%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                            try:
                                date = datetime.strptime(date_str, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            date = datetime.now()  # Fallback to today
                else:
                    date = datetime.now()

                normalized_txn = {
                    "description": txn.get("description", "Unknown"),
                    "amount": float(txn.get("amount", 0)),
                    "date": date,
                    "type": txn.get("type", "card"),
                    "card": txn.get("card"),
                    "category": txn.get("category"),
                    "metadata": {
                        "extracted_by": "llm",
                        "confidence": "high",  # Could add confidence scoring
                    },
                }

                # Only add if valid amount
                if normalized_txn["amount"] > 0:
                    normalized.append(normalized_txn)

            except (ValueError, KeyError) as e:
                print(f"Error normalizing transaction: {e}")
                continue

        return normalized
