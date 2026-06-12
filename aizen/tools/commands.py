"""
Command execution tools: run_command, background task management.
"""

import os
import re
import subprocess
import threading
import time
import uuid
from typing import Any

from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from ..config import DANGEROUS_PATTERNS, SAFE_COMMAND_PREFIXES, Theme, console
from ..logging_config import logger
from .helpers import _ask_permission, terminal_lock

# Global dictionary for tracking background tasks
# task_id -> {"process": Popen, "stdout": list, "stderr": list, "command": str}
background_tasks: dict[str, dict[str, Any]] = {}
background_tasks_lock = threading.Lock()  # Protects background_tasks dict


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


def run_command_impl(command: str, auto_approve: bool = False, timeout: int = 120, background: bool = False) -> str:
    """Execute a shell command with safety checks, configurable timeout, and live output."""
    logger.debug("run_command: %s (timeout=%ds, background=%s)", command, timeout, background)

    # Intercept pure 'cd' commands to update process working directory persistently
    cmd_stripped = command.strip()
    if cmd_stripped.startswith("cd ") and not any(sep in cmd_stripped for sep in ["&&", ";", "||", "|"]):
        target_dir = cmd_stripped[3:].strip()
        target_dir = os.path.expanduser(target_dir.strip("\"'"))
        try:
            os.chdir(target_dir)
            new_cwd = os.getcwd()
            logger.info("Changed working directory to %s", new_cwd)
            console.print(f"  [dim]▶ Changed directory to {new_cwd}[/dim]")
            return f"Working directory changed to {new_cwd}"
        except Exception as e:
            logger.error("Failed to change directory to '%s': %s", target_dir, e)
            return f"Error changing directory: {e}"
    safe = is_command_safe(command)

    if not safe:
        console.print(
            Panel(
                f"[bold {Theme.ACCENT}]◆ AIZEN[/bold {Theme.ACCENT}] [{Theme.TEXT}]wants to run:[/{Theme.TEXT}]\n\n[bold {Theme.TEXT}]{command}[/bold {Theme.TEXT}]",
                border_style=Theme.BORDER,
            )
        )
        with terminal_lock:
            if not _ask_permission("  ▸ Allow?", auto_approve):
                return "User denied command execution."
    elif safe:
        console.print(f"  [dim]▶ {command}{' (background)' if background else ''}[/dim]")

    try:
        # Use Popen for streaming output with live display
        import select  # Not available at module level on all platforms

        proc = subprocess.Popen(
            command,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if background:
            task_id = f"bg_{uuid.uuid4().hex[:8]}"
            task_info = {
                "process": proc,
                "stdout": [],
                "stderr": [],
                "command": command,
                "start_time": time.time()
            }
            with background_tasks_lock:
                background_tasks[task_id] = task_info

            def stream_reader(pipe, dest_list):
                for line in iter(pipe.readline, ''):
                    dest_list.append(line)
                pipe.close()

            threading.Thread(target=stream_reader, args=(proc.stdout, task_info["stdout"]), daemon=True).start()
            threading.Thread(target=stream_reader, args=(proc.stderr, task_info["stderr"]), daemon=True).start()

            return f"Task started in background with ID: {task_id}"

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        start_time = time.time()

        with Live(
            Text("  ▶ Running...", style="dim italic"),
            console=console,
            refresh_per_second=4,
            transient=True,
        ) as live:
            while proc.poll() is None:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    proc.kill()
                    logger.warning("Command timed out after %ds: %s", timeout, command)
                    return f"Error: Command timed out after {timeout} seconds."

                reads = []
                if proc.stdout:
                    reads.append(proc.stdout)
                if proc.stderr:
                    reads.append(proc.stderr)

                if reads:
                    rlist, _, _ = select.select(reads, [], [], 0.1)
                    for fd in rlist:
                        if fd == proc.stdout:
                            line = proc.stdout.readline()
                            if line:
                                stdout_lines.append(line)
                                tail = "".join(stdout_lines[-15:])
                                display = Text()
                                display.append(f"  ▶ Running ({elapsed:.0f}s)\n", style="dim italic")
                                display.append(tail.rstrip(), style="dim")
                                live.update(display)
                        elif fd == proc.stderr:
                            line = proc.stderr.readline()
                            if line:
                                stderr_lines.append(line)

            # Read remaining output after process exits
            if proc.stdout:
                remaining = proc.stdout.read()
                if remaining:
                    stdout_lines.append(remaining)
            if proc.stderr:
                stderr_lines.append(proc.stderr.read())

        output = "".join(stdout_lines)
        stderr_output = "".join(stderr_lines).strip()

        if stderr_output:
            if output:
                output += f"\nSTDERR:\n{stderr_output}"
            else:
                output = stderr_output
        if proc.returncode != 0:
            output += f"\n[Exit code: {proc.returncode}]"
        return output.strip() if output.strip() else f"Command completed (exit code {proc.returncode})"
    except subprocess.TimeoutExpired:
        logger.warning("Command timed out after %ds: %s", timeout, command)
        return f"Error: Command timed out after {timeout} seconds."
    except Exception as e:
        logger.exception("Error executing command: %s", command)
        return f"Error executing command: {e}"


def check_background_task_impl(task_id: str) -> str:
    """Checks the status of a background task and returns its recent output."""
    with background_tasks_lock:
        if task_id not in background_tasks:
            return f"Error: No such background task '{task_id}'."
        task = background_tasks[task_id]

    proc = task["process"]

    out_lines = list(task["stdout"])
    err_lines = list(task["stderr"])

    stdout_str = "".join(out_lines[-100:]).strip()
    stderr_str = "".join(err_lines[-100:]).strip()

    status = "RUNNING" if proc.poll() is None else f"FINISHED (Exit code {proc.returncode})"

    result = f"Task: {task_id}\nCommand: {task['command']}\nStatus: {status}\n\n"
    if stdout_str:
        result += f"--- STDOUT (last 100 lines) ---\n{stdout_str}\n\n"
    if stderr_str:
        result += f"--- STDERR (last 100 lines) ---\n{stderr_str}\n"

    # Cleanup if done
    if proc.poll() is not None:
        with background_tasks_lock:
            background_tasks.pop(task_id, None)

    return result.strip()


def kill_background_task_impl(task_id: str) -> str:
    """Kills a running background task."""
    with background_tasks_lock:
        if task_id not in background_tasks:
            return f"Error: No such background task '{task_id}'."
        task = background_tasks.pop(task_id)

    proc = task["process"]

    if proc.poll() is None:
        proc.kill()
        return f"Task {task_id} killed."
    else:
        return f"Task {task_id} was already finished."
