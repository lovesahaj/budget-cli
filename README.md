# Budget Tracker MCP Server

A personal budget tracking MCP (Model Context Protocol) server for Claude Desktop. Manage daily transactions, account balances, and spending limits directly through conversation with Claude.

## Features

- **MCP Server Integration**: Use with Claude Desktop for natural conversation-based budget tracking
- **Transaction Management**: Track income and expenses with categories
- **Bulk Transaction Import**: Add multiple transactions at once
- **Balance Tracking**: Monitor account balances (cash, cards)
- **Spending Limits**: Set and check spending limits by category or source
- **Reports**: View spending by category and daily trends
- **Auto-Import**: Automatically import transactions from:
  - **PDF files** (bank statements, credit card statements, receipts)
  - **Images** (photos of receipts using OCR or direct multimodal analysis)
  - **Email** (Gmail/Outlook - scans for transaction emails)
- **Smart Deduplication**: Automatically detects and prevents duplicate transactions
- **Multimodal Support**: Direct image analysis with Gemma 3 (no OCR needed, 896x896 normalized)
- **Python API**: Programmatic access for advanced use cases

## Installation

### Prerequisites

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or pip
- [Claude Desktop](https://claude.ai/download) (for MCP server integration)
- Docker (optional, for containerized deployment)

### Quick Start

```bash
# Install dependencies
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

### MCP Server

The MCP (Model Context Protocol) server allows you to use the budget tracker with Claude Desktop and other MCP clients.

#### Running with Docker

The easiest way to run the MCP server is with Docker.

```bash
# Build and start the server in the background
docker-compose up -d

# Check that the container is running
docker ps
```

The MCP server uses stdio for communication (not HTTP), so it doesn't expose a web interface.

#### Usage with Claude Desktop

To use this MCP server with Claude Desktop, you can run it either locally or with Docker.

##### With Local Development Server

This method is recommended for development.

**macOS/Linux**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "budget-tracker": {
      "command": "/Users/lovess/.local/bin/uv",
      "args": ["--directory", "/Users/lovess/Documents/budget", "run", "budget-mcp"],
      "env": {
        "BUDGET_DB_NAME": "budget.db"
      }
    }
  }
}
```

**Note:** If `uv` is installed in a different location on your system, use `which uv` to find the full path and update the `command` field accordingly.

**Windows**

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "budget-tracker": {
      "command": "C:\\Users\\YourUsername\\.local\\bin\\uv.exe",
      "args": ["--directory", "C:\\path\\to\\budget", "run", "budget-mcp"],
      "env": {
        "BUDGET_DB_NAME": "budget.db"
      }
    }
  }
}
```

**Important:**

- Replace `C:\\path\\to\\budget` with the actual absolute path to your budget project directory
- Find your `uv.exe` location using `where uv` in PowerShell and update the `command` field accordingly.

##### With Docker

This method is recommended for a more stable setup.

1.  **Start the server:**

    ```bash
    docker-compose up -d
    ```

2.  **Configure Claude Desktop:**

    The `command` for Claude Desktop will use `docker exec` to run the `budget-mcp` command inside the running container.

    **macOS/Linux**

    ```json
    {
      "mcpServers": {
        "budget-tracker": {
          "command": "docker",
          "args": ["exec", "-i", "budget-mcp-server", "uv", "run", "budget-mcp"],
          "env": {}
        }
      }
    }
    ```

    **Windows**

    ```json
    {
      "mcpServers": {
        "budget-tracker": {
          "command": "docker.exe",
          "args": ["exec", "-i", "budget-mcp-server", "uv", "run", "budget-mcp"],
          "env": {}
        }
      }
    }
    ```

    **Note:** The container name `budget-mcp-server` is set in the `docker-compose.yml` file. If you rename the container, update this configuration accordingly.

#### Using with Claude Desktop

Once configured, you can interact with your budget tracker naturally through Claude. Here are some example interactions:

**Adding Transactions:**
```
Add a coffee purchase for $5.50 in cash, category Food
```

**Bulk Import:**
```
Add these transactions:
- Lunch at McDonald's for $12.50 (Visa card, Food)
- Gas for $45.00 (Mastercard, Transportation)
- Groceries for $85.30 (cash, Food)
```

**Viewing and Searching:**
```
Show me my recent transactions
Search for all food transactions over $20 this month
```

**Balances and Reports:**
```
What are my current balances?
Show me spending by category for this month
Show daily spending for the last 7 days
```

**Spending Limits:**
```
Set a monthly spending limit of $500 for Food
Check my spending limit for Food this month
```

#### Available Tools

The MCP server exposes the following tools:

**Transaction Tools:**
- `add_transaction` - Add a single transaction
- `add_multiple_transactions` - Add multiple transactions at once (bulk import)
- `list_transactions` - List recent transactions with filters
- `search_transactions` - Advanced search with date range and amount filters
- `update_transaction` - Update an existing transaction
- `delete_transaction` - Delete a transaction

**Category & Card Tools:**
- `add_category` - Add a new category
- `list_categories` - List all categories
- `add_card` - Add a new payment card
- `list_cards` - List all cards

**Balance Tools:**
- `get_balance` - Get balance for a specific account
- `get_all_balances` - Get all balances
- `update_balance` - Update an account balance

**Spending Limit Tools:**
- `set_spending_limit` - Set spending limits by period/category/source
- `check_spending_limit` - Check spending against limits

**Report Tools:**
- `get_daily_spending` - Get daily spending report
- `get_spending_by_category` - Get spending breakdown by category

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
├── mcp_server.py     # MCP server entry point
├── utils.py          # Utility functions (hashing, deduplication)
├── mcp/              # MCP server modules
│   ├── __init__.py
│   ├── tools.py      # Tool definitions organized by category
│   └── handlers.py   # Tool handlers organized by domain
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

docker/
├── Dockerfile        # Container image definition
├── docker-compose.yml # Container orchestration
└── entrypoint.sh     # Container startup script

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

