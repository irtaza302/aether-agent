"""
Aizen tools package.

Re-exports the public API for backwards compatibility:
- `tools` — the tool schema list sent to the AI model
- `execute_tool` — dispatches tool calls to implementations
- `backup_manager` — file backup/undo manager
"""

from .dispatcher import execute_tool, tools
from .helpers import backup_manager

__all__ = ["tools", "execute_tool", "backup_manager"]
