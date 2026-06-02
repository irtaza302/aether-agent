import os
import json
import re
import difflib
import fnmatch
import subprocess
from rich.panel import Panel
from rich.text import Text

from .config import console, SAFE_COMMAND_PREFIXES, DANGEROUS_PATTERNS
from .utils import BackupManager, truncate_output, load_gitignore_patterns, should_ignore, Struct

# ─── Tools Definition ──────────────────────────────────────────────────────────

tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the contents of a file. Use this to understand code before making changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to read.",
                    }
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Creates a new file or fully overwrites an existing one. For modifying existing files, prefer edit_file instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to create/overwrite.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The full content to write.",
                    },
                },
                "required": ["filepath", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Makes a surgical edit to an existing file by replacing a specific block of text with new text. Always use this instead of write_file when modifying existing files. The old_content must match exactly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to edit.",
                    },
                    "old_content": {
                        "type": "string",
                        "description": "The exact existing text block to find and replace. Must match the file content exactly.",
                    },
                    "new_content": {
                        "type": "string",
                        "description": "The replacement text.",
                    },
                },
                "required": ["filepath", "old_content", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Executes a shell command. Safe read-only commands run automatically; destructive commands require user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Lists files and folders in a directory, respecting .gitignore patterns. Shows file sizes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (defaults to '.').",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Searches for a text or regex pattern in files under a directory. Returns matching lines with file paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The text or regex pattern to search for.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (defaults to '.').",
                    },
                    "is_regex": {
                        "type": "boolean",
                        "description": "If true, treats query as a regex pattern. Default: false.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Finds files by name pattern (glob) across the workspace. Use this to locate files when you don't know the exact path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match filenames (e.g., '*.py', 'test_*.js', 'Dockerfile').",
                    },
                    "path": {
                        "type": "string",
                        "description": "Root directory to search from (defaults to '.').",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
]


# ─── Tool Implementations ──────────────────────────────────────────────────────

backup_manager = BackupManager()

def read_file(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        return f"[File: {filepath} | {line_count} lines]\n{content}"
    except Exception as e:
        return f"Error reading file: {e}"


def write_file_with_diff(filepath: str, content: str) -> str:
    try:
        old_content = ""
        exists = os.path.exists(filepath)

        if exists:
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    old_content = f.read()
            except Exception:
                pass

        if exists:
            diff = list(
                difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{filepath}",
                    tofile=f"b/{filepath}",
                    n=3,
                )
            )
            if not diff:
                return f"No changes to write for {filepath}"

            console.print(
                Panel(
                    f"[bold magenta]Aether wants to overwrite:[/bold magenta] [cyan]{filepath}[/cyan]",
                    border_style="magenta",
                )
            )
            for line in diff:
                if line.startswith("+") and not line.startswith("+++"):
                    console.print(f"[green]{line.rstrip()}[/green]")
                elif line.startswith("-") and not line.startswith("---"):
                    console.print(f"[red]{line.rstrip()}[/red]")
                elif line.startswith("@@"):
                    console.print(f"[cyan]{line.rstrip()}[/cyan]")
                else:
                    console.print(line.rstrip())
        else:
            preview_lines = content.split("\n")[:15]
            preview = "\n".join(preview_lines)
            total_lines = len(content.split("\n"))
            if total_lines > 15:
                preview += f"\n... ({total_lines} total lines)"
            console.print(
                Panel(
                    f"[bold magenta]Aether wants to create:[/bold magenta] [cyan]{filepath}[/cyan]\n\n"
                    f"[dim]{preview}[/dim]",
                    border_style="magenta",
                )
            )

        confirmation = input("  Allow? (y/n): ").strip().lower()
        if confirmation != "y":
            return "User denied file write operation."

        # Create backup before overwriting
        if exists:
            backup_manager.backup(filepath)

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✓ Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"


