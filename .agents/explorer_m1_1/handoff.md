# Technical Investigation and Scope Definition Report: RAG Feature

This report presents a comprehensive technical investigation, design, and implementation plan for adding Retrieval-Augmented Generation (RAG) capabilities to Aizen.

---

## 1. Observations

### 1.1 OpenAI/OpenRouter Client Interaction
- **Import Location**: `aizen/main.py:15`
  ```python
  from openai import AsyncOpenAI
  ```
- **Initialization**: `aizen/main.py:230`
  ```python
  client = AsyncOpenAI(base_url=api_base, api_key=api_key)
  ```
- **Key & Base URL Resolution**:
  - `api_key` is resolved at `aizen/main.py:216`:
    ```python
    api_key = get_api_key(config, reset=args.reset_key)
    ```
    Where `get_api_key` is imported from `.config` and reads `OPENROUTER_API_KEY` from config, environment, or queries the user.
  - `api_base` is resolved at `aizen/main.py:223`:
    ```python
    api_base = config.get("API_BASE_URL", "https://openrouter.ai/api/v1")
    ```
- **Usage for Request Streaming**: `aizen/agent.py:149`
  ```python
  stream: AsyncStream = await self.client.chat.completions.create(**api_params)
  ```

### 1.2 Local Database Configurations
- **Sessions Directory**: `aizen/config.py:29`
  ```python
  SESSIONS_DIR = os.path.expanduser("~/.aizen_sessions")
  ```
- **Sessions DB Connection & Path**: `aizen/session.py:62`
  ```python
  db_path = os.path.join(SESSIONS_DIR, "aizen.db")
  ```
  And `_get_db()` returns a singleton `sqlite3.Connection`.

### 1.3 Slash Commands Implementation
- **Registration List**: `aizen/commands.py:28`
  ```python
  SLASH_COMMANDS = [
      ("/help", "Show all available commands"),
      ...
  ]
  ```
- **Command Completion / Argument Detection**: `aizen/commands.py:70`
  ```python
  cmds_with_args = {"/model", "/save", "/load", "/export", "/checkpoint", "/restore"}
  ```
- **Command Handling Routing**: `aizen/commands.py:141`
  ```python
  async def handle_slash_command(
      command_str: str, messages: list, token_tracker: TokenTracker, mcp_manager=None, client=None
  ) -> bool:
  ```
- **Rich Integration**: Inside `handle_slash_command`, output is directed to the user via the `console` object (imported from `.config`):
  ```python
  console.print(f"  [{Theme.SUCCESS}]✓ Restored checkpoint...[/{Theme.SUCCESS}]\n")
  ```

### 1.4 Gitignore Utility
- **Implementation**: `aizen/utils.py:254` and `aizen/utils.py:279`
  ```python
  def load_gitignore_patterns() -> list: ...
  def should_ignore(path: str, patterns: list) -> bool: ...
  ```

### 1.5 Tool Registration and Execution
- **Schema List**: `aizen/tools/dispatcher.py:31` defines the schema array `tools`.
- **Execution Hook**: `aizen/tools/dispatcher.py:307`
  ```python
  def execute_tool(tool_call, auto_approve: bool = False) -> str:
  ```
- **Call Mechanics**: `aizen/agent.py:237`
  ```python
  result = await asyncio.to_thread(execute_tool, tc_struct, self.auto_approve)
  ```
  *Crucial architectural observation*: Tool execution is offloaded to a background thread using `asyncio.to_thread`. Therefore, the tool dispatcher executes synchronously, and does not receive the asynchronous `client` instance.

---

## 2. Logic Chain

### 2.1 Embedding Generation Integration
- **Step 1**: To obtain embeddings from OpenAI, we use the `client.embeddings.create` method. Since the client is of type `AsyncOpenAI`, the API request is made using:
  ```python
  response = await client.embeddings.create(input=[text], model=model_name)
  ```
- **Step 2**: OpenRouter does not officially support embeddings on its default endpoint. Therefore, if the user configures Aizen with OpenRouter, embeddings generation using the primary client will fail.
- **Step 3 (Conclusion)**: We must allow optional config overrides for embeddings in `~/.aizen_config.json`:
  - `EMBEDDING_API_KEY`: Fallback to primary API key.
  - `EMBEDDING_BASE_URL`: Fallback to `https://api.openai.com/v1` or primary base URL.
  - `EMBEDDING_MODEL`: Defaults to `text-embedding-3-small`.
