# Scope: Local Codebase Semantic Search (RAG) E2E Test Suite

## Architecture
The Semantic Search / RAG system consists of:
1. **Chunker & Indexer**: Parses workspace files, filters based on `.gitignore`, binary status, and file size, splits files into semantic chunks, and calculates file content hashes.
2. **Embedding Generator**: Interface to LLM embedding provider with mock fallback.
3. **Vector Database / Storage**: SQLite-based db storing text chunks, file paths, line ranges, and serialized float vectors. Provides cosine similarity search.
4. **Slash Command Interface**: CLI terminal command handler for `/search <query>` to search and output matches using Rich.
5. **semantic_search Tool**: Aize-dispatchable tool allowing LLM to programmatically retrieve codebase snippets.

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Test Plan & Infrastructure | Create test environment, mocks, and skeleton | None | DONE |
| 2 | Test Cases Implementation | Implement 60 tests in `tests/test_rag_search.py` | M1 | DONE |
| 3 | Test Suite Validation | Run pytest to verify all tests execute and pass | M2 | DONE |

---

## 4-Tier Test Matrix

### Feature 1: Chunker & Indexer
* **Tier 1 (Feature Coverage):**
  1. `test_chunker_basic_chunking`: Verify a file is split into chunks of correct size.
  2. `test_chunker_gitignore_respect`: Verify files ignored by `.gitignore` are not indexed.
  3. `test_chunker_ignore_binary`: Verify binary files (e.g. `.png`) are skipped.
  4. `test_chunker_ignore_large`: Verify files exceeding the size limit (e.g. >1MB) are ignored.
  5. `test_chunker_incremental_hash`: Verify a file is only re-chunked if its content hash changes.
* **Tier 2 (Boundary & Corner Cases):**
  6. `test_chunker_empty_file`: Chunking an empty file produces 0 chunks.
  7. `test_chunker_single_exact_chunk`: File size matches chunk size exactly.
  8. `test_chunker_very_long_lines`: Line longer than the chunk character limit.
  9. `test_chunker_malformed_gitignore`: Handle missing/unreadable `.gitignore` gracefully.
  10. `test_chunker_unicode_decoding`: Non-UTF-8 or malformed characters decoded safely without crashing.

### Feature 2: Embedding Generation
* **Tier 1 (Feature Coverage):**
  11. `test_embedding_gen_successful_api`: Verify API returns correct vector dimension for a text input.
  2. `test_embedding_gen_batching`: Verify embedding requests are batched for efficiency.
  13. `test_embedding_gen_rate_limit_retry`: Verify embedding generator retries on rate limits (429).
  14. `test_embedding_gen_timeout_handling`: Verify generator handles timeouts gracefully.
  15. `test_embedding_gen_mock_fallback`: Verify fallback embedding is generated if API credentials are not set/configured.
* **Tier 2 (Boundary & Corner Cases):**
  16. `test_embedding_gen_empty_input`: Generating embedding for empty string returns zero-vector or handles gracefully.
  17. `test_embedding_gen_excessive_input_tokens`: Truncate chunk text if it exceeds LLM token limit.
  18. `test_embedding_gen_invalid_api_key`: Correctly raises Authentication/Configuration error.
  19. `test_embedding_gen_partial_api_failure`: Partial failures in batch request are handled (e.g., individual retries).
  20. `test_embedding_gen_special_characters`: Vector generation for emojis, math symbols, and control chars.

### Feature 3: Vector Storage
* **Tier 1 (Feature Coverage):**
  21. `test_vector_db_save_load`: Verify embeddings are stored and reloaded from SQLite cache.
  22. `test_vector_db_cosine_similarity`: Verify cosine similarity ranks exact matches first.
  23. `test_vector_db_incremental_sync`: Database retains unchanged files, updates changed, deletes removed.
  24. `test_vector_db_top_k_filtering`: Retrieval returns exactly `top_k` results.
  25. `test_vector_db_session_isolation`: Vector cache is isolated per workspace or session directory.
