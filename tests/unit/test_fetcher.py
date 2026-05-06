"""Unit tests for URL fetcher, HTML parser, and robots checker.

Covers:
- src/search/fetcher/fetcher.py (URLFetcher, FetchResult)
- src/search/fetcher/parser.py (HTMLParser)
- src/search/fetcher/robots.py (RobotsChecker)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from src.search.fetcher.fetcher import URLFetcher, FetchResult
from src.search.fetcher.parser import HTMLParser
from src.search.fetcher.robots import RobotsChecker


# ---------------------------------------------------------------------------
# FetchResult
# ---------------------------------------------------------------------------

class TestFetchResult:
    """Tests for FetchResult dataclass."""

    def test_is_success_happy_path(self):
        r = FetchResult(url="https://x.com", status=200, content="ok")
        assert r.is_success() is True

    def test_is_success_non_200(self):
        r = FetchResult(url="https://x.com", status=404, content="not found")
        assert r.is_success() is False

    def test_is_success_200_no_content(self):
        r = FetchResult(url="https://x.com", status=200, content=None)
        assert r.is_success() is False

    def test_is_success_error(self):
        r = FetchResult(url="https://x.com", status=0, error="Timeout")
        assert r.is_success() is False

    def test_to_dict_roundtrip(self):
        r = FetchResult(
            url="https://x.com",
            status=200,
            content="hello",
            content_type="text/html",
            title="X",
            fetch_time_ms=42.0,
            byte_size=5,
        )
        d = r.to_dict()
        assert d["url"] == "https://x.com"
        assert d["status"] == 200
        assert d["content"] == "hello"
        assert d["title"] == "X"

    def test_to_dict_defaults(self):
        r = FetchResult(url="https://x.com", status=500)
        d = r.to_dict()
        assert d["content"] is None
        assert d["error"] is None


# ---------------------------------------------------------------------------
# URLFetcher
# ---------------------------------------------------------------------------

class TestURLFetcher:
    """Tests for URLFetcher."""

    def test_default_headers(self):
        f = URLFetcher()
        assert "User-Agent" in f.headers
        assert "OpenDsearch" in f.headers["User-Agent"]

    def test_custom_headers(self):
        f = URLFetcher(headers={"X-Custom": "yes"})
        assert f.headers["X-Custom"] == "yes"

    def test_extract_title_from_title_tag(self):
        f = URLFetcher()
        html = "<html><head><title>My Page</title></head><body></body></html>"
        assert f._extract_title(html) == "My Page"

    def test_extract_title_from_h1_fallback(self):
        f = URLFetcher()
        html = "<html><body><h1>Fallback Title</h1></body></html>"
        assert f._extract_title(html) == "Fallback Title"

    def test_extract_title_none(self):
        f = URLFetcher()
        html = "<html><body><p>No title here</p></body></html>"
        assert f._extract_title(html) is None

    def test_extract_title_strips_whitespace(self):
        f = URLFetcher()
        html = "<title>  Spaced Title  </title>"
        assert f._extract_title(html) == "Spaced Title"

    @pytest.mark.asyncio
    async def test_fetch_invalid_url(self):
        f = URLFetcher()
        result = await f.fetch("not-a-url")
        assert result.status == 0
        assert result.error == "Invalid URL"

    @pytest.mark.asyncio
    async def test_fetch_empty_url(self):
        f = URLFetcher()
        result = await f.fetch("")
        assert result.status == 0
        assert result.error == "Invalid URL"

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        f = URLFetcher()
        await f.close()  # Should not raise even with no session
        await f.close()  # Double close is fine

    @pytest.mark.asyncio
    async def test_context_manager(self):
        async with URLFetcher() as f:
            assert f is not None
        # Session should be cleaned up after context exit

    @pytest.mark.asyncio
    async def test_fetch_many_empty(self):
        f = URLFetcher()
        results = await f.fetch_many([])
        assert results == []
        await f.close()


# ---------------------------------------------------------------------------
# HTMLParser
# ---------------------------------------------------------------------------

class TestHTMLParser:
    """Tests for HTMLParser."""

    def test_parse_empty(self):
        p = HTMLParser()
        assert p.parse("") == ""

    def test_parse_none_like(self):
        p = HTMLParser()
        assert p.parse("") == ""

    def test_parse_basic_text(self):
        p = HTMLParser()
        html = "<p>Hello world</p>"
        result = p.parse(html)
        assert "Hello world" in result

    def test_parse_h1(self):
        p = HTMLParser()
        html = "<h1>Title</h1>"
        result = p.parse(html)
        assert "# Title" in result

    def test_parse_h2(self):
        p = HTMLParser()
        html = "<h2>Subtitle</h2>"
        result = p.parse(html)
        assert "## Subtitle" in result

    def test_parse_h3(self):
        p = HTMLParser()
        html = "<h3>Section</h3>"
        result = p.parse(html)
        assert "### Section" in result

    def test_parse_h4(self):
        p = HTMLParser()
        html = "<h4>Subsection</h4>"
        result = p.parse(html)
        assert "#### Subsection" in result

    def test_parse_h5(self):
        p = HTMLParser()
        html = "<h5>Minor</h5>"
        result = p.parse(html)
        assert "##### Minor" in result

    def test_parse_h6(self):
        p = HTMLParser()
        html = "<h6>Tiny</h6>"
        result = p.parse(html)
        assert "###### Tiny" in result

    def test_parse_link(self):
        p = HTMLParser()
        html = '<a href="https://example.com">Click here</a>'
        result = p.parse(html)
        assert "[Click here](https://example.com)" in result

    def test_parse_link_with_nested_tags(self):
        p = HTMLParser()
        html = '<a href="https://example.com"><strong>Bold Link</strong></a>'
        result = p.parse(html)
        assert "[Bold Link](https://example.com)" in result

    def test_parse_unordered_list(self):
        p = HTMLParser()
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = p.parse(html)
        assert "- Item 1" in result
        assert "- Item 2" in result

    def test_parse_ordered_list(self):
        p = HTMLParser()
        html = "<ol><li>First</li><li>Second</li></ol>"
        result = p.parse(html)
        assert "1. First" in result
        assert "2. Second" in result

    def test_parse_bold_strong(self):
        p = HTMLParser()
        html = "<strong>Bold text</strong>"
        result = p.parse(html)
        assert "**Bold text**" in result

    def test_parse_bold_b(self):
        p = HTMLParser()
        html = "<b>Bold text</b>"
        result = p.parse(html)
        assert "**Bold text**" in result

    def test_parse_italic_em(self):
        p = HTMLParser()
        html = "<em>Italic text</em>"
        result = p.parse(html)
        assert "*Italic text*" in result

    def test_parse_italic_i(self):
        p = HTMLParser()
        html = "<i>Italic text</i>"
        result = p.parse(html)
        assert "*Italic text*" in result

    def test_parse_inline_code(self):
        p = HTMLParser()
        html = "<code>var x = 1</code>"
        result = p.parse(html)
        assert "`var x = 1`" in result

    def test_parse_code_block(self):
        p = HTMLParser()
        html = "<pre><code>def hello():\n    pass</code></pre>"
        result = p.parse(html)
        assert "```" in result
        assert "def hello():" in result

    def test_parse_code_block_with_language(self):
        p = HTMLParser()
        html = '<pre><code class="language-python">print("hi")</code></pre>'
        result = p.parse(html)
        assert "```python" in result
        assert 'print("hi")' in result

    def test_parse_blockquote(self):
        p = HTMLParser()
        html = "<blockquote>This is a quote</blockquote>"
        result = p.parse(html)
        assert "> This is a quote" in result

    def test_parse_script_removed(self):
        p = HTMLParser()
        html = "<script>alert('xss')</script><p>Safe content</p>"
        result = p.parse(html)
        assert "alert" not in result
        assert "Safe content" in result

    def test_parse_style_removed(self):
        p = HTMLParser()
        html = "<style>body { color: red; }</style><p>Text</p>"
        result = p.parse(html)
        assert "color" not in result
        assert "Text" in result

    def test_parse_table(self):
        p = HTMLParser()
        html = "<table><tr><td>A</td><td>B</td></tr></table>"
        result = p.parse(html)
        assert "A" in result
        assert "B" in result

    def test_parse_html_entities(self):
        p = HTMLParser()
        html = "<p>5 &lt; 10 &amp; 10 &gt; 5</p>"
        result = p.parse(html)
        assert "5 < 10" in result
        assert "10 > 5" in result

    def test_parse_complex_document(self):
        p = HTMLParser()
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Main Title</h1>
            <p>Some paragraph text with <strong>bold</strong> and <em>italic</em>.</p>
            <ul>
                <li>First item</li>
                <li>Second item</li>
            </ul>
            <a href="https://example.com">A link</a>
        </body>
        </html>
        """
        result = p.parse(html)
        assert "# Main Title" in result
        assert "**bold**" in result
        assert "*italic*" in result
        assert "- First item" in result
        assert "[A link](https://example.com)" in result

    def test_parse_nested_lists(self):
        p = HTMLParser()
        html = "<ul><li>Outer<ul><li>Inner</li></ul></li></ul>"
        result = p.parse(html)
        assert "Outer" in result
        assert "Inner" in result

    def test_parse_preserves_whitespace_in_code(self):
        p = HTMLParser()
        html = "<pre><code>  indented\n    more</code></pre>"
        result = p.parse(html)
        assert "indented" in result

    def test_parse_empty_tags(self):
        p = HTMLParser()
        html = "<p></p><h1></h1>"
        result = p.parse(html)
        # Should not crash, just produce clean output
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# RobotsChecker
# ---------------------------------------------------------------------------

