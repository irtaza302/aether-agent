# Aizen AI Agent CLI Codebase Analysis for Semantic Search Integration

This report outlines the structural components of the Aizen AI Agent CLI and proposes a design and implementation strategy for integrating **Semantic Search** (vector embeddings based search) into the terminal interface and the tool calling framework.

---

## 1. CLI Entry Points & Slash Commands

### Entry Points
- **Package script mapping:** In `pyproject.toml` (lines 51–52), the terminal command `aizen` maps to the function `aizen.main:main`:
  ```toml
  [project.scripts]
  aizen = "aizen.main:main"
  ```
- **Main function:** Inside `aizen/main.py`, `main()` runs `asyncio.run(main_loop())`.
- **Interactive Prompt Loop:** The interactive CLI loop is managed inside `main_loop()` (lines 324–476 of `aizen/main.py`) using `prompt_toolkit.PromptSession`. It processes multiline input and command syntax.

### Slash Commands Architecture
Slash commands are prefixed with `/`. 
- **Trigger and Delegation:** In `aizen/main.py` (lines 371–397):
  ```python
  if user_input.strip().startswith("/"):
      if user_input.strip().startswith("/auto"):
          # ... handles autonomous mode in-place ...
      else:
          should_retry = await handle_slash_command(
              user_input.strip(), messages, token_tracker, mcp_manager, client
          )
          if should_retry and messages and messages[-1]["role"] == "user":
              pass  # Fall through to the agent loop
          else:
              continue
  ```
- **Command Registry:** `SLASH_COMMANDS` in `aizen/commands.py` (lines 28–48) registers active interactive commands:
  ```python
  SLASH_COMMANDS = [
      ("/help", "Show all available commands"),
      ("/model", "View or switch the active model"),
      # ...
  ]
  ```
- **Command Handler:** The `handle_slash_command(...)` function in `aizen/commands.py` parses commands and implements the business logic (lines 141–738).
- **Auto-completion:** `AizenCompleter` in `aizen/commands.py` (lines 54–139) automatically completes registered slash commands when the user types `/` in the prompt.

### 💡 Recommendation for Slash Command `/search`
1. Register `/search` in `SLASH_COMMANDS` in `aizen/commands.py`:
   ```python
   ("/search", "Perform semantic search across the codebase workspace")
   ```
2. Handle the command in `handle_slash_command(...)` inside `aizen/commands.py`:
   ```python
   elif cmd == "/search":
       if not arg:
           console.print(f"  [{Theme.WARNING}]Please provide a search query. Usage: /search <query>[/{Theme.WARNING}]\\n")
       else:
           console.print(f"  [{Theme.MUTED}]Searching code with semantic embeddings...[/{Theme.MUTED}]")
           results = await perform_semantic_search(arg)  # to be implemented
           # Format results with Rich table/panel
   ```
3. Add a companion command `/reindex` to force indexing/indexing update for the workspace.

---

## 2. LLM Provider Configurations & API Wrappers

### Configuration Structure
- **Global Config Path:** `~/.aizen_config.json` (defined as `CONFIG_PATH` in `aizen/config.py:28`).
- **Config Loader:** `load_config()` in `aizen/config.py:214` merges the global configuration with workspace-local config files (`.aizen_config.json` in the current working directory).
- **Active Model Management:** Managed via `get_active_model()` and `set_active_model(...)` in `aizen/config.py` using a thread lock for thread safety.

### Client Wrapper
- **API Client initialization:** In `aizen/main.py` (line 230):
  ```python
  client = AsyncOpenAI(base_url=api_base, api_key=api_key)
  ```
  Where `api_base` defaults to OpenRouter (`https://openrouter.ai/api/v1`) and `api_key` is fetched dynamically.
- **Embedding Generation Capability:** Since `client` is an instance of `AsyncOpenAI`, it has built-in support for generating embeddings:
  ```python
  response = await client.embeddings.create(
      input=["text to embed"],
      model="openai/text-embedding-3-small"  # or user-configured model
  )
  embedding = response.data[0].embedding
  ```

### 💡 Recommendation for Embedding Generation
- Introduce a new configuration option `EMBEDDING_MODEL` in `~/.aizen_config.json` (defaulting to e.g., `"openai/text-embedding-3-small"` if OpenRouter is used, or `"text-embedding-3-small"` for direct OpenAI).
- Implement an asynchronous wrapper utility `get_embeddings(client, texts: list[str]) -> list[list[float]]` in a new file `aizen/embeddings.py` (or inside `aizen/utils.py`).

---

## 3. Tool Calling Framework

### Tool Schemas
All core tools are defined as OpenAI tool function schemas in `aizen/tools/dispatcher.py` (lines 31–302) inside the global `tools` list.

### Tool Execution routing
The function `execute_tool(tool_call, auto_approve)` (lines 307–438 in `aizen/tools/dispatcher.py`) handles:
1. JSON argument decoding and automatic repair attempt.
2. Routing based on `tool_call.function.name`.
3. Invocation of the tool implementation.

### 💡 Integration of `semantic_search` Tool
1. **Schema registration:** Add the following function schema to the `tools` list in `aizen/tools/dispatcher.py`:
   ```json
   {
       "type": "function",
       "function": {
           "name": "semantic_search",
           "description": "Searches the codebase semantically for concepts, function descriptions, or code blocks rather than exact text matching. Returns relevant snippets.",
           "parameters": {
               "type": "object",
               "properties": {
                   "query": {
                       "type": "string",
                       "description": "The search query explaining the concept or looking for the codebase functionality."
                   },
                   "limit": {
                       "type": "integer",
                       "description": "Maximum number of code snippets to return (default: 5)."
                   }
               },
               "required": ["query"]
           }
       }
   }
   ```
