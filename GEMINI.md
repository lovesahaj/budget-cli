# GEMINI.md

This file provides guidance to Gemini when working with code in this repository.

## Project Overview

Personal Budget Tracker - A command-line application for tracking daily transactions, account balances, spending limits, and financial analytics. Built with Python using Typer (CLI), Rich (terminal UI), Textual (TUI), and SQLite (database).

## Running the Application

This project uses `uv` for dependency management. Always prefix Python commands with `uv run`:

```bash
# Show all available commands
uv run budget_cli.py --help

# Run specific commands
uv run budget_cli.py balance
uv run budget_cli.py list-transactions --limit 10
uv run budget_cli.py add-transaction cash "Coffee" 3.50
uv run budget_cli.py tui  # Launch interactive TUI

# Interactive mode for multiple entries
uv run budget_cli.py interactive
```

## Architecture

### Three-Layer Design

1. **budget_core.py** - Core business logic and data layer
   - `BudgetManager` class: Main controller for all database operations
   - Custom exceptions: `BudgetError`, `DatabaseError`, `ValidationError`
   - Context manager support for safe resource management
   - Database schema migrations handled automatically

2. **budget_cli.py** - Command-line interface layer
   - Built with Typer framework
   - Each `@app.command()` decorated function is a CLI command
   - Imports and uses `BudgetManager` from budget_core
   - All commands call `init_budget_manager()` to setup database connection
   - Error handling wraps `BudgetError` exceptions

3. **budget_tui.py** - Terminal user interface (optional interactive mode)
   - Built with Textual framework
   - Lazygit-style interface with vim-like keybindings
   - Displays: balances, daily spending chart, recent transactions table
   - Launched via `tui` command

### Database Schema

SQLite database (`budget.db`) with 5 tables:

- `cards` - Payment cards/accounts
- `categories` - Transaction categories
- `transactions` - All spending records (includes category column)
- `balances` - Current balance per account type
- `spending_limits` - Budget limits by category/source/period

Schema migrations run automatically on first connection after updates.

## Key Implementation Details

### Transaction Flow

When adding a transaction:

1. Validate inputs (type, amount, card existence)
2. Check/update balance (with negative balance warnings)
3. Insert transaction record with optional category
4. Check spending limits and show warnings if exceeded

### Data Return Types

`BudgetManager` methods return dictionaries (not tuples) for transactions:

```python
# New format (dict with keys)
{"id": 1, "type": "card", "card": "Wise", "category": "Food", ...}

# Old format was: (type, card, description, amount, timestamp)
```

**Important:** When modifying transaction-related code, use dictionary access with keys like `t['id']`, `t['category']`, etc.

### Error Handling Pattern

All `BudgetManager` methods wrap SQLite errors:

```python
try:
    # database operation
except sqlite3.Error as e:
    raise DatabaseError(f"Context: {e}")
```

CLI commands catch these and display user-friendly Rich-formatted messages.

### Adding New Features

When adding new CLI commands:

1. Add method to `BudgetManager` in budget_core.py
2. Add error handling (try/except with custom exceptions)
3. Create `@app.command()` in budget_cli.py
4. Call `init_budget_manager()` at start of command
5. Wrap in `try/except BudgetError` block
6. Use Rich formatting for output

When modifying database schema:

1. Update table creation in `connect_db()`
2. Add migration logic to `_migrate_schema()`
3. Test with existing budget.db to ensure backward compatibility

## Currency

Application uses GBP (£) hardcoded throughout. To change currency:

- Search for "£" symbol in all Python files
- Update display formatting in CLI and TUI