class TestRobotsChecker:
    """Tests for RobotsChecker."""

    def test_parse_robots_empty(self):
        rc = RobotsChecker(user_agent="TestBot")
        disallowed, allowed = rc._parse_robots("")
        assert disallowed == set()
        assert allowed == set()

    def test_parse_robots_wildcard_disallow(self):
        rc = RobotsChecker(user_agent="TestBot")
        text = """
User-agent: *
Disallow: /admin/
Disallow: /private/
"""
        disallowed, allowed = rc._parse_robots(text)
        assert "/admin/" in disallowed
        assert "/private/" in disallowed

    def test_parse_robots_specific_agent(self):
        rc = RobotsChecker(user_agent="TestBot")
        text = """
User-agent: TestBot
Disallow: /bot-specific/
User-agent: *
Disallow: /general/
"""
        disallowed, allowed = rc._parse_robots(text)
        # Only our agent's rules should be picked up
        assert "/bot-specific/" in disallowed

    def test_parse_robots_allow_directive(self):
        rc = RobotsChecker(user_agent="TestBot")
        text = """
User-agent: *
Disallow: /
Allow: /public/
"""
        disallowed, allowed = rc._parse_robots(text)
        assert "/" in disallowed
        assert "/public/" in allowed

    def test_parse_robots_comments_stripped(self):
        rc = RobotsChecker(user_agent="TestBot")
        text = """
User-agent: * # this is a comment
Disallow: /admin/ # another comment
"""
        disallowed, allowed = rc._parse_robots(text)
        assert "/admin/" in disallowed

    def test_parse_robots_empty_disallow(self):
        """Empty Disallow means allow everything (equivalent to Allow: /)."""
        rc = RobotsChecker(user_agent="TestBot")
        text = """
User-agent: *
Disallow:
"""
        disallowed, allowed = rc._parse_robots(text)
        # Empty value should not be added
        assert len(disallowed) == 0

    @pytest.mark.asyncio
    async def test_is_allowed_no_robots(self):
        """No robots.txt means everything is allowed."""
        rc = RobotsChecker(user_agent="TestBot")
        with patch.object(rc, "_get_rules", new_callable=AsyncMock, return_value=None):
            assert await rc.is_allowed("https://example.com/page") is True

    @pytest.mark.asyncio
    async def test_is_allowed_disallowed_path(self):
        rc = RobotsChecker(user_agent="TestBot")
        import time
        rules = (time.time(), {"/admin/"}, set())
        with patch.object(rc, "_get_rules", new_callable=AsyncMock, return_value=rules):
            assert await rc.is_allowed("https://example.com/admin/secret") is False

    @pytest.mark.asyncio
    async def test_is_allowed_allowed_path(self):
        rc = RobotsChecker(user_agent="TestBot")
        import time
        rules = (time.time(), {"/"}, {"/public/"})
        with patch.object(rc, "_get_rules", new_callable=AsyncMock, return_value=rules):
            # Allow is more specific and should win
            assert await rc.is_allowed("https://example.com/public/file") is True

    @pytest.mark.asyncio
    async def test_is_allowed_normal_path(self):
        rc = RobotsChecker(user_agent="TestBot")
        import time
        rules = (time.time(), {"/admin/"}, set())
        with patch.object(rc, "_get_rules", new_callable=AsyncMock, return_value=rules):
            assert await rc.is_allowed("https://example.com/page") is True

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        rc = RobotsChecker(user_agent="TestBot")
        rc._session = None
        await rc.close()  # Should not raise
        await rc.close()  # Double close is fine

    def test_parse_robots_case_insensitive_directive(self):
        rc = RobotsChecker(user_agent="TestBot")
        text = """
user-agent: *
disallow: /secret/
"""
        disallowed, allowed = rc._parse_robots(text)
        assert "/secret/" in disallowed

    def test_parse_robots_ignores_malformed_lines(self):
        rc = RobotsChecker(user_agent="TestBot")
        text = """
User-agent: *
this is not valid
Disallow: /admin/
"""
        disallowed, allowed = rc._parse_robots(text)
        assert "/admin/" in disallowed
        # Should not crash on malformed lines