* **Tier 2 (Boundary & Corner Cases):**
  26. `test_vector_db_duplicate_indexing`: Re-syncing the same workspace multiple times does not insert duplicates.
  27. `test_vector_db_empty_db_query`: Querying an empty database returns empty results list.
  28. `test_vector_db_zero_cosine_distance`: Querying with orthogonal vector returns low/zero similarity.
  29. `test_vector_db_max_chunks_limit`: Limit max indexable chunks to avoid database bloat.
  30. `test_vector_db_schema_migration`: Handles older schema db files by recreating/migrating.

### Feature 4: Slash Command `/search`
* **Tier 1 (Feature Coverage):**
  31. `test_search_command_output_format`: Verify command prints results with file paths, similarity, and snippet.
  32. `test_search_command_matching_snippets`: Verify the correct text snippet is printed.
  33. `test_search_command_help_text`: Verify search command help/usage displays correctly.
  34. `test_search_command_top_n_arg`: User can customize number of results with `--limit` or `-n`.
  35. `test_search_command_interactive`: Verify slash command responds correctly within CLI interactive session.
* **Tier 2 (Boundary & Corner Cases):**
  36. `test_search_command_empty_query`: Reject empty query with help message.
  37. `test_search_command_no_results`: Displays a friendly "No matches found" message.
  38. `test_search_command_query_special_chars`: Handles queries with special symbols/regex characters.
  39. `test_search_command_huge_limit`: Handles excessively large limit values safely.
  40. `test_search_command_nonexistent_workspace`: Handles search command run outside any workspace.

### Feature 5: `semantic_search` Tool
* **Tier 1 (Feature Coverage):**
  41. `test_tool_schema_declaration`: Tool defines standard parameters (query, limit, path).
  42. `test_tool_dispatch_invocation`: Dispatcher executes tool with valid arguments.
  43. `test_tool_returns_json_string`: Output matches LLM context schema (JSON format).
  44. `test_tool_result_content`: Returns correct files, line ranges, and scores.
  45. `test_tool_path_filter`: Respects `path` argument to restrict search to a subdirectory.
* **Tier 2 (Boundary & Corner Cases):**
  46. `test_tool_invalid_arguments`: Handles wrong parameter types/missing query gracefully.
  47. `test_tool_empty_results`: Tool returns clear JSON indicating no hits found.
  48. `test_tool_absolute_vs_relative_paths`: Tool accepts and correctly resolves both absolute and relative path bounds.
  49. `test_tool_concurrent_queries`: Tool executes concurrently under dispatcher without SQLite locking.
  50. `test_tool_malformed_path_arg`: Handles non-existent directories or invalid paths without crashing.

### Tier 3: Cross-Feature Combinations (Pairwise Coverage)
51. `test_combo_indexer_sync_and_command`: Run full indexing on workspace, verify CLI command finds newly added files.
52. `test_combo_sync_deleted_file_tool`: Delete a file from workspace, run sync, verify tool no longer retrieves it.
53. `test_combo_api_error_fallback_search`: LLM API returns error, fallback occurs, command still works with fallback vectors.
54. `test_combo_slash_command_during_active_indexing`: CLI search during indexing shows available chunks without locking db.
55. `test_combo_tool_and_command_consistent_results`: Tool and slash command return same matches for identical query.

### Tier 4: Real-World Application Scenarios
56. `test_scenario_code_comprehension`: Find where a specific configuration key is loaded and trace its validation logic.
57. `test_scenario_bug_investigation`: Search for "sqlite3.OperationalError" to locate database connection bugs.
58. `test_scenario_refactoring_impact`: Search functions referencing a utility method to plan renaming impact.
59. `test_scenario_incremental_dev`: Index codebase, add a new endpoint module, sync, query the new endpoints.
60. `test_scenario_agent_interaction`: Simulate agent diagnosing a crash using `semantic_search` tool to find the error file.

---

## Interface Contracts
- **Search CLI Command**: `/search <query> [--limit <n>]`
- **Tool Schema**:
  - `semantic_search(query: str, limit: int = 5, path: str = None) -> str`
- **Database Location**: `~/.aizen_sessions/vector_cache.db` or configured app path.
