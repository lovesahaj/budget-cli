# Budget Tracker

A simple personal budget tracking application for managing daily transactions, account balances, and spending limits.

## Features

- **Transaction Management**: Track income and expenses with categories
- **Balance Tracking**: Monitor account balances (cash, cards)
- **Spending Limits**: Set and check spending limits by category or source
- **Reports**: View spending by category and daily trends
- **Simple CLI**: Easy-to-use command-line interface
- **Auto-Import** (NEW): Automatically import transactions from:
  - **PDF files** (bank statements, credit card statements, receipts)
  - **Images** (photos of receipts using OCR or direct multimodal analysis)
  - **Email** (Gmail/Outlook - scans for transaction emails)
- **Smart Deduplication**: Automatically detects and prevents duplicate transactions
- **Multimodal Support**: Direct image analysis with Gemma 3 (no OCR needed, 896x896 normalized)

## Installation

### Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or pip

### Quick Start

```bash
# Install basic dependencies
uv sync

# Or with pip
pip install -e .

# For auto-import features (PDF, images, email)
uv pip install -e ".[imports]"
# Or with pip
pip install -e ".[imports]"
```

### Auto-Import Setup

To use the auto-import features, you'll need:

1. **LLM Provider** (for transaction extraction) - Choose one:

   **Option A: Anthropic Claude API** (Recommended for best accuracy):

   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

   Get one at: https://console.anthropic.com/

   **Option B: Local LLM via LM Studio** (Free, runs locally):
   1. Download and install LM Studio: https://lmstudio.ai/
   2. Load a model:
      - **For text extraction**: Llama 3.1 8B or similar
      - **For images (multimodal)**: Gemma 3 12B (recommended for receipts)
   3. Start the local server (default: http://localhost:1234)
   4. No API key needed!

   **Note:** Gemma 3 supports direct image analysis (multimodal) and automatically normalizes images to 896x896 resolution. This provides better accuracy than OCR for receipts and documents.

2. **Tesseract OCR** (for image import with OCR):

   ```bash
   # macOS
   brew install tesseract

   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr

   # Windows
   # Download from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

   **Note:** Tesseract is optional if you're using a multimodal model like Gemma 3, which can analyze images directly without OCR.

3. **Gmail App Password** (for email import):
   - Go to: https://myaccount.google.com/apppasswords
   - Generate an app password (do NOT use your regular Gmail password)

## Usage

### Command Line Interface

```bash
# Add a transaction
budget add cash "Coffee" 5.50 --category Food
budget add card "Lunch" 12.50 --card Visa --category Food

# List recent transactions
budget list
budget list --limit 20
budget list --category Food

# Add a category
budget category add Food "Food and dining"
budget category list

# Check/set balances
budget balance show
budget balance set cash 100.0

# Set spending limits
budget limit set 500 --period monthly --category Food
budget limit check --category Food

# View reports
budget report daily --days 7
budget report category --month 10

# Auto-import from PDF (bank statement, credit card statement)
budget import pdf statement.pdf
budget import pdf statements/ --context "credit card statement"

# Auto-import from images (receipts)
budget import image receipt.jpg
budget import image receipts/ --context "store receipt"

# Auto-import from Gmail
budget import email --email your@gmail.com --provider gmail --days 30

# Use local LLM (LM Studio) instead of Anthropic
budget import pdf statement.pdf --provider local
budget import image receipt.jpg --provider local --base-url http://localhost:1234/v1
budget import email --email your@gmail.com --llm-provider local --model "llama-3.1-8b"

# Use Gemma 3 multimodal for direct image analysis (no OCR needed)
budget import image receipt.jpg --provider local --model "gemma-3-12b"

# Disable multimodal and use OCR instead
budget import image receipt.jpg --provider local --no-multimodal
```

### Python API

```python
from budget import Budget

# Create a budget tracker
budget = Budget()

# Add transactions
txn_id = budget.add_transaction("cash", "Coffee", 5.50, category="Food")
budget.add_transaction("card", "Lunch", 12.50, card="Visa", category="Food")

# Get recent transactions
recent = budget.get_recent_transactions(10)
for txn in recent:
    print(f"{txn.description}: ${txn.amount}")

# Search transactions
food_txns = budget.search_transactions(category="Food")

# Manage categories
budget.add_category("Food", "Food and dining")
budget.add_category("Transport", "Transportation costs")

# Check balances
balances = budget.get_all_balances()
budget.update_balance("cash", 100.0)

# Set spending limits
budget.set_spending_limit(500.0, period="monthly", category="Food")

# Check limits
result = budget.check_spending_limit(category="Food", period="monthly")
print(f"Spent: ${result['spent']:.2f} / ${result['limit']:.2f}")

# Get reports
daily = budget.get_daily_spending(days=7)
by_category = budget.get_spending_by_category(2025, 10)

# Auto-import from PDF (with Anthropic)
from budget.importers import PDFImporter
pdf_importer = PDFImporter()
transactions = pdf_importer.extract_from_file("statement.pdf")
stats = budget.import_transactions(transactions, "pdf")
print(f"Imported {stats['imported']}, skipped {stats['duplicates']} duplicates")

# Auto-import from PDF (with local LLM)
pdf_importer = PDFImporter(provider="local", base_url="http://localhost:1234/v1", model="llama-3.1-8b")
transactions = pdf_importer.extract_from_file("statement.pdf")
stats = budget.import_transactions(transactions, "pdf")

# Auto-import from images (with OCR)
from budget.importers import ImageImporter
img_importer = ImageImporter()
transactions = img_importer.extract_from_file("receipt.jpg")
stats = budget.import_transactions(transactions, "image")

# Auto-import with Gemma 3 multimodal (direct image analysis, no OCR)
img_importer = ImageImporter(
    provider="local",
    model="gemma-3-12b",
    use_multimodal=True  # Images normalized to 896x896 automatically
)
transactions = img_importer.extract_from_file("receipt.jpg")
stats = budget.import_transactions(transactions, "image")

# Auto-import from email
from budget.importers import EmailImporter
email_importer = EmailImporter()
email_importer.connect_gmail("your@gmail.com", "app-password")
transactions = email_importer.scan_for_transactions(days=30)
stats = budget.import_transactions(transactions, "email")
email_importer.disconnect()
```

## Project Structure

```
budget/
├── budget.py         # Main Budget class with all functionality
├── models.py         # SQLAlchemy database models
├── cli.py            # Command-line interface
├── utils.py          # Utility functions (hashing, deduplication)
├── importers/        # Auto-import modules
│   ├── __init__.py
│   ├── llm.py        # LLM-based transaction extraction (Anthropic)
│   ├── llm_local.py  # Local LLM extraction (LM Studio)
│   ├── pdf.py        # PDF importer
│   ├── image.py      # Image/OCR importer
│   └── email.py      # Email importer (Gmail, Outlook)
└── __init__.py       # Package exports

tests/
└── test_budget.py    # All tests

pyproject.toml        # Project configuration
README.md            # This file
```

## Database

The application uses SQLite for data storage. The database file (`budget.db` by default) is created automatically on first use.

**Database location:**

- Default: `./budget.db`
- Custom: Set via `BUDGET_DB_NAME` environment variable or pass to `Budget(db_name="...")`

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=budget

# Run specific test file
pytest tests/test_budget.py -v
```

### Dependencies

**Core:**

- **sqlalchemy** (>=2.0.0): Database ORM
- **click** (>=8.0.0): CLI framework

**Auto-Import** (optional):

- **anthropic** (>=0.18.0): Claude API for LLM-based extraction
- **openai** (>=1.0.0): OpenAI-compatible client for local LLM (LM Studio)
- **pdfplumber** (>=0.10.0): PDF text extraction
- **pytesseract** (>=0.3.10): OCR for images
- **Pillow** (>=10.0.0): Image processing

**Development:**

- **pytest** (>=8.0.0): Testing framework
- **pytest-cov** (>=4.1.0): Coverage reporting

## Examples

### Track Daily Expenses

```python
from budget import Budget

budget = Budget()

# Set up categories
budget.add_category("Food", "Meals and groceries")
budget.add_category("Transport", "Bus, taxi, etc.")
budget.add_category("Entertainment", "Movies, games, etc.")

# Add today's transactions
budget.add_transaction("cash", "Morning coffee", 5.50, category="Food")
budget.add_transaction("card", "Lunch", 12.00, card="Visa", category="Food")
budget.add_transaction("cash", "Bus fare", 2.50, category="Transport")

# Check today's spending
from datetime import datetime
now = datetime.now()
spending = budget.get_spending_by_category(now.year, now.month)
total = sum(spending.values())
print(f"Total spent this month: ${total:.2f}")
```

### Set Monthly Budget

```python
from budget import Budget

budget = Budget()

# Set monthly limits
budget.set_spending_limit(500.0, period="monthly", category="Food")
budget.set_spending_limit(100.0, period="monthly", category="Transport")

# Check if you're within budget
result = budget.check_spending_limit(category="Food", period="monthly")
if result["exceeded"]:
    print(f"Over budget by ${abs(result['remaining']):.2f}!")
else:
    print(f"${result['remaining']:.2f} remaining")
```

## License

MIT License
