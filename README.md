# Aether AI Agent 🚀

A professional-grade AI coding assistant that runs directly in your terminal. Aether reads your code, writes files with surgical precision, runs commands safely, and helps you build faster — all from a beautifully designed CLI.

## ✨ Features

### Core
- **Asynchronous Architecture** — Fully asynchronous operations leveraging `asyncio` and `AsyncOpenAI` for concurrent processing, parallel tool runs, and streaming.
- **Rich Markdown Rendering** — AI responses are rendered with full Markdown formatting (headers, code blocks, lists, bold/italic) via Rich's live display.
- **Streaming with Live Preview** — Watch responses render in real-time inside a styled panel with an animated thinking spinner.
- **Surgical File Editing** — The `edit_file` tool makes precise search-and-replace edits with color-coded diff previews, instead of rewriting entire files.
- **SQLite Session Persistence** — Session storage is powered by a SQLite database (`~/.aether_sessions/aether.db`), auto-migrating older JSON sessions.
- **Project-Specific Rules** — Customizes agent behavior per repository by auto-loading `.aether_rules` or `.cursorrules` from the current working directory.
- **Smart Autocomplete** — `@`-mention files with Tab completion that respects `.gitignore` and supports directory traversal.

### Tools
Aether has 9 built-in tools the AI can use:

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents before making changes |
| `write_file` | Create new files (with preview) |
| `edit_file` | Surgical search-and-replace on existing files (with diff preview) |
| `run_command` | Execute shell commands (supports background execution; safe commands auto-run, dangerous ones require approval) |
| `check_background_task` | Check the status and read recent output of a command running in the background |
| `kill_background_task` | Kill a running background task |
| `list_directory` | List files/folders with sizes, respecting `.gitignore` |
| `grep_search` | Search for text or regex patterns across the codebase |
| `find_files` | Find files by glob pattern (e.g., `*.py`, `Dockerfile`) |

### Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/model [name]` | View or switch the active AI model |
| `/clear` | Clear conversation history |
| `/drop` | Drop attached files/URLs/commands from history to save tokens |
| `/save [name]` | Save current conversation to SQLite database |
| `/load [name]` | Load a previously saved conversation |
| `/checkpoint [name]` | Save a conversation snapshot to memory |
| `/restore [name]` | Restore a saved conversation checkpoint |
| `/usage` | Show token usage, estimated session cost (USD), and statistics |
| `/commit` | Auto-generate a commit message for staged/unstaged changes and commit them |
| `/compact` | Summarize older messages using AI (fallback to text-summarization) to save tokens |
| `/undo` | Undo the last file modification |
| `/retry` | Retry the last message |
| `/copy` | Copy last AI response to clipboard |
| `/export [file]` | Export conversation to a Markdown file |
| `/config` | View current configuration |
| `/mcp` | View configured MCP servers and their connection status |

### Safety & UX
- **Command Safety** — Read-only commands (`ls`, `cat`, `git status`, etc.) auto-execute. Destructive commands (`rm`, `sudo`, etc.) always require confirmation.
- **`--yolo` Mode** — Auto-approve all operations for power users.
- **Background Tasks** — Run builds, tests, or other long-running tasks asynchronously while continuing to interact with Aether.
- **File Backups** — Every file modification creates a backup. Use `/undo` to restore.
- **Multi-line Input** — End a line with `\` to continue on the next line.
- **Session Persistence** — Conversations auto-save on exit to SQLite. Use `/save` and `/load` to manage.
- **Cost Tracking & Token Usage** — Live tracking of input/output tokens, session duration, and estimated session cost in USD.
- **Structured Logging** — Rotated file logging at `~/.aether_logs/aether.log` plus verbose console debugging logs via `--verbose`.
- **Graceful Error Recovery** — Helpful hints for common API errors (invalid key, rate limits, timeouts).

## Dependencies

- `openai` — OpenAI-compatible API client
- `python-dotenv` — Environment variable management
- `rich` — Rich text, Markdown rendering, panels, tables, and live display
- `prompt_toolkit` — Interactive command line with autocomplete

## Installation

### 1. Python (pip / pipx) — Recommended
```bash
pipx install aether-ai-cli
# Or:
pip install aether-ai-cli
```

### 2. NPM (Node.js)
```bash
npm install -g aether-ai-cli
```

### 3. Homebrew (macOS)
```bash
brew tap irtaza302/aether-agent
brew install aether
```

### 4. Local Development
```bash
git clone https://github.com/irtaza302/aether-agent.git
cd aether-agent
pip install -r requirements.txt
python aether.py
```

## Usage

```bash
aether
```

On first launch, you'll be prompted for your [OpenRouter API key](https://openrouter.ai/keys). It's saved securely to `~/.aether_config.json`.

### Command Line Arguments

| Flag | Description |
|------|-------------|
| `--version` | Show version |
| `--model <name>` | Override the default model for this session |
| `--reset-key` | Clear and re-enter your API key |
| `--set-base-url <url>` | Set custom API base URL (e.g., `http://localhost:11434/v1` for Ollama) |
| `--yolo` | Auto-approve all file writes and command executions |
| `--verbose` | Enable verbose logging output to the console |

