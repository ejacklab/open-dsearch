"""Tests for robots.txt compliance checker."""

import pytest

from src.search.fetcher.robots import RobotsChecker


@pytest.fixture
def checker():
    return RobotsChecker(user_agent="OpenDsearch/0.2.0")


class TestParseRobots:
    def test_empty_robots(self, checker):
        disallowed, allowed = checker._parse_robots("")
        assert disallowed == set()
        assert allowed == set()

    def test_wildcard_disallow(self, checker):
        text = "User-agent: *\nDisallow: /private/\nDisallow: /admin/"
        disallowed, allowed = checker._parse_robots(text)
        assert "/private/" in disallowed
        assert "/admin/" in disallowed

    def test_specific_agent_disallow(self, checker):
        text = "User-agent: opendsearch/0.2.0\nDisallow: /search/"
        disallowed, allowed = checker._parse_robots(text)
        assert "/search/" in disallowed

    def test_allow_overrides(self, checker):
        text = (
            "User-agent: *\n"
            "Disallow: /\n"
            "Allow: /public/\n"
        )
        disallowed, allowed = checker._parse_robots(text)
        assert "/" in disallowed
        assert "/public/" in allowed

    def test_comments_ignored(self, checker):
        text = "# This is a comment\nUser-agent: *\nDisallow: /tmp/ # inline comment"
        disallowed, allowed = checker._parse_robots(text)
        assert "/tmp/" in disallowed

    def test_non_matching_agent_ignored(self, checker):
        text = "User-agent: GoogleBot\nDisallow: /secret/"
        disallowed, allowed = checker._parse_robots(text)
        assert "/secret/" not in disallowed


class TestRobotsCheckerUnit:
    """Unit tests for path matching logic."""

    def test_disallowed_path_blocked(self, checker):
        checker._cache["https://example.com"] = (
            9999999999.0,
            {"/private/", "/admin/"},
            set(),
        )
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            checker.is_allowed("https://example.com/private/data")
        )
        assert result is False

    def test_allowed_path_permitted(self, checker):
        checker._cache["https://example.com"] = (
            9999999999.0,
            {"/"},
            {"/public/"},
        )
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            checker.is_allowed("https://example.com/public/page")
        )
        assert result is True

    def test_unrelated_path_disallowed_by_root(self, checker):
        checker._cache["https://example.com"] = (
            9999999999.0,
            {"/"},
            set(),
        )
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            checker.is_allowed("https://example.com/anything")
        )
        assert result is False