# ---------------------------------------------------------------------------
# URLFetcher with mocked aiohttp (integration-style unit tests)
# ---------------------------------------------------------------------------

class TestURLFetcherMockedHTTP:
    """Test URLFetcher.fetch with mocked aiohttp sessions."""

    @pytest.mark.asyncio
    async def test_fetch_success(self):
        f = URLFetcher()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.read = AsyncMock(return_value=b"<html><head><title>Test</title></head><body>Hello</body></html>")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        with patch.object(f, "_get_session", new_callable=AsyncMock) as mock_session:
            mock_session.return_value.get = MagicMock(return_value=mock_response)
            # Disable robots check for speed
            f._respect_robots = False

            result = await f.fetch("https://example.com/page")

        assert result.status == 200
        assert result.title == "Test"
        assert "Hello" in result.content
        assert result.fetch_time_ms > 0

    @pytest.mark.asyncio
    async def test_fetch_404(self):
        f = URLFetcher()
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        with patch.object(f, "_get_session", new_callable=AsyncMock) as mock_session:
            mock_session.return_value.get = MagicMock(return_value=mock_response)
            f._respect_robots = False

            result = await f.fetch("https://example.com/missing")

        assert result.status == 404
        assert result.error == "HTTP 404"
        assert result.content is None

    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        import asyncio
        f = URLFetcher()
        f._respect_robots = False

        with patch.object(f, "_get_session", new_callable=AsyncMock) as mock_session:
            mock_session.return_value.get = MagicMock(
                side_effect=asyncio.TimeoutError()
            )

            result = await f.fetch("https://example.com/slow")

        assert result.status == 0
        assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_fetch_client_error(self):
        import aiohttp
        f = URLFetcher()
        f._respect_robots = False

        with patch.object(f, "_get_session", new_callable=AsyncMock) as mock_session:
            mock_session.return_value.get = MagicMock(
                side_effect=aiohttp.ClientError("Connection refused")
            )

            result = await f.fetch("https://example.com/down")

        assert result.status == 0
        assert "Client error" in result.error

    @pytest.mark.asyncio
    async def test_fetch_large_content(self):
        f = URLFetcher()
        f.max_size = 100  # Very small limit
        f._respect_robots = False

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.read = AsyncMock(return_value=b"x" * 200)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        with patch.object(f, "_get_session", new_callable=AsyncMock) as mock_session:
            mock_session.return_value.get = MagicMock(return_value=mock_response)

            result = await f.fetch("https://example.com/huge")

        assert result.error is not None
        assert "too large" in result.error.lower()

    @pytest.mark.asyncio
    async def test_fetch_robots_blocks(self):
        """When robots.txt disallows, fetch should return 403."""
        f = URLFetcher()
        f._respect_robots = True

        mock_checker = AsyncMock()
        mock_checker.is_allowed = AsyncMock(return_value=False)
        f._robots_checker = mock_checker

        result = await f.fetch("https://example.com/admin/secret")
        assert result.status == 403
        assert "robots.txt" in result.error

    @pytest.mark.asyncio
    async def test_fetch_many_concurrent(self):
        f = URLFetcher()
        f._respect_robots = False

        urls = ["https://a.com/1", "https://b.com/2", "https://c.com/3"]

        async def fake_fetch(url):
            return FetchResult(url=url, status=200, content=f"content-{url}")

        with patch.object(f, "fetch", side_effect=fake_fetch):
            results = await f.fetch_many(urls, max_concurrent=2)

        assert len(results) == 3
        assert all(r.status == 200 for r in results)

    @pytest.mark.asyncio
    async def test_fetch_unicode_content(self):
        f = URLFetcher()
        f._respect_robots = False

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.read = AsyncMock(return_value="<p>Héllo wörld 你好</p>".encode("utf-8"))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        with patch.object(f, "_get_session", new_callable=AsyncMock) as mock_session:
            mock_session.return_value.get = MagicMock(return_value=mock_response)

            result = await f.fetch("https://example.com/unicode")

        assert result.status == 200
        assert "Héllo" in result.content
        assert "你好" in result.content
