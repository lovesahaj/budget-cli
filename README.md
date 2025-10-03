# Personal Budget Tracker

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A powerful command-line application for tracking daily transactions, managing account balances, setting spending limits, and analyzing your financial data.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Account Management](#account-management)
  - [Transactions](#transactions)
  - [Categories](#categories)
  - [Search & Analytics](#search--analytics)
  - [Budget Limits](#budget-limits)
  - [Export Data](#export-data)
- [Interactive Modes](#interactive-modes)
- [Database](#database)
- [Requirements](#requirements)
- [Tips](#tips)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- 💰 **Multi-Account Support** - Track cash and multiple payment cards
- 📊 **Transaction Categories** - Organize spending by custom categories
- 🔍 **Advanced Search** - Filter transactions by date, amount, category, or card
- 📈 **Spending Analytics** - Monthly breakdowns by source or category
- ⚠️ **Budget Limits** - Set and monitor spending limits with automatic alerts
- 📤 **Export Data** - Export transactions to CSV or JSON
- 🖥️ **Dual Interface** - CLI commands or interactive TUI (Terminal UI)
- ✏️ **Transaction Management** - Edit or delete transactions as needed

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for Python dependency management.

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/lovesahaj/budget-cli.git
cd budget-cli

# Dependencies will be installed automatically when you run commands
```

## Quick Start

```bash
# View your current balances
uv run budget_cli.py balance

# Add funds to an account
uv run budget_cli.py add-funds --cash 100

# Record a transaction
uv run budget_cli.py add-transaction cash "Groceries" 25.50
uv run budget_cli.py add-transaction card "Coffee" 3.50 --card Wise --category "Food & Drink"

# View recent transactions
uv run budget_cli.py list-transactions --limit 10

# Launch interactive mode
uv run budget_cli.py interactive

# Launch TUI (Terminal UI)
uv run budget_cli.py tui
```

## Usage

### Account Management

```bash
# Add funds
uv run budget_cli.py add-funds --cash 100
uv run budget_cli.py add-funds --card Wise --amount 500

# Add a new payment card
uv run budget_cli.py add-card "Revolut"

# View balances
uv run budget_cli.py balance
```

### Transactions

```bash
# Add a transaction
uv run budget_cli.py add-transaction cash "Lunch" 8.50
uv run budget_cli.py add-transaction card "Groceries" 45.20 --card ICICI --category Food

# List recent transactions
uv run budget_cli.py list-transactions --limit 20

# Edit a transaction
uv run budget_cli.py edit-transaction 5 --description "Updated description" --amount 10.00

# Delete a transaction
uv run budget_cli.py delete-transaction 5 --force
```

### Categories

```bash
# Add a category
uv run budget_cli.py add-category "Food & Drink" --description "All food and beverage expenses"
uv run budget_cli.py add-category "Transport"
uv run budget_cli.py add-category "Entertainment"

# List all categories
uv run budget_cli.py list-categories
```

### Search & Analytics

```bash
# Search transactions
uv run budget_cli.py search --query "coffee"
uv run budget_cli.py search --category Food --min 10 --max 50
uv run budget_cli.py search --start 2025-01-01 --end 2025-01-31

# Monthly spending report
uv run budget_cli.py monthly-spending
uv run budget_cli.py monthly-spending --year 2025 --month 9
uv run budget_cli.py monthly-spending --by-category
```

### Budget Limits

```bash
# Set spending limits
uv run budget_cli.py set-limit 500 --period monthly --category Food
uv run budget_cli.py set-limit 200 --period weekly --source Wise
uv run budget_cli.py set-limit 50 --period daily

# View all limits
uv run budget_cli.py list-limits
```

### Export Data

```bash
# Export to CSV
uv run budget_cli.py export transactions.csv --format csv

# Export to JSON
uv run budget_cli.py export transactions.json --format json

# Export with date range
uv run budget_cli.py export report.csv --start 2025-01-01 --end 2025-12-31
```

## Interactive Modes

### Interactive CLI Mode

For adding multiple transactions in one session:

```bash
uv run budget_cli.py interactive
```

This mode guides you through:
1. Adding funds to accounts
2. Recording multiple transactions with prompts
3. Creating new categories on-the-fly
4. Viewing final balances

### TUI (Terminal User Interface)

Launch a lazygit-style terminal interface:

```bash
uv run budget_cli.py tui
```

**Keybindings:**
- `r` - Refresh data
- `+`/`-` - Adjust daily spending chart window
- `h`/`l` - Focus left/right panel
- `j`/`k` - Navigate transactions (vim-style)
- `gg` - Jump to top
- `G` - Jump to bottom
- `Ctrl+d`/`Ctrl+u` - Page down/up
- `q` - Quit

## Database

All data is stored in a local SQLite database (`budget.db`). The database is created automatically on first run.

**Backup your data:**
```bash
cp budget.db budget.db.backup
```

## Requirements

- Python >= 3.13
- Dependencies (managed by uv):
  - typer >= 0.17.4
  - rich >= 13.7.1
  - textual >= 0.82.0

## Tips

- **Negative balances:** The app will warn you before allowing transactions that result in negative balances
- **Spending alerts:** When you exceed a spending limit, you'll see a warning immediately after the transaction
- **Category auto-create:** If you reference a non-existent category in a transaction, it will be created automatically
- **Transaction IDs:** Use `list-transactions` to find transaction IDs for editing or deleting

## Project Structure

```
budget/
├── __init__.py           # Package initialization
├── models.py            # Database models and schemas
├── database.py         # Database connection and setup
├── budget_core.py      # Core business logic
├── budget_cli.py       # Command-line interface
├── budget_tui.py       # Terminal UI implementation
├── transactions.py     # Transaction-related operations
├── categories.py       # Category management
├── cards.py           # Payment card management
├── limits.py          # Budget limits functionality
├── reports.py         # Reporting and analytics
├── exports.py         # Data export functionality
├── balances.py        # Balance tracking
└── exceptions.py      # Custom exceptions
```

### Key Components

1. **Core Components:**
   - `budget_core.py`: Contains the main business logic and coordinates between different modules
   - `models.py`: Defines SQLAlchemy models for database tables
   - `database.py`: Handles database connections and migrations

2. **Interface Layers:**
   - `budget_cli.py`: Command-line interface using Typer
   - `budget_tui.py`: Terminal UI using Textual framework

3. **Feature Modules:**
   - `transactions.py`: Transaction CRUD operations
   - `categories.py`: Category management
   - `cards.py`: Payment card operations
   - `limits.py`: Budget limit tracking
   - `reports.py`: Generates financial reports
   - `exports.py`: Handles data export
   - `balances.py`: Account balance tracking

### Data Flow

1. User input → CLI/TUI interface
2. Interface calls appropriate core function
3. Core logic validates and processes request
4. Database operations performed through models
5. Results returned to interface for display

## Getting Started with Development

First, let's understand the development workflow:

1. **Setting Up Your Environment**

```bash
# Clone the repository
git clone https://github.com/lovesahaj/budget-cli.git
cd budget-cli

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies with dev packages
uv pip install -e ".[dev]"
```

2. **Understanding the Dependencies**

The project uses several key dependencies:
- `typer`: For building the command-line interface
- `rich`: For beautiful terminal formatting
- `textual`: For the terminal user interface (TUI)
- `sqlalchemy`: For database operations
- Development tools:
  - `pytest`: For testing
  - `pytest-cov`: For test coverage reporting
  - `pytest-mock`: For mocking in tests

3. **Database Setup**

The application uses SQLite for data storage:
- Database file is created automatically as `budget.db`
- Tables are created based on models in `models.py`
- SQLAlchemy handles all database operations

4. **Adding New Features**

When adding new features:

a. **Plan Your Changes**
   - Determine which modules will be affected
   - Plan any new database models needed
   - Consider impacts on existing features

b. **Implementation Steps**
   - Add new models to `models.py` if needed
   - Implement core logic in appropriate module
   - Add CLI commands in `budget_cli.py`
   - Add TUI interface in `budget_tui.py` if needed
   - Write tests in `tests/` directory

c. **Testing Your Changes**
   ```bash
   # Run all tests
   pytest

   # Run tests with coverage
   pytest --cov=budget tests/

   # Run specific test file
   pytest tests/test_specific_file.py
   ```

5. **Code Style and Standards**

- The project follows PEP 8 guidelines
- Use type hints for all function parameters and returns
- Document all public functions and classes
- Keep functions focused and small
- Add tests for new functionality

## Development

```bash
# Clone the repository
git clone https://github.com/lovesahaj/budget-cli.git
cd budget-cli

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=budget tests/
```

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the tests to ensure everything works
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please make sure to update tests as appropriate and follow the existing code style.

## License

MIT License

Copyright (c) 2025 lovesahaj

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