def edit_file(filepath: str, old_content: str, new_content: str) -> str:
    try:
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist. Use write_file to create new files."

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            file_content = f.read()

        # Check if old_content exists in the file
        occurrence_count = file_content.count(old_content)
        if occurrence_count == 0:
            # Try with normalized whitespace as a hint
            normalized_file = re.sub(r"[ \t]+", " ", file_content)
            normalized_old = re.sub(r"[ \t]+", " ", old_content)
            if normalized_old in normalized_file:
                return (
                    "Error: Exact match not found, but a similar block exists with different whitespace. "
                    "Please re-read the file and use the exact text including whitespace."
                )
            return (
                f"Error: Could not find the specified text in {filepath}. "
                f"Please read the file first to get the exact content."
            )

        if occurrence_count > 1:
            return (
                f"Error: Found {occurrence_count} occurrences of the target text in {filepath}. "
                f"Please provide a more specific/unique block to match exactly one location."
            )

        # Show diff preview
        new_file_content = file_content.replace(old_content, new_content, 1)
        diff = list(
            difflib.unified_diff(
                file_content.splitlines(keepends=True),
                new_file_content.splitlines(keepends=True),
                fromfile=f"a/{filepath}",
                tofile=f"b/{filepath}",
                n=3,
            )
        )

        if not diff:
            return "No changes detected."

        console.print(
            Panel(
                f"[bold magenta]Aether wants to edit:[/bold magenta] [cyan]{filepath}[/cyan]",
                border_style="magenta",
            )
        )
        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                console.print(f"[green]{line.rstrip()}[/green]")
            elif line.startswith("-") and not line.startswith("---"):
                console.print(f"[red]{line.rstrip()}[/red]")
            elif line.startswith("@@"):
                console.print(f"[cyan]{line.rstrip()}[/cyan]")
            else:
                console.print(line.rstrip())

        confirmation = input("  Apply edit? (y/n): ").strip().lower()
        if confirmation != "y":
            return "User denied the edit."

        # Create backup
        backup_manager.backup(filepath)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_file_content)

        return f"✓ Successfully edited {filepath}"
    except Exception as e:
        return f"Error editing file: {e}"


def is_command_safe(command: str) -> bool:
    """Check if a command is safe to auto-execute without confirmation."""
    cmd_stripped = command.strip()

    # Check dangerous patterns first
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_stripped):
            return False

    # Check safe prefixes
    for safe in SAFE_COMMAND_PREFIXES:
        if cmd_stripped == safe or cmd_stripped.startswith(safe + " "):
            return True

    return False


def run_command_impl(command: str, auto_approve: bool = False) -> str:
    safe = is_command_safe(command)

    if not safe and not auto_approve:
        console.print(
            Panel(
                f"[bold magenta]Aether wants to run:[/bold magenta]\n\n[white]{command}[/white]",
                border_style="magenta",
            )
        )
        confirmation = input("  Allow? (y/n): ").strip().lower()
        if confirmation != "y":
            return "User denied command execution."
    elif safe:
        console.print(f"  [dim]▶ {command}[/dim]")

    try:
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += f"\nSTDERR:\n{result.stderr}"
            else:
                output = result.stderr
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"
        return output.strip() if output.strip() else f"Command completed (exit code {result.returncode})"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds."
    except Exception as e:
        return f"Error executing command: {e}"


def list_directory(path: str = ".") -> str:
    try:
        if not path:
            path = "."
        if not os.path.exists(path):
            return f"Error: Path '{path}' does not exist."
        if not os.path.isdir(path):
            return f"Error: '{path}' is not a directory."

        items = os.listdir(path)
        ignore_patterns = load_gitignore_patterns()

        dirs = []
        files = []
        for item in sorted(items):
            item_path = os.path.join(path, item)
            if should_ignore(item_path, ignore_patterns):
                continue
            if os.path.isdir(item_path):
                dirs.append(f"📁 {item}/")
            else:
                try:
                    size = os.path.getsize(item_path)
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f}KB"
                    else:
                        size_str = f"{size / 1024 / 1024:.1f}MB"
                    files.append(f"📄 {item} ({size_str})")
                except OSError:
                    files.append(f"📄 {item}")

        if not dirs and not files:
            return f"Directory '{path}' is empty or all contents are ignored."

        result = ""
        if dirs:
            result += "\n".join(dirs)
        if files:
            if result:
                result += "\n"
            result += "\n".join(files)
        return result
    except Exception as e:
        return f"Error listing directory: {e}"


