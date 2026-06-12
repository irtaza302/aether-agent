"""Tests for aizen.tools package."""

import os
from unittest.mock import patch

from aizen.tools.commands import is_command_safe, run_command_impl


class TestCommandSafety:
    """Tests for command safety checks."""

    def test_safe_commands(self):
        assert is_command_safe("ls") is True
        assert is_command_safe("ls -la") is True
        assert is_command_safe("git status") is True
        assert is_command_safe("git log --oneline") is True
        assert is_command_safe("cat file.txt") is True
        assert is_command_safe("python --version") is True

    def test_dangerous_commands(self):
        assert is_command_safe("rm -rf /") is False
        assert is_command_safe("sudo apt install") is False
        assert is_command_safe("chmod 777 file") is False
        assert is_command_safe("kill -9 1234") is False

    def test_unknown_commands_unsafe(self):
        assert is_command_safe("npm install") is False
        assert is_command_safe("pip install requests") is False
        assert is_command_safe("make build") is False


class TestRunCommand:
    """Tests for command execution."""

    def test_run_simple_command(self):
        result = run_command_impl("echo 'hello'", auto_approve=True)
        assert "hello" in result

    def test_run_failing_command(self):
        result = run_command_impl("false", auto_approve=True)
        assert "Exit code:" in result or "exit code" in result.lower()

    def test_run_command_timeout(self):
        result = run_command_impl("sleep 10", auto_approve=True, timeout=2)
        assert "timed out" in result.lower()

    def test_run_command_user_deny(self):
        with patch("builtins.input", return_value="n"):
            result = run_command_impl("npm install", auto_approve=False)
        assert "denied" in result.lower()

    def test_run_command_with_stderr(self):
        result = run_command_impl("echo 'err' >&2", auto_approve=True)
        assert "err" in result

    def test_run_command_persistent_cd(self, tmp_dir):
        old_cwd = os.getcwd()
        try:
            # Create a test directory
            test_dir = os.path.join(tmp_dir, "cd_test")
            os.makedirs(test_dir, exist_ok=True)

            # Change to it using the tool
            run_command_impl(f"cd {test_dir}", auto_approve=True)
            assert os.getcwd() == os.path.realpath(test_dir)
        finally:
            os.chdir(old_cwd)

    def test_run_command_background(self):
        from aizen.tools.commands import check_background_task_impl, kill_background_task_impl
        # Start a background task
        result = run_command_impl("sleep 10", auto_approve=True, background=True)
        assert "Task started in background with ID:" in result

        # Extract task ID
        task_id = result.split("ID: ")[1].strip()

        # Check task status
        status = check_background_task_impl(task_id)
        assert "Status: RUNNING" in status

        # Kill the task
        kill_result = kill_background_task_impl(task_id)
        assert "killed" in kill_result

        # Ensure it's removed
        assert "Error: No such background task" in check_background_task_impl(task_id)


