# Budget Tracker MCP Server

This project includes an MCP (Model Context Protocol) server that allows you to interact with your budget tracker through LLMs like Claude.

## What is MCP?

MCP (Model Context Protocol) is a protocol by Anthropic that allows LLMs to interact with external tools and data sources. This MCP server exposes all the budget tracker functionality as tools that an LLM can use to help you manage your finances.

## Installation

1. Install the project with MCP dependencies:

```bash
uv sync
```

2. The MCP server is now available as the `budget-mcp` command.

## Available Tools

The MCP server exposes the following tools:

### Transaction Management

- `add_transaction` - Add a new transaction (expense)
- `list_transactions` - List recent transactions with optional filters
- `search_transactions` - Advanced transaction search with date range and amount filters
- `update_transaction` - Update an existing transaction
- `delete_transaction` - Delete a transaction by ID

### Category Management

- `add_category` - Add a new transaction category
- `list_categories` - List all available categories

### Card Management

- `add_card` - Add a new payment card
- `list_cards` - List all payment cards

### Balance Management

- `get_balance` - Get balance for a specific type (cash or card name)
- `get_all_balances` - Get all balances
- `update_balance` - Update balance for a type

### Spending Limits

- `set_spending_limit` - Set a spending limit for a period
- `check_spending_limit` - Check spending against limits

### Reports

- `get_daily_spending` - Get daily spending for the last N days
- `get_spending_by_category` - Get spending breakdown by category for a month

## Usage with Claude Desktop

To use this MCP server with Claude Desktop, add it to your Claude configuration:

### macOS/Linux

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

### Windows

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
- Find your `uv.exe` location using `where uv` in PowerShell and update the `command` field accordingly

## Usage with Other MCP Clients

The MCP server can be used with any MCP-compatible client. Run it directly:

```bash
uv run budget-mcp
```

The server communicates via stdio (standard input/output).

## Database Configuration

By default, the server uses `budget.db` in the current directory. You can specify a different database by setting the `BUDGET_DB_NAME` environment variable:

```bash
export BUDGET_DB_NAME=/path/to/your/budget.db
uv run budget-mcp
```

## Example Interactions

Once connected to Claude Desktop, you can interact with your budget naturally:

- "Add a new transaction for $25 coffee at Starbucks using my Visa card"
- "Show me all my transactions from last week"
- "What's my total spending this month?"
- "Set a monthly spending limit of $2000"
- "How much have I spent on groceries this month?"
- "Show me a breakdown of my spending by category"
- "What's my current balance?"

Claude will automatically use the appropriate tools to help you manage your budget.

## Development

To test the MCP server locally:

```bash
# Run the server
uv run budget-mcp

# The server will wait for MCP protocol messages on stdin
# You can use an MCP client or the MCP Inspector for testing
```

## Troubleshooting

### "spawn uv ENOENT" error

This means Claude Desktop can't find the `uv` command. You need to use the full path to `uv`:

1. Find where `uv` is installed:
   ```bash
   which uv
   ```

2. Update the `command` field in your config with the full path (e.g., `/Users/lovess/.local/bin/uv`)

3. Restart Claude Desktop

### Server not appearing in Claude Desktop

1. Make sure the path in the config file is absolute and correct
2. Restart Claude Desktop after editing the config
3. Check Claude Desktop's logs for errors

### Database errors

Make sure the database file exists and is accessible. The server will create tables automatically on first run.

### Permission issues

Ensure the uv command is in your PATH and the project directory is readable.

## Security Note

The MCP server has full access to your budget database. Only use it with trusted LLM applications.
