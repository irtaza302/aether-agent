"""Tests for aizen.plugins module."""

from unittest.mock import patch

import pytest

from aizen.plugins import PluginManager
from aizen.utils import Struct


@pytest.fixture
def temp_plugins_dir(tmp_path):
    """Fixture that overrides PLUGINS_DIR to a temporary directory."""
    with patch("aizen.plugins.PLUGINS_DIR", str(tmp_path)):
        yield tmp_path


def test_plugin_manager_empty_dir(temp_plugins_dir):
    pm = PluginManager()
    assert pm.get_tools() == []
    assert pm.plugins == {}


def test_plugin_manager_loads_valid_plugin(temp_plugins_dir):
    # Create a dummy plugin
    plugin_content = """
def get_tools():
    return [{
        "type": "function",
        "function": {
            "name": "dummy_tool",
            "description": "A dummy tool"
        }
    }]

def execute_tool(tool_call, auto_approve=False):
    return "dummy result"
"""
    plugin_path = temp_plugins_dir / "my_plugin.py"
    plugin_path.write_text(plugin_content)

    pm = PluginManager()

    assert "my_plugin" in pm.plugins
    assert len(pm.get_tools()) == 1
    assert pm.get_tools()[0]["function"]["name"] == "dummy_tool"

    # Test execution
    tool_call = Struct(
        id="call_1",
        type="function",
        function=Struct(name="dummy_tool", arguments="{}")
    )
    result = pm.execute_tool(tool_call)
    assert result == "dummy result"


def test_plugin_manager_ignores_invalid_plugin(temp_plugins_dir):
    # Missing execute_tool
    plugin_content = """
def get_tools():
    return []
"""
    plugin_path = temp_plugins_dir / "bad_plugin.py"
    plugin_path.write_text(plugin_content)

    # Should not crash, just ignore
    pm = PluginManager()
    assert "bad_plugin" not in pm.plugins
    assert len(pm.get_tools()) == 0


def test_plugin_manager_ignores_underscores_and_non_py(temp_plugins_dir):
    (temp_plugins_dir / "_ignored.py").write_text("invalid python code")
    (temp_plugins_dir / "not_python.txt").write_text("hello")

    pm = PluginManager()
    assert len(pm.plugins) == 0


def test_plugin_manager_execution_error(temp_plugins_dir):
    plugin_content = """
def get_tools():
    return [{"type": "function", "function": {"name": "fail_tool"}}]

def execute_tool(tool_call, auto_approve=False):
    raise ValueError("Plugin failed")
"""
    (temp_plugins_dir / "fail_plugin.py").write_text(plugin_content)

    pm = PluginManager()
    tool_call = Struct(
        id="call_1",
        type="function",
        function=Struct(name="fail_tool", arguments="{}")
    )

    result = pm.execute_tool(tool_call)
    assert "Error executing plugin tool fail_tool: Plugin failed" in result


def test_plugin_manager_unhandled_tool(temp_plugins_dir):
    pm = PluginManager()
    tool_call = Struct(
        id="call_1",
        type="function",
        function=Struct(name="unknown_tool", arguments="{}")
    )

    # Should return None for unhandled tools
    result = pm.execute_tool(tool_call)
    assert result is None
