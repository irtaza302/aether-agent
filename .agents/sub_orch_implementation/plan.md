# Plan: Local Codebase Semantic Search (RAG) Implementation

## Objective
Implement Local Codebase Semantic Search (RAG) in the Aizen CLI.

## Subtasks & Verification
1. **M1: Technical Investigation and Scope Definition**
   - Goal: Research existing files (`aizen/commands.py`, `aizen/utils.py`, `aizen/tools/dispatcher.py`) and plan exact integrations.
   - Verification: Design document and milestone list written to `SCOPE.md`.

2. **M2: Embedding Generation and Gitignore Filtering**
   - Goal: Build embedding generation logic that calls the active OpenRouter/OpenAI client, using `text-embedding-3-small` or standard API. Ensure it uses `aizen/utils.py`'s `should_ignore`/`load_gitignore_patterns` to respect `.gitignore`.
   - Verification: Unit test verification that files matching `.gitignore` are excluded and embeddings are successfully requested via mock/real API client.

3. **M3: SQLite Vector Cache (Database / storage layer)**
   - Goal: Implement a SQLite database/table to store file paths, last modified timestamps, file content hash, and vector embeddings. Location: `~/.aizen_vector_cache/vector_cache.db` or session db.
   - Verification: DB schema checks, insert, query, update, cosine similarity computation in SQL or Python.

4. **M4: Slash Commands (/search, /reindex) and semantic_search tool**
   - Goal: Integrate `/search <query>` and `/reindex` slash commands in `aizen/commands.py` with Rich formatting. Register the `semantic_search` tool in `aizen/tools/dispatcher.py`.
   - Verification: Command parsing checks, formatting checks.

5. **M5: E2E Verification & Audit**
   - Goal: Run tests in `tests/test_rag_search.py` published by the E2E track and fix any bugs. Run Forensic Auditor.
   - Verification: 100% tests passing, Forensic Auditor clean verdict.