2. **Execution routing:** Add a routing branch in `execute_tool` in `aizen/tools/dispatcher.py`:
   ```python
   elif func_name == "semantic_search":
       query = str(args.get("query", ""))
       limit = int(args.get("limit", 5))
       tool_label.append(f" → '{query}' (limit {limit})", style="dim")
       console.print(tool_label)
       # Run similarity search
       return truncate_output(run_semantic_search_tool_impl(query, limit))
   ```

---

## 4. App Data & Session Directories

### Directory Structure
`aizen/config.py` defines standard user-level directories:
- `~/.aizen_config.json`: Configuration settings.
- `~/.aizen_sessions/`: Contains chat histories.
- `~/.aizen_backups/`: Contains state backups.

### Database Architecture
`aizen` leverages a central SQLite database to store sessions rather than individual files, defined in `aizen/session.py` (lines 53–96):
- DB Path: `~/.aizen_sessions/aizen.db`.
- DB Manager: `_get_db()` returns a singleton thread-safe `sqlite3.Connection`.

### 💡 Recommendation for Vector Cache/Database Location
- **Cache Location:** Centralized inside `~/.aizen_vector_cache/vector_cache.db` (or a dedicated table inside `~/.aizen_sessions/aizen.db`). Centralized SQLite database separates semantic index cache from raw chat sessions while avoiding polluting local codebase repositories with untracked directories.
- **Index Identification:** Workspaces are identified by their absolute directory path (`os.getcwd()`).
- **Database Schema Proposal:**
  ```sql
  CREATE TABLE IF NOT EXISTS file_index (
      workspace_path TEXT,
      filepath TEXT,
      last_modified REAL,
      file_hash TEXT,
      PRIMARY KEY (workspace_path, filepath)
  );

  CREATE TABLE IF NOT EXISTS chunk_embeddings (
      workspace_path TEXT,
      filepath TEXT,
      chunk_index INTEGER,
      content TEXT,
      embedding BLOB,  -- Store serialized list of floats (JSON or binary array)
      PRIMARY KEY (workspace_path, filepath, chunk_index),
      FOREIGN KEY (workspace_path, filepath) REFERENCES file_index(workspace_path, filepath) ON DELETE CASCADE
  );
  ```

---

## Proposing a Dependency-Free Embeddings/Similarity Strategy
To keep the Aizen CLI lightweight and easily installable (without requiring compilation of native vector search libraries like `faiss`, `chromadb`, or `sqlite-vec` extension):
1. **Embedding generation:** Call OpenRouter/OpenAI embeddings API.
2. **Similarity calculation:** Query the SQLite database for all embeddings of the current workspace, load them into memory, and compute cosine similarity in pure Python:
   ```python
   import math

   def cosine_similarity(v1: list[float], v2: list[float]) -> float:
       dot_product = sum(a * b for a, b in zip(v1, v2))
       magnitude_v1 = math.sqrt(sum(a * a for a in v1))
       magnitude_v2 = math.sqrt(sum(b * b for b in v2))
       if not magnitude_v1 or not magnitude_v2:
           return 0.0
       return dot_product / (magnitude_v1 * magnitude_v2)
   ```
3. Since a typical software project has under 5,000 code chunks, an in-memory similarity scan takes less than **5–15 milliseconds** in pure Python. This provides a fast, robust, and zero-dependency solution.

---

## 5. Implementation Strategy & Milestone Decomposition

### **R1: Core Embedding & Vector Storage Engine (Foundational)**
- **Objective:** Create the database storage, file parser/chunker, API wrapper for embeddings, and an incremental sync utility.
- **Steps:**
  1. Create `aizen/embeddings.py` to handle the `sqlite3` database table setup.
  2. Implement an incremental sync engine that:
     - Scans workspace files (respecting `.gitignore` using `aizen/utils.py:should_ignore`).
     - Detects changed/new files (by comparing modification times or hashes).
     - Splits files into chunks (e.g. 50-line window with 10-line overlap).
     - Fetches embeddings in batches from OpenRouter/OpenAI.
     - Saves/updates chunks and embeddings in the database.
  3. Add test suite in `tests/test_embeddings.py`.

### **R2: Slash Command Integration (`/search`)**
- **Objective:** Allow interactive CLI users to perform semantic searches directly.
- **Steps:**
  1. Implement workspace indexing command triggers:
     - `/reindex` to scan the workspace and perform an incremental update.
     - `/search <query>` to perform a search and print a formatted output.
  2. Register `/search` and `/reindex` in `SLASH_COMMANDS` and `handle_slash_command` inside `aizen/commands.py`.
  3. Add unit and integration tests in `tests/test_search_commands.py`.

### **R3: Tool Integration (`semantic_search` tool)**
- **Objective:** Expose semantic search capability to the AI model so it can autonomously navigate large codebases.
- **Steps:**
  1. Define `semantic_search` schema in `tools` within `aizen/tools/dispatcher.py`.
  2. Map it in `execute_tool` to invoke the vector search function and format outputs for the model's consumption.
  3. Update Aizen's system prompt (defined in `aizen/config.py`) to guide the model on when to use `semantic_search` (e.g., when exact `grep_search` results are empty or for conceptual lookups).
  4. Write test scenarios in `tests/test_semantic_search_tool.py`.
