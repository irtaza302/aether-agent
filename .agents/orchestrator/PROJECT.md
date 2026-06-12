# Project: Local Codebase Semantic Search (RAG)

## Architecture
- **Embedding Generation**: Wrap the configured OpenAI/OpenRouter client to call `/embeddings` endpoint using model `openai/text-embedding-3-small` (or similar configured model).
- **Local Vector Storage**: Standard SQLite database storage in `~/.aizen_vector_cache/vector_cache.db` or as a new table `chunk_embeddings` in `~/.aizen_sessions/aizen.db`.
- **Search Logic**: Pure-Python in-memory cosine similarity calculation over workspace embeddings.
- **CLI Commands**: Add `/search <query>` and `/reindex` to `aizen/commands.py`.
- **Agent Tools**: Add `semantic_search` tool schema and handler in `aizen/tools/dispatcher.py`.

## Code Layout
- `aizen/rag.py` (New): Handles DB schema, chunking, API wrapper, and workspace indexing.
- `aizen/commands.py` (Modify): Adds slash command parsing and output formatting.
- `aizen/tools/dispatcher.py` (Modify): Registers schema and routing for `semantic_search`.
- `tests/test_rag_search.py` (New): E2E test cases covering features, boundaries, combinations, and application scenarios.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | E2E Testing Track | Write comprehensive 4-tier opaque-box test suite in `tests/test_rag_search.py` and publish `TEST_READY.md` | None | DONE (Conv: 6e27c2d1-3373-4698-ac55-22abb3db5417, 60 tests passed) |
| 2 | Core Implementation | Implement embeddings, SQLite store, incremental indexing in `aizen/rag.py` | None | DONE (Conv: 3777abf1-2fc8-490e-b092-8fa66bddfc7e) |
| 3 | Command & Tool Integration | Integrate `/search` slash command and `semantic_search` tool | M2 | DONE (Conv: 3777abf1-2fc8-490e-b092-8fa66bddfc7e) |
| 4 | Final E2E Validation | Pass 100% of the E2E test suite | M1, M3 | DONE (60/60 tests passing) |
| 5 | Adversarial Hardening | White-box coverage analysis and adversarial testing | M4 | DONE (CLEAN forensic audit verdict) |

## Interface Contracts
### `aizen/rag.py`
- `class VectorStore`
- `class EmbeddingGenerator`
- `class Chunker`
- `class SlashCommandRunner`
- `def semantic_search_tool`
