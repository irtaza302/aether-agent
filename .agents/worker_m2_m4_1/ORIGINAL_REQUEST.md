## 2026-06-12T11:27:41Z
You are a worker with role 'RAG Implementer'.
Your working directory is `/Users/devexcel/Documents/irtaza/agent/.agents/worker_m2_m4_1/`.

Your task is to implement the Local Codebase Semantic Search (RAG) feature.
Follow these specifications:

1. Create a new module `aizen/rag.py` containing:
- Embedding generation logic using OpenAI / OpenRouter client. Since the main tool dispatcher runs synchronously inside `asyncio.to_thread`, you must provide BOTH synchronous and asynchronous functions:
  * `def generate_embedding_sync(text: str) -> list[float]`
  * `async def generate_embedding_async(text: str) -> list[float]`
- API key, base URL and model resolution:
  * Retrieve config using `from .config import load_config`.
  * Get API key from `EMBEDDING_API_KEY` (config or environment), fallback to `OPENAI_API_KEY` (environment), fallback to `OPENROUTER_API_KEY` (config or environment).
  * Get API Base from `EMBEDDING_BASE_URL` (config or environment). If not provided, fallback to primary `API_BASE_URL` from config. If the base URL contains 'openrouter.ai', default to 'https://api.openai.com/v1' for embedding generation.
  * Get model from `EMBEDDING_MODEL` (config or environment), default to 'text-embedding-3-small'.
- Gitignore filtering:
  * Import `load_gitignore_patterns` and `should_ignore` from `aizen.utils`.
  * When walking the codebase, respect `.gitignore` rules. Do not index directories or files that should be ignored.
- Local vector database using `sqlite3`:
  * Database file path: `~/.aizen_vector_cache/vector_cache.db`. Create the parent directories if they do not exist.
  * Define a table `vector_cache` containing columns: `id`, `file_path`, `chunk_index`, `content` (text snippet), `embedding` (BLOB serialized with `struct.pack`), and `mtime` (last modified time of the file).
  * Handle serializing/deserializing vectors using `struct.pack(f"{len(v)}f", *v)` and `struct.unpack`.
- Document Chunking:
  * Implement text chunking, e.g. chunk size ~1000 characters with an overlap of ~200.
  * Skip binary files (by catching UnicodeDecodeError) and files larger than 500KB.
- Cosine Similarity Search:
  * Compute cosine similarity in Python between query vector and database vectors. Return top-K records sorted by score descending.

2. Integrate Slash Commands in `aizen/commands.py`:
- Register `/search` and `/reindex` commands in `SLASH_COMMANDS` and `cmds_with_args`.
- Implement `/search <query>`:
  * Format search results beautifully using Rich formatting (following the `Theme` styling of Aizen).
- Implement `/reindex`:
  * Re-scans the current directory (defaulting to `.`), updates index for new/modified files, deletes database rows for files that no longer exist or are now ignored.
  * Run reindexing in a thread (`await asyncio.to_thread(reindex_directory, target_dir)`) to prevent blocking the event loop.

3. Register `semantic_search` tool in `aizen/tools/dispatcher.py`:
- Add the function schema definition in the `tools` list.
- Dispatch the call under `execute_tool` using the sync functions in `aizen/rag.py`. Return the formatted matches to the model.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT
hardcode test results, create dummy/facade implementations, or
circumvent the intended task. A Forensic Auditor will independently
verify your work. Integrity violations WILL be detected and your
work WILL be rejected.

Please execute the changes, test and compile your work if needed, and write a handoff report at `/Users/devexcel/Documents/irtaza/agent/.agents/worker_m2_m4_1/handoff.md` detailing the changes and verification results. Send a message to us when complete.
