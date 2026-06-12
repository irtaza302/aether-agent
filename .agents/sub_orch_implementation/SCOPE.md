# Scope: Local Codebase Semantic Search (RAG) Implementation

## Architecture
- **Embedding Client**: Uses OpenAI/OpenRouter client to generate embeddings.
- **Ignore Filtering**: Uses `aizen/utils.py` functions to load `.gitignore` and filter files.
- **SQLite Vector Store**: Manages vectors. We will create tables for cached file embeddings: paths, contents/hashes, timestamps, and binary-serialized/JSON-serialized embeddings.
- **Slash Commands**: `/search <query>` and `/reindex` command integration in `aizen/commands.py`.
- **Semantic Search Tool**: `semantic_search` function registered in `aizen/tools/dispatcher.py` to allow agent to query vectors.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Investigation | Analyze codebase structures, design data layouts, verify requirements. | None | DONE |
| 2 | M2: Embedding & Filter | Implement embedding generation and ignore-aware workspace walking. | M1 | DONE |
| 3 | M3: Vector Cache | SQLite database layer for embeddings storage and semantic similarity. | M2 | DONE |
| 4 | M4: Search Interfaces | `/search`, `/reindex` slash commands & `semantic_search` dispatcher tool. | M3 | DONE |
| 5 | M5: E2E and Audit | Integration with E2E Testing Track suite and Forensic Audit. | M4 | DONE |

## Interface Contracts
### Embedding Engine
- `async def generate_embeddings(texts: list[str], client) -> list[list[float]]`
- Model target: `text-embedding-3-small` or standard embedding model.

### Database Layer
- Storage path: `~/.aizen_vector_cache/vector_cache.db`
- Schema:
  - `file_embeddings` table: `filepath TEXT PRIMARY KEY`, `content_hash TEXT`, `last_modified REAL`, `embedding BLOB/TEXT`

### Search Command
- `/search <query>` - outputs top-K similar files/snippets using Rich panel/table format.
- `/reindex` - scans directory, updates/adds embeddings for new/modified files, deletes stale records.
