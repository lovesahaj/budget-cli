"""Personal Budget Tracker - Simple expense tracking application.

## Quick Start

```python
from budget import Budget

# Create a budget tracker
budget = Budget()

# Add a transaction
txn_id = budget.add_transaction("card", "Coffee", 5.50, card="Visa", category="Food")

# Get recent transactions
transactions = budget.get_recent_transactions(10)

# Check balances
balances = budget.get_all_balances()
```
"""

from budget.budget import Budget
from budget.models import Balance, Card, Category, SpendingLimit, Transaction

__version__ = "0.2.0"
__all__ = ["Budget", "Transaction", "Card", "Category", "Balance", "SpendingLimit"]
