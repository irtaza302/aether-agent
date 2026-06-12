# Aizen AI Agent 🚀

[![CI](https://github.com/irtaza302/aizen-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/irtaza302/aizen-agent/actions/workflows/ci.yml)

Aizen is a powerful, asynchronous AI assistant that integrates seamlessly into your terminal workflow. It reads your code, edits files safely, runs commands, and provides real‑time, richly formatted assistance—all while keeping costs transparent and sessions persistent.

## 🌟 Key Benefits

- **Effortless Integration** — Operates directly in your terminal, preserving shell state across commands.
- **Intelligent Editing** — Perform precise, color‑coded file edits with `edit_file`.
- **Background Execution** — Run long‑running tasks asynchronously and retrieve results later.
- **Cost‑Aware Usage** — Real‑time cost estimation for all major LLMs.
- **Persistent Sessions** — Save and restore conversations with checkpoints.
- **Rich Visual Feedback** — Stream responses with live previews and animated thought indicators.
- **Extensible Architecture** — Custom plugins and project‑specific rules tailor Aizen to your workflow.
- **Comprehensive Logging** — Rotating logs with optional verbose output for debugging.

## 🚀 Core Features

### Asynchronous Architecture
- Fully asynchronous operations using `asyncio` and `AsyncOpenAI` for concurrent processing, parallel tool runs, and streaming.

### Stateful Terminal Session
- Environment variables and directory changes persist across interactions.

### Rich Markdown Rendering
- Full Markdown support with headers, code blocks, lists, and styling via Rich.

### Surgical File Editing
- Precise search‑and‑replace with color‑coded diff previews (`edit_file`).

### Vision Support
- Native image handling and encoding for Vision APIs (e.g., GPT‑4o, Claude 3.5 Sonnet).

### Real‑Time Command Streaming
- Background command execution with async streaming of stdout/stderr; use `run_command --background`.

## 🎛️ Workflow Tools

- **Background Tasks** — Run non‑blocking commands; monitor with `check_background_task`; cancel with `kill_background_task`.
- **Session Persistence** — Powered by SQLite (`~/.aizen_sessions/aizen.db`), auto‑migrating older JSON sessions.
- **Project‑Specific Rules** — Auto‑load `.aizen_rules` or `.cursorrules` for repo‑specific behavior.
- **Smart Autocomplete** — TAB‑completion with `.gitignore` awareness and directory traversal.

## 💰 Cost Tracking

- Real‑time token counting for inputs and outputs.
- Current cost estimate shown in the CLI status bar.
- Supports Anthropic (Claude 3.5/3.7 Sonnet, Opus, Haiku), Google (Gemini 2.5 Pro/Flash), and OpenAI (GPT‑4o, o1, o3‑mini).

## 📌 Session Management

- `/checkpoint [name]` — Save conversation snapshots.
- `/restore [name]` — Restore a previous checkpoint.

## 📁 Structured Logging

- Logs stored at `~/.aizen_logs/aizen.log` (rotated, 5 MB caps, 3 files).
- Verbose flag mirrors output to console.

## 📦 Publishing & Development

- Use `publish.sh` to build and publish to PyPI, NPM, and PyInstaller binaries.