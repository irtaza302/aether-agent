"""Tests for aizen.tools package."""


from aizen.tools.helpers import detect_language, is_binary_file, try_repair_json


class TestHelpers:
    """Tests for helper functions."""

    def test_binary_detection(self):
        assert is_binary_file("image.png") is True
        assert is_binary_file("photo.jpg") is True
        assert is_binary_file("doc.pdf") is True
        assert is_binary_file("code.py") is False
        assert is_binary_file("readme.md") is False
        assert is_binary_file("data.json") is False

    def test_language_detection(self):
        assert detect_language("main.py") == "python"
        assert detect_language("app.js") == "javascript"
        assert detect_language("style.css") == "css"
        assert detect_language("config.yaml") == "yaml"
        assert detect_language("Dockerfile") == "dockerfile"
        assert detect_language("unknown.xyz") == "text"

    def test_json_repair_valid(self):
        result = try_repair_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_repair_trailing_comma(self):
        result = try_repair_json('{"key": "value",}')
        assert result == {"key": "value"}

    def test_json_repair_irreparable(self):
        result = try_repair_json("not json at all")
        assert result is None