def grep_search(query: str, path: str = ".", is_regex: bool = False) -> str:
    try:
        if not path:
            path = "."
        if not os.path.exists(path):
            return f"Error: Path '{path}' does not exist."

        if is_regex:
            try:
                pattern = re.compile(query, re.IGNORECASE)
            except re.error as e:
                return f"Invalid regex pattern: {e}"

        ignore_patterns = load_gitignore_patterns()
        matches = []

        for root, dirs, files in os.walk(path):
            dirs[:] = [
                d
                for d in dirs
                if not should_ignore(os.path.join(root, d), ignore_patterns)
            ]

            for file in files:
                file_path = os.path.join(root, file)
                if should_ignore(file_path, ignore_patterns):
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            matched = False
                            if is_regex:
                                matched = bool(pattern.search(line))
                            else:
                                matched = query.lower() in line.lower()

                            if matched:
                                matches.append(
                                    f"{file_path}:{line_num}: {line.strip()}"
                                )
                                if len(matches) >= 50:
                                    return (
                                        "\n".join(matches)
                                        + "\n\n(Showing first 50 results)"
                                    )
                except (UnicodeDecodeError, PermissionError, OSError):
                    pass

        if not matches:
            return f"No matches found for '{query}'."
        return "\n".join(matches)
    except Exception as e:
        return f"Error searching: {e}"


def find_files(pattern: str, path: str = ".") -> str:
    try:
        if not path:
            path = "."
        if not os.path.exists(path):
            return f"Error: Path '{path}' does not exist."

        ignore_patterns = load_gitignore_patterns()
        matches = []

        for root, dirs, files in os.walk(path):
            dirs[:] = [
                d
                for d in dirs
                if not should_ignore(os.path.join(root, d), ignore_patterns)
            ]

            for file in files:
                if fnmatch.fnmatch(file, pattern) or fnmatch.fnmatch(
                    file.lower(), pattern.lower()
                ):
                    file_path = os.path.join(root, file)
                    if not should_ignore(file_path, ignore_patterns):
                        matches.append(file_path)
                        if len(matches) >= 100:
                            return (
                                "\n".join(matches) + "\n\n(Showing first 100 results)"
                            )

        if not matches:
            return f"No files matching '{pattern}' found."
        return "\n".join(matches)
    except Exception as e:
        return f"Error finding files: {e}"


# ─── Tool Dispatcher ───────────────────────────────────────────────────────────

def execute_tool(tool_call, auto_approve: bool = False) -> str:
    func_name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return "Error: Invalid JSON in tool arguments."

    tool_label = Text("  ⚙️  ", style="magenta")
    tool_label.append(func_name, style="dim magenta")

    if func_name == "read_file":
        tool_label.append(f" → {args.get('filepath', '?')}", style="dim")
        console.print(tool_label)
        return truncate_output(read_file(args.get("filepath")))

    elif func_name == "write_file":
        tool_label.append(f" → {args.get('filepath', '?')}", style="dim")
        console.print(tool_label)
        return write_file_with_diff(args.get("filepath"), args.get("content"))

    elif func_name == "edit_file":
        tool_label.append(f" → {args.get('filepath', '?')}", style="dim")
        console.print(tool_label)
        return edit_file(
            args.get("filepath"), args.get("old_content"), args.get("new_content")
        )

    elif func_name == "run_command":
        tool_label.append(f" → {args.get('command', '?')}", style="dim")
        console.print(tool_label)
        return truncate_output(run_command_impl(args.get("command"), auto_approve))

    elif func_name == "list_directory":
        p = args.get("path", ".")
        tool_label.append(f" → {p}", style="dim")
        console.print(tool_label)
        return truncate_output(list_directory(p))

    elif func_name == "grep_search":
        tool_label.append(f" → '{args.get('query', '?')}'", style="dim")
        console.print(tool_label)
        return truncate_output(
            grep_search(args.get("query"), args.get("path", "."), args.get("is_regex", False))
        )

    elif func_name == "find_files":
        tool_label.append(f" → {args.get('pattern', '?')}", style="dim")
        console.print(tool_label)
        return truncate_output(
            find_files(args.get("pattern"), args.get("path", "."))
        )

    else:
        console.print(tool_label)
        return f"Unknown tool: {func_name}"