### Attaching Context (`@`)

Type `@` followed by a filename, directory, web URL, or command to give Aether context. Autocomplete filters out `.gitignore`d files:

- **Files:** `@aether.py` attaches the file contents.
- **Directories:** `@tests/` generates and attaches a visual directory tree respecting `.gitignore`.
- **URLs:** `@https://docs.python.org/...` fetches the webpage, converts it to markdown, and attaches it.
- **Commands:** `@cmd:"pytest"` or `@cmd:ls` securely runs the command in the background and injects its `stdout` and `stderr` directly into the prompt.

```
👤 You
❯ Can you refactor @aether.py to use async?

👤 You
❯ Explain this output: @cmd:"npm run build"
```

### Multi-line Input

End a line with `\` to continue typing on the next line:

```
👤 You
❯ Write a function that \
⋮  takes a list of numbers \
⋮  and returns the sorted unique values
```

## Configuration

Aether stores its config in `~/.aether_config.json`:

```json
{
  "OPENROUTER_API_KEY": "sk-or-...",
  "API_BASE_URL": "https://openrouter.ai/api/v1",
  "DEFAULT_MODEL": "anthropic/claude-sonnet-4"
}
```

### Model Context Protocol (MCP) Support

Aether supports integrating with external [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers to extend its capabilities (e.g. connecting to local databases, searching the web, or accessing custom APIs).

To configure MCP servers, add an `"mcp_servers"` block to your `~/.aether_config.json`:

```json
{
  "mcp_servers": {
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "~/test.db"]
    },
    "everything": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-everything"]
    }
  }
}
```

When you start Aether, it will automatically connect to these servers and make their tools available to the AI.

Sessions are saved in a SQLite database at `~/.aether_sessions/aether.db`, and file backups are placed in `~/.aether_backups/`.

### 📂 Project-Specific Rules

Aether supports loading custom, project-specific rules files (such as `.aether_rules` or `.cursorrules`) from the root of your project directory. 
When Aether starts, it checks for these files in the current working directory in the following order:
1. `.aether_rules`
2. `.cursorrules`

If one is found, Aether automatically appends its contents to the system prompt. This allows you to enforce codebase-specific styling guidelines, coding standards, or project rules without editing Aether's global configuration.

### 🔄 Background Task Management

For long-running processes (e.g., running test suites, starting local dev servers, or building bundles), you can run commands in the background asynchronously:
- Aether's `run_command` tool supports a boolean `background` parameter. If set to `true`, the tool immediately returns a unique `task_id` (e.g., `bg_a1b2c3d4`).
- You can inspect the status and read the recent stdout/stderr output of a background task using the `check_background_task` tool.
- You can terminate any active background task using the `kill_background_task` tool.

This allows you to continue discussing other topics or refactoring files with Aether while your tests or builds run in parallel.

### 💰 Cost Tracking

Aether dynamically estimates session costs in USD for known models based on token usage:
- Input and output tokens are tracked in real-time.
- The estimated session cost is displayed in the CLI status bar and summary tables (via the `/usage` command).
- The cost calculations support popular models from Anthropic (Claude 3.5/3.7 Sonnet, Opus, Haiku), Google (Gemini 2.5 Pro/Flash), and OpenAI (GPT-4o, o1, o3-mini).

### 📌 Session Checkpoints & Restoring

You can save and restore conversation snapshots at any point during your session:
- `/checkpoint [name]`: Save the current conversation messages history as a named snapshot in memory.
- `/restore [name]`: Revert the conversation history to the specified checkpoint. If run without a name, it lists all currently active checkpoints.

This is extremely useful when experimenting with different implementation approaches or when recovering from an unintended direction.

### 📝 Structured Logging

All internal activities, tool calls, and API events are written to a rotating file logger:
- Logs are located at `~/.aether_logs/aether.log`.
- Up to three rotated log files are kept (5 MB per file limit).
- You can run Aether with the `--verbose` flag to mirror log output directly to the console stderr stream.

## Publishing & Development

Use the included `publish.sh` script to build and publish across all platforms (PyPI, NPM, and PyInstaller binaries).