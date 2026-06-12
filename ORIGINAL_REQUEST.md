# Original User Request

## Initial Request — 2026-06-12T16:20:47Z

Add Local Codebase Semantic Search (RAG) to the Aizen AI Agent CLI to allow the agent and the user to quickly find relevant code context across large repositories without exceeding context windows.

Working directory: /Users/devexcel/Documents/irtaza/agent
Integrity mode: development

## Requirements

### R1. Embedding Generation
Integrate with the configured LLM provider's embedding API (or a lightweight local alternative) to generate vector embeddings for source code files in the workspace. The indexer must respect `.gitignore` and ignore binary/large files.

### R2. Local Vector Storage
Implement a lightweight local vector store (e.g., using SQLite with distance functions, or a simple in-memory numpy cache saved to disk) to persist file embeddings between Aizen sessions. This should be stored in the existing `~/.aizen_sessions` or similar app data directory.

### R3. Search Interfaces
1. Expose a new interactive `/search <query>` slash command for the user to manually query the codebase.
2. Add a `semantic_search` tool to Aizen's tool calling framework so the LLM can query the codebase on its own when investigating issues.

## Acceptance Criteria

### Automated Testing
- [ ] A test script (`tests/test_rag_search.py`) is created to verify indexing and retrieval.
- [ ] The test indexes a small set of mock code files.
- [ ] The test performs a semantic query and successfully retrieves the most relevant mocked file based on cosine similarity or distance.
- [ ] The test verifies that the `semantic_search` tool correctly formats and returns search results.
- [ ] Running `pytest tests/test_rag_search.py` passes without errors.
