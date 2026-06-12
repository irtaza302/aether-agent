# Context - Aizen AI Agent CLI Codebase

## Codebase Info
- Location: `/Users/devexcel/Documents/irtaza/agent`
- Existing structure: TBD (to be explored by subagent)
- Targets:
  - CLI commands (specifically slash commands)
  - Tool framework for agent (where tools are registered)
  - Sessions/App data directory (`~/.aizen_sessions`)

## Key Constraints
- Code only network mode. No external calls to download/download packages or hit external endpoints directly during runtime unless through a configured API key/endpoint. Wait, embedding generation should connect to the *configured* LLM provider's embedding API (or lightweight local alternative). We must check what the configured LLM provider is in Aizen config.
- Lightweight local vector store (e.g. SQLite or simple numpy cache saved to disk).
