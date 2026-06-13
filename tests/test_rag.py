"""
RAG Pipeline Unit Tests.

Tests for the data processing and RAG components.
"""

import pytest

from app.utils.data_loader import clean_html


class TestCleanHTML:
    """Tests for the HTML cleaning function."""

    def test_plain_text_passthrough(self):
        """Plain text should pass through unchanged."""
        assert clean_html("Hello world") == "Hello world"

    def test_remove_simple_tags(self):
        """Simple HTML tags should be removed."""
        result = clean_html("<p>Hello <b>world</b></p>")
        assert "Hello" in result
        assert "world" in result
        assert "<p>" not in result
        assert "<b>" not in result

    def test_preserve_code_blocks(self):
        """Code blocks should be preserved with markdown formatting."""
        html = "<p>Use this:</p><code>print('hello')</code>"
        result = clean_html(html)
        assert "print('hello')" in result

    def test_multiline_code_blocks(self):
        """Multi-line code should get fenced code block formatting."""
        html = "<code>def foo():\n    return 42</code>"
        result = clean_html(html)
        assert "def foo():" in result
        assert "return 42" in result
        assert "```python" in result

    def test_empty_string(self):
        """Empty string should return empty."""
        assert clean_html("") == ""

    def test_none_input(self):
        """None input should return empty string."""
        assert clean_html(None) == ""

    def test_nested_html(self):
        """Nested HTML should be properly cleaned."""
        html = "<div><p>Outer <span>inner</span> text</p></div>"
        result = clean_html(html)
        assert "Outer" in result
        assert "inner" in result
        assert "text" in result
        assert "<div>" not in result

    def test_html_entities(self):
        """HTML entities should be decoded."""
        html = "<p>A &amp; B &lt; C</p>"
        result = clean_html(html)
        assert "A & B < C" in result
