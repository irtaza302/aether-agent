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


class TestListDirectory:
    """Tests for directory listing."""

    def test_list_current_dir(self, sample_dir):
        old_cwd = os.getcwd()
        try:
            os.chdir(sample_dir)
            result = list_directory(".")
            assert "src" in result
            assert "README.md" in result
        finally:
            os.chdir(old_cwd)

    def test_list_nonexistent_dir(self):
        result = list_directory("/nonexistent/path")
        assert "Error" in result

    def test_list_respects_gitignore(self, sample_dir):
        old_cwd = os.getcwd()
        try:
            os.chdir(sample_dir)
            result = list_directory(".")
            assert "node_modules" not in result
        finally:
            os.chdir(old_cwd)


class TestGrepSearch:
    """Tests for grep search."""

    def test_basic_search(self, sample_dir):
        result = grep_search("hello", sample_dir)
        assert "hello" in result.lower()

    def test_search_no_results(self, sample_dir):
        result = grep_search("zzz_nonexistent_pattern_zzz", sample_dir)
        assert "No matches" in result

    def test_regex_search(self, sample_dir):
        result = grep_search(r"def \w+", sample_dir, is_regex=True)
        assert "def" in result

    def test_invalid_regex(self, sample_dir):
        result = grep_search("[invalid", sample_dir, is_regex=True)
        assert "Invalid regex" in result


class TestFindFiles:
    """Tests for file finding."""

    def test_find_by_extension(self, sample_dir):
        result = find_files("*.py", sample_dir)
        assert "main.py" in result
        assert "utils.py" in result

    def test_find_by_name(self, sample_dir):
        result = find_files("README.md", sample_dir)
        assert "README.md" in result

    def test_find_no_results(self, sample_dir):
        result = find_files("*.xyz", sample_dir)
        assert "No files" in result


