# E2E Test Infra: Aizen CLI Semantic Search (RAG)

## Test Philosophy
- Opaque-box, requirement-driven. Minimum dependency on internal structures.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combination + Workload Testing.
- Utilizes mocked LLM endpoints, console environments, and file layouts to test CLI and tool dispatch flows before the backend is fully wired.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Chunker & Indexer | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | Embedding Generation | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | Local Vector Storage | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 4 | CLI Slash Command `/search` | ORIGINAL_REQUEST §R3.1 | 5 | 5 | ✓ |
| 5 | Tool `semantic_search` | ORIGINAL_REQUEST §R3.2 | 5 | 5 | ✓ |

## Test Architecture
- **Test Runner**: Pytest. Invoked via `pytest tests/test_rag_search.py`.
- **Mocks and Fixtures**:
  - Embedding Generator API calls: Mocked to return mock float vectors of appropriate size.
  - File layouts: Temporary directory trees created with varying size, naming, `.gitignore` patterns, and contents.
  - SQLite Store: Clean mock database inside temporary sessions directories to isolate tests.
  - Interactive CLI environment: Mock console and session input objects to verify slash commands.
- **Directory Layout**:
  - Test suite code: `tests/test_rag_search.py`
  - Workspace cache database: `~/.aizen_sessions/vector_cache.db` (for production) or temporary caches (for testing).

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | `test_scenario_code_comprehension` | F1, F2, F3, F4 | Medium |
| 2 | `test_scenario_bug_investigation` | F1, F2, F3, F4, F5 | High |
| 3 | `test_scenario_refactoring_impact` | F1, F3, F4 | Medium |
| 4 | `test_scenario_incremental_dev` | F1, F2, F3, F4 | High |
| 5 | `test_scenario_agent_interaction` | F1, F2, F3, F5 | High |

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: 25 tests (5 per feature)
- **Tier 2 (Boundary & Corner)**: 25 tests (5 per feature)
- **Tier 3 (Cross-Feature Combinations)**: 5 tests (covering pairwise features)
- **Tier 4 (Real-World Scenarios)**: 5 application workloads
- **Total Minimum**: 60 test cases
