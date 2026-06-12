"""Tests for aizen.tools package."""

import json
import os
from unittest.mock import patch

from aizen.tools import backup_manager, execute_tool
from aizen.tools.helpers import detect_language, is_binary_file, try_repair_json
from aizen.tools.file_ops import read_file, replace_file_content, write_file_with_diff
from aizen.tools.commands import is_command_safe, run_command_impl
from aizen.tools.search import find_files, grep_search, list_directory
from aizen.utils import Struct


class TestExecuteTool:
    """Tests for the tool dispatcher."""

    def test_execute_read_file(self, sample_file):
        tool_call = Struct(
            id="call_1",
            type="function",
            function=Struct(
                name="read_file",
                arguments=json.dumps({"filepath": sample_file}),
            ),
        )
        result = execute_tool(tool_call)
        assert "def hello():" in result

    def test_execute_unknown_tool(self):
        tool_call = Struct(
            id="call_1",
            type="function",
            function=Struct(
                name="nonexistent_tool",
                arguments="{}",
            ),
        )
        result = execute_tool(tool_call)
        assert "Unknown tool" in result

    def test_execute_invalid_json(self):
        tool_call = Struct(
            id="call_1",
            type="function",
            function=Struct(
                name="read_file",
                arguments="not valid json {{{",
            ),
        )
        result = execute_tool(tool_call)
        assert "Error" in result or "Invalid JSON" in result

    def test_execute_repaired_json(self, sample_file):
        # Trailing comma — should be repaired
        tool_call = Struct(
            id="call_1",
            type="function",
            function=Struct(
                name="read_file",
                arguments=f'{{"filepath": "{sample_file}",}}',
            ),
        )
        result = execute_tool(tool_call)
        assert "def hello():" in result

    def test_execute_replace_file_content(self, sample_file):
        tool_call = Struct(
            id="call_1",
            type="function",
            function=Struct(
                name="replace_file_content",
                arguments=json.dumps({
                    "filepath": sample_file,
                    "target_content": 'print("Hello, world!")',
                    "replacement_content": 'print("Aizen Test!")',
                    "start_line": 1,
                    "end_line": 999
                }),
            ),
        )
        result = execute_tool(tool_call, auto_approve=True)
        assert "✓" in result
        with open(sample_file) as f:
            assert 'print("Aizen Test!")' in f.read()