- **Step 4**: Since tool dispatcher functions run synchronously in `asyncio.to_thread`, we should implement both a synchronous embedding generator (using a synchronous `openai.OpenAI` client initialized inside the tool) and an asynchronous generator (for commands running in the main event loop).

### 2.2 Local Vector Database Design
- **Step 1**: The session database `~/.aizen_sessions/aizen.db` currently manages conversation states. Storing high-dimensional vectors (e.g. 1536 dimensions for `text-embedding-3-small` or 3072 for `text-embedding-3-large`) and source code chunks in the same DB would significantly bloat session database file sizes, affecting CLI startup and recovery performance.
- **Step 2 (Conclusion)**: We should create a separate database file `~/.aizen_sessions/vector_cache.db`. This keeps session storage lightweight and lets the user easily delete or reset the vector index.
- **Step 3**: SQLite does not support native vector cosine similarity operations. Thus, we will serialize float lists to BLOB using Python's `struct.pack('f' * len(v), *v)` and deserialize via `struct.unpack`. Similarity calculations (cosine similarity or dot product for normalized embeddings) will be calculated in Python.

### 2.3 Command & Tool Integration
- **Step 1**: `/search` and `/reindex` slash commands will register in `aizen/commands.py` by adding them to `SLASH_COMMANDS` and routing in `handle_slash_command`.
- **Step 2**: The `semantic_search` function will register as a tool in `aizen/tools/dispatcher.py` to let the LLM execute semantic searches autonomously.
- **Step 3**: The tool dispatcher runs in a synchronous thread, so it will instantiate a synchronous `openai.OpenAI` client on-demand or use a cached global client to invoke embedding generation.

---

## 3. Caveats
- **OpenRouter Support**: OpenRouter endpoint does not support embeddings. If the user only has an OpenRouter free key and no OpenAI key, RAG indexing and search will fail unless configured with a local embedding provider (like Ollama at `http://localhost:11434/v1` or an OpenAI key). This limitation must be clearly communicated to users via console warnings.
- **Binary/Large Files**: The indexer must skip binary files and extremely large files (e.g., >500KB) to prevent hitting rate limits or consuming too many tokens.
- **Memory Consumption**: Calculating cosine similarity for thousands of chunks in Python could be slow. For extremely large codebases, indexing should be optimized or restricted to specific subfolders.

---

## 4. Conclusion & Proposed Architecture

We propose introducing a new module `aizen/rag.py` to centralize all RAG functionality.

### 4.1 Proposed RAG Module (`aizen/rag.py`)
```python
import os
import json
import sqlite3
import struct
import math
from openai import OpenAI, AsyncOpenAI
from .config import load_config, get_api_key, SESSIONS_DIR
from .utils import load_gitignore_patterns, should_ignore

DB_PATH = os.path.join(SESSIONS_DIR, "vector_cache.db")

# Initialize and cache embedding clients
_sync_client = None
_async_client = None

def get_embedding_config():
    config = load_config()
    # Read specialized embedding configurations or fall back to defaults
    api_key = config.get("EMBEDDING_API_KEY") or config.get("OPENROUTER_API_KEY")
    api_base = config.get("EMBEDDING_BASE_URL")
    if not api_base:
        primary_base = config.get("API_BASE_URL", "")
        if "openrouter" in primary_base.lower():
            # OpenRouter doesn't support embeddings; default to standard OpenAI
            api_base = "https://api.openai.com/v1"
        else:
            api_base = primary_base or "https://api.openai.com/v1"
            
    model = config.get("EMBEDDING_MODEL", "text-embedding-3-small")
    return api_key, api_base, model

def get_sync_client():
    global _sync_client
    if _sync_client is None:
        api_key, api_base, _ = get_embedding_config()
        if not api_key:
            raise ValueError("No API key available for embedding generation. Please set EMBEDDING_API_KEY.")
        _sync_client = OpenAI(api_key=api_key, base_url=api_base)
    return _sync_client

def get_async_client():
    global _async_client
    if _async_client is None:
        api_key, api_base, _ = get_embedding_config()
        if not api_key:
            raise ValueError("No API key available for embedding generation. Please set EMBEDDING_API_KEY.")
        _async_client = AsyncOpenAI(api_key=api_key, base_url=api_base)
    return _async_client

def generate_embedding_sync(text: str) -> list[float]:
    client = get_sync_client()
    _, _, model = get_embedding_config()
    response = client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding

async def generate_embedding_async(text: str) -> list[float]:
    client = get_async_client()
    _, _, model = get_embedding_config()
    response = await client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding

# ─── SQLite Vector Store Cache ───

def get_db():
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vector_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            chunk_index INTEGER,
            content TEXT,
            embedding BLOB,
            mtime REAL
        )
    """)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_file_chunk ON vector_cache(file_path, chunk_index)")
    conn.commit()
    return conn

def serialize_vector(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)

def deserialize_vector(blob: bytes) -> list[float]:
    num_floats = len(blob) // 4
    return list(struct.unpack(f"{num_floats}f", blob))

# ─── Document Chunking & Indexing ───

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def index_file(file_path: str):
    try:
        mtime = os.path.getmtime(file_path)
        conn = get_db()
        
        # Check if file has changed
        cursor = conn.execute("SELECT mtime FROM vector_cache WHERE file_path = ? LIMIT 1", (file_path,))
        row = cursor.fetchone()
        if row and row[0] >= mtime:
            return  # Skip unchanged file
            
        # Clear old chunks
        conn.execute("DELETE FROM vector_cache WHERE file_path = ?", (file_path,))
        
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            embedding = generate_embedding_sync(chunk)
            blob = serialize_vector(embedding)
            conn.execute(
                "INSERT INTO vector_cache (file_path, chunk_index, content, embedding, mtime) VALUES (?, ?, ?, ?, ?)",
                (file_path, i, chunk, blob, mtime)
            )
        conn.commit()
    except Exception as e:
        print(f"Failed to index {file_path}: {e}")

def reindex_directory(root_dir: str = "."):
    ignore_patterns = load_gitignore_patterns()
    for root, dirs, files in os.walk(root_dir):
        # Filter directories in-place to avoid going into ignored ones
        dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d), ignore_patterns)]
        for file in files:
            file_path = os.path.join(root, file)
            if not should_ignore(file_path, ignore_patterns):
                # Only index text files under 500KB
                try:
                    if os.path.getsize(file_path) < 500000:
                        index_file(file_path)
                except OSError:
                    pass

# ─── Cosine Similarity Search ───

def dot_product(v1, v2):
    return sum(x * y for x, y in zip(v1, v2))

def magnitude(v):
    return math.sqrt(sum(x * x for x in v))

def cosine_similarity(v1, v2):
    mag1 = magnitude(v1)
    mag2 = magnitude(v2)
    if mag1 == 0 or mag2 == 0:
        return 0
    return dot_product(v1, v2) / (mag1 * mag2)

def query_vector_cache(query_vector: list[float], top_k: int = 5) -> list[dict]:
    conn = get_db()
    cursor = conn.execute("SELECT file_path, chunk_index, content, embedding FROM vector_cache")
    results = []
    for row in cursor.fetchall():
        file_path, chunk_index, content, blob = row
        db_vector = deserialize_vector(blob)
        score = cosine_similarity(query_vector, db_vector)
        results.append({
            "file_path": file_path,
            "chunk_index": chunk_index,
            "content": content,
            "score": score
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
```

### 4.2 Registering `/search` and `/reindex` commands (`aizen/commands.py`)
1. **Append to `SLASH_COMMANDS`**:
   ```python
   SLASH_COMMANDS = [
       ...
       ("/search", "Perform semantic search across the workspace"),
       ("/reindex", "Reindex workspace files into the vector store"),
   ]
   ```
2. **Add to `cmds_with_args`**:
   ```python
   cmds_with_args = {"/model", "/save", "/load", "/export", "/checkpoint", "/restore", "/search", "/reindex"}
   ```
3. **Route in `handle_slash_command`**:
   ```python
   elif cmd == "/search":
       if not arg:
           console.print(f"  [{Theme.ERROR}]Error: Please provide a search query.[/{Theme.ERROR}]\n")
           return False
       console.print(f"  [{Theme.MUTED}]Searching for: '{arg}'...[/{Theme.MUTED}]")
       try:
           from .rag import generate_embedding_async, query_vector_cache
           q_emb = await generate_embedding_async(arg)
           results = query_vector_cache(q_emb, top_k=5)
           
           if not results:
               console.print(f"  [{Theme.WARNING}]No semantic search matches found. Try running /reindex first.[/{Theme.WARNING}]\n")
               return False
               
           console.print(f"\n  [bold {Theme.TEXT}]Semantic Search Results:[/bold {Theme.TEXT}]")
           for idx, r in enumerate(results, 1):
               console.print(f"  [bold {Theme.ACCENT}]{idx}. {r['file_path']}[/bold {Theme.ACCENT}] (Score: [dim]{r['score']:.4f}[/dim])")
               console.print(f"  [dim]{r['content'][:300]}...[/dim]\n")
       except Exception as e:
           console.print(f"  [{Theme.ERROR}]Error during search: {e}[/{Theme.ERROR}]\n")
           
   elif cmd == "/reindex":
       target_dir = arg or "."
       console.print(f"  [{Theme.MUTED}]Reindexing files in '{target_dir}'...[/{Theme.MUTED}]")
       try:
           from .rag import reindex_directory
           # Run reindexing inside a thread to prevent freezing the event loop
           await asyncio.to_thread(reindex_directory, target_dir)
           console.print(f"  [{Theme.SUCCESS}]✓ Reindexing complete.[/{Theme.SUCCESS}]\n")
       except Exception as e:
           console.print(f"  [{Theme.ERROR}]Error during reindexing: {e}[/{Theme.ERROR}]\n")
   ```

### 4.3 Registering the `semantic_search` Tool (`aizen/tools/dispatcher.py`)
1. **Schema registration**:
   ```python
   {
       "type": "function",
       "function": {
           "name": "semantic_search",
           "description": "Semantically searches the local codebase using vector embeddings. Ideal for finding conceptual matches or API usages when exact keywords are unknown.",
           "parameters": {
               "type": "object",
               "properties": {
                   "query": {
                       "type": "string",
                       "description": "The concept or functionality to search for.",
                   },
                   "top_k": {
                       "type": "integer",
                       "description": "Number of results to retrieve (default: 5).",
                   }
               },
               "required": ["query"],
           },
       },
   }
   ```
2. **Execute tool implementation**:
   ```python
   elif func_name == "semantic_search":
       query = str(args.get("query", ""))
       top_k = int(args.get("top_k", 5))
       tool_label.append(f" → '{query}' (top_k={top_k})", style="dim")
       console.print(tool_label)
       
       try:
           from ..rag import generate_embedding_sync, query_vector_cache
           q_emb = generate_embedding_sync(query)
           results = query_vector_cache(q_emb, top_k=top_k)
           
           if not results:
               return "No semantic search matches found. Advise the user to run /reindex."
               
           formatted = []
           for r in results:
               formatted.append(
                   f"File: {r['file_path']} (Similarity: {r['score']:.4f})\n"
                   f"Snippet:\n---\n{r['content']}\n---\n"
               )
           return "\n".join(formatted)
       except Exception as e:
           return f"Error executing semantic search: {e}"
   ```

---

## 5. Verification Method

To verify the correct execution and robustness of the implementation:
1. **Run Tests**: Execute `pytest tests/` (once implemented, unit tests for the functions inside `aizen/rag.py` should be added to `tests/test_rag.py`).
2. **Configuration Check**: Verify that `~/.aizen_config.json` is modified to include custom embedding details:
   ```json
   {
       "EMBEDDING_API_KEY": "openai_api_key_here",
       "EMBEDDING_MODEL": "text-embedding-3-small"
   }
   ```
3. **Execution Invalidation**: Ensure that when the `~/.aizen_sessions/vector_cache.db` is deleted, a search returns a warning instead of raising an unhandled exception, and running `/reindex` regenerates the DB file successfully.
