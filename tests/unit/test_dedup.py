"""Comprehensive unit tests for result deduplication."""

import pytest

from src.search.providers.base import SearchResult
from src.search.ranking.dedup import Deduplicator, DedupConfig


def _make_result(
    title: str = "Test Result",
    url: str = "https://example.com",
    snippet: str = "A test search result snippet",
    source: str = "test",
) -> SearchResult:
    """Helper to create a SearchResult with defaults."""
    return SearchResult(title=title, url=url, snippet=snippet, source=source)


# ── DedupConfig ──────────────────────────────────────────────────────────────


class TestDedupConfig:
    """Tests for DedupConfig defaults and customization."""

    def test_default_config(self):
        config = DedupConfig()
        assert config.normalize_urls is True
        assert config.ignore_fragments is True
        assert config.content_similarity_threshold == 0.5
        assert config.min_content_length == 20
        assert config.max_per_domain == 3

    def test_default_ignore_query_params(self):
        config = DedupConfig()
        assert "utm_source" in config.ignore_query_params
        assert "fbclid" in config.ignore_query_params
        assert "gclid" in config.ignore_query_params

    def test_custom_threshold(self):
        config = DedupConfig(content_similarity_threshold=0.8)
        assert config.content_similarity_threshold == 0.8

    def test_custom_max_per_domain(self):
        config = DedupConfig(max_per_domain=5)
        assert config.max_per_domain == 5


# ── URL-based deduplication ──────────────────────────────────────────────────


class TestUrlDeduplication:
    """Tests for URL normalization and deduplication."""

    def test_exact_url_duplicate_removed(self):
        dedup = Deduplicator()
        results = [
            _make_result(url="https://example.com/page1", snippet="Content about page one"),
            _make_result(url="https://example.com/page1", snippet="Content about page one again"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_different_urls_kept(self):
        dedup = Deduplicator(DedupConfig(max_per_domain=10, content_similarity_threshold=0.99))
        results = [
            _make_result(url="https://example.com/page1", snippet="Django web framework installation setup"),
            _make_result(url="https://example.com/page2", snippet="Flask micro framework configuration deployment"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 2

    def test_case_insensitive_url(self):
        dedup = Deduplicator()
        results = [
            _make_result(url="https://Example.com/Page", snippet="First version of content here"),
            _make_result(url="https://example.com/page", snippet="Second version of content here"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_www_prefix_normalized(self):
        dedup = Deduplicator()
        results = [
            _make_result(url="https://www.example.com/page", snippet="WWW version content"),
            _make_result(url="https://example.com/page", snippet="Non-WWW version content"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_trailing_slash_normalized(self):
        dedup = Deduplicator()
        results = [
            _make_result(url="https://example.com/page/", snippet="With slash content"),
            _make_result(url="https://example.com/page", snippet="Without slash content"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_http_vs_https_not_deduped_by_url(self):
        """Different schemes survive URL dedup but may still be caught by content similarity."""
        config = DedupConfig(max_per_domain=10, content_similarity_threshold=0.99)
        dedup = Deduplicator(config)
        results = [
            _make_result(url="https://example.com/page", snippet="Secure version of the content here"),
            _make_result(url="http://example.com/page", snippet="Insecure version of the content here"),
        ]
        deduped = dedup.deduplicate(results)
        # With very high threshold and different snippets, both should survive
        assert len(deduped) == 2

    def test_utm_params_ignored(self):
        dedup = Deduplicator()
        results = [
            _make_result(url="https://example.com/page", snippet="Organic content"),
            _make_result(url="https://example.com/page?utm_source=twitter", snippet="Twitter content"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_fbclid_ignored(self):
        dedup = Deduplicator()
        results = [
            _make_result(url="https://example.com/page", snippet="Clean content"),
            _make_result(url="https://example.com/page?fbclid=abc123", snippet="Facebook content"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_meaningful_query_params_kept(self):
        config = DedupConfig(max_per_domain=10, content_similarity_threshold=0.99)
        dedup = Deduplicator(config)
        results = [
            _make_result(url="https://example.com/search?q=python", snippet="Python search results page content"),
            _make_result(url="https://example.com/search?q=javascript", snippet="JavaScript search results page content"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 2

    def test_fragment_ignored(self):
        dedup = Deduplicator()
        results = [
            _make_result(url="https://example.com/page#section1", snippet="Section one content"),
            _make_result(url="https://example.com/page#section2", snippet="Section two content"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_multiple_utm_params(self):
        dedup = Deduplicator()
        results = [
            _make_result(url="https://example.com/page", snippet="Plain content"),
            _make_result(url="https://example.com/page?utm_source=tw&utm_medium=social", snippet="Campaign content"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_query_param_order_normalized(self):
        """Query params are sorted, so order doesn't matter."""
        dedup = Deduplicator()
        results = [
            _make_result(url="https://example.com/page?a=1&b=2", snippet="Ordered params content"),
            _make_result(url="https://example.com/page?b=2&a=1", snippet="Reversed params content"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_normalize_disabled(self):
        config = DedupConfig(normalize_urls=False)
        dedup = Deduplicator(config)
        results = [
            _make_result(url="https://EXAMPLE.COM/Page", snippet="Upper content here"),
            _make_result(url="https://example.com/page", snippet="Lower content here"),
        ]
        # Even with normalize=False, lower() is applied — so these are still equal
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1


# ── Domain limiting ──────────────────────────────────────────────────────────


class TestDomainLimiting:
    """Tests for per-domain result limits."""

    def test_max_per_domain_enforced(self):
        config = DedupConfig(max_per_domain=2)
        dedup = Deduplicator(config)
        results = [
            _make_result(url="https://example.com/page1", snippet="First page content"),
            _make_result(url="https://example.com/page2", snippet="Second page content"),
            _make_result(url="https://example.com/page3", snippet="Third page content"),
            _make_result(url="https://example.com/page4", snippet="Fourth page content"),
        ]
        deduped = dedup.deduplicate(results)
        example_count = sum(1 for r in deduped if "example.com" in r.url)
        assert example_count <= 2

    def test_different_domains_independent(self):
        config = DedupConfig(max_per_domain=2)
        dedup = Deduplicator(config)
        results = [
            _make_result(url="https://a.com/1", snippet="A one content"),
            _make_result(url="https://a.com/2", snippet="A two content"),
            _make_result(url="https://a.com/3", snippet="A three content"),
            _make_result(url="https://b.com/1", snippet="B one content"),
            _make_result(url="https://b.com/2", snippet="B two content"),
            _make_result(url="https://b.com/3", snippet="B three content"),
        ]
        deduped = dedup.deduplicate(results)
        a_count = sum(1 for r in deduped if "a.com" in r.url)
        b_count = sum(1 for r in deduped if "b.com" in r.url)
        assert a_count <= 2
        assert b_count <= 2

    def test_www_domain_grouped(self):
        config = DedupConfig(max_per_domain=2)
        dedup = Deduplicator(config)
        results = [
            _make_result(url="https://example.com/1", snippet="Without www content"),
            _make_result(url="https://www.example.com/2", snippet="With www content"),
            _make_result(url="https://example.com/3", snippet="Third page content"),
        ]
        deduped = dedup.deduplicate(results)
        # www is normalized, so these all share a domain
        example_count = sum(1 for r in deduped if "example.com" in r.url)
        assert example_count <= 2

    def test_first_results_preserved(self):
        config = DedupConfig(max_per_domain=1)
        dedup = Deduplicator(config)
        r1 = _make_result(url="https://example.com/first", title="First", snippet="First page content")
        r2 = _make_result(url="https://example.com/second", title="Second", snippet="Second page content")
        deduped = dedup.deduplicate([r1, r2])
        assert len(deduped) == 1
        assert deduped[0].title == "First"


# ── Content similarity deduplication ─────────────────────────────────────────


class TestContentSimilarity:
    """Tests for Jaccard-based content deduplication."""

    def test_identical_content_deduped(self):
        config = DedupConfig(max_per_domain=10, content_similarity_threshold=0.5)
        dedup = Deduplicator(config)
        results = [
            _make_result(
                title="Python Tutorial",
                url="https://python.org/tutorial",
                snippet="Learn Python programming with this comprehensive guide for beginners",
            ),
            _make_result(
                title="Python Tutorial",
                url="https://python.org/tutorial2",
                snippet="Learn Python programming with this comprehensive guide for beginners",
            ),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_similar_content_deduped(self):
        config = DedupConfig(max_per_domain=10, content_similarity_threshold=0.5)
        dedup = Deduplicator(config)
        results = [
            _make_result(
                title="Python Tutorial",
                url="https://python.org/tutorial",
                snippet="Learn Python programming with this comprehensive guide for beginners and advanced developers",
            ),
            _make_result(
                title="Python Tutorial Guide",
                url="https://python.org/tutorial2",
                snippet="Learn Python programming with this comprehensive guide for beginners and advanced developers",
            ),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_different_content_kept(self):
        config = DedupConfig(max_per_domain=10, content_similarity_threshold=0.5)
        dedup = Deduplicator(config)
        results = [
            _make_result(
                title="Python Tutorial",
                url="https://python.org/basics",
                snippet="Learn Python programming language fundamentals and syntax for beginners",
            ),
            _make_result(
                title="Rust Guide",
                url="https://rust-lang.org/ownership",
                snippet="Systems programming with Rust ownership model and borrow checker patterns",
            ),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 2

    def test_short_content_skipped(self):
        """Content below min_content_length is not similarity-deduped."""
        config = DedupConfig(
            max_per_domain=10,
            content_similarity_threshold=0.5,
            min_content_length=200,
        )
        dedup = Deduplicator(config)
        results = [
            _make_result(title="A", url="https://a.com/x", snippet="short"),
            _make_result(title="B", url="https://b.com/y", snippet="short"),
        ]
        deduped = dedup.deduplicate(results)
        # Both have short content, similarity returns 0.0 → kept
        assert len(deduped) == 2

    def test_high_threshold_keeps_more(self):
        config = DedupConfig(max_per_domain=10, content_similarity_threshold=0.95)
        dedup = Deduplicator(config)
        results = [
            _make_result(
                title="Python Web Development",
                url="https://python.org/django",
                snippet="Build web applications using Python Django framework with REST APIs and database integration",
            ),
            _make_result(
                title="Python Web Dev",
                url="https://python.org/flask",
                snippet="Build web applications using Python Django framework with REST APIs and templates rendering",
            ),
        ]
        deduped = dedup.deduplicate(results)
        # At 0.95 threshold, even similar content should be kept
        assert len(deduped) == 2

    def test_low_threshold_dedupes_more(self):
        config = DedupConfig(max_per_domain=10, content_similarity_threshold=0.1)
        dedup = Deduplicator(config)
        results = [
            _make_result(
                title="Python Tutorial",
                url="https://python.org/learn",
                snippet="Learn Python programming with examples tutorials exercises practice problems",
            ),
            _make_result(
                title="Python Guide",
                url="https://python.org/guide",
                snippet="Learn Python programming with examples tutorials exercises practice problems",
            ),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1


# ── Integration / pipeline ordering ──────────────────────────────────────────


class TestDeduplicationPipeline:
    """Tests for the full dedup pipeline (URL → domain → content)."""

    def test_empty_input(self):
        dedup = Deduplicator()
        assert dedup.deduplicate([]) == []

    def test_single_result(self):
        dedup = Deduplicator()
        results = [_make_result(url="https://example.com", snippet="Just one result")]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1
        assert deduped[0].url == "https://example.com"

    def test_pipeline_url_dedup_before_domain_limit(self):
        """URL dedup runs first, reducing count before domain limit check."""
        config = DedupConfig(max_per_domain=2)
        dedup = Deduplicator(config)
        results = [
            _make_result(url="https://example.com/1", snippet="First page content"),
            _make_result(url="https://example.com/1?utm_source=a", snippet="Campaign content"),
            _make_result(url="https://example.com/2", snippet="Second page content"),
            _make_result(url="https://example.com/3", snippet="Third page content"),
        ]
        deduped = dedup.deduplicate(results)
        example_count = sum(1 for r in deduped if "example.com" in r.url)
        assert example_count <= 2

    def test_preserves_first_occurrence(self):
        """First result is always kept; later duplicates are dropped."""
        dedup = Deduplicator()
        results = [
            _make_result(title="Original", url="https://example.com/page", snippet="Original content here"),
            _make_result(title="Duplicate", url="https://example.com/page", snippet="Duplicate content here"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1
        assert deduped[0].title == "Original"

    def test_mixed_domains_with_duplicates(self):
        config = DedupConfig(max_per_domain=3)
        results = [
            _make_result(url="https://docs.python.org/3/library", snippet="Python standard library reference"),
            _make_result(url="https://docs.python.org/3/library", snippet="Duplicate library reference"),
            _make_result(url="https://docs.python.org/3/tutorial", snippet="Python tutorial for beginners"),
            _make_result(url="https://docs.python.org/3/howto", snippet="Python how-to guides"),
            _make_result(url="https://docs.python.org/3/faq", snippet="Python frequently asked questions"),
            _make_result(url="https://realpython.com/basics", snippet="Real Python basics tutorial"),
            _make_result(url="https://realpython.com/basics?ref=home", snippet="Real Python basics ref"),
        ]
        dedup = Deduplicator(config)
        deduped = dedup.deduplicate(results)
        python_docs = sum(1 for r in deduped if "docs.python.org" in r.url)
        assert python_docs <= 3
        realpython = sum(1 for r in deduped if "realpython.com" in r.url)
        assert realpython <= 3


# ── get_duplicate_groups ─────────────────────────────────────────────────────


class TestGetDuplicateGroups:
    """Tests for the group-based duplicate detection API."""

    def test_no_duplicates(self):
        dedup = Deduplicator(DedupConfig(max_per_domain=10))
        results = [
            _make_result(title="A", url="https://a.com", snippet="Alpha beta gamma delta epsilon zeta eta"),
            _make_result(title="B", url="https://b.com", snippet="Zeta eta theta iota kappa lambda mu"),
        ]
        groups = dedup.get_duplicate_groups(results)
        assert len(groups) == 2
        assert all(len(g) == 1 for g in groups)

    def test_all_duplicates(self):
        dedup = Deduplicator(DedupConfig(max_per_domain=10))
        results = [
            _make_result(title="X", url="https://a.com", snippet="Alpha beta gamma delta epsilon zeta eta theta"),
            _make_result(title="Y", url="https://b.com", snippet="Alpha beta gamma delta epsilon zeta eta theta"),
        ]
        groups = dedup.get_duplicate_groups(results)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_empty_input(self):
        dedup = Deduplicator()
        groups = dedup.get_duplicate_groups([])
        assert groups == []

    def test_partial_duplicates(self):
        dedup = Deduplicator(DedupConfig(max_per_domain=10, content_similarity_threshold=0.5))
        results = [
            _make_result(
                title="Python",
                url="https://python.org/a",
                snippet="Python programming language tutorial guide for beginners and experts",
            ),
            _make_result(
                title="Python",
                url="https://python.org/b",
                snippet="Python programming language tutorial guide for beginners and experts",
            ),
            _make_result(
                title="Rust",
                url="https://rust-lang.org/a",
                snippet="Rust programming language systems ownership borrow checker patterns",
            ),
        ]
        groups = dedup.get_duplicate_groups(results)
        # Should have 2 groups: [Python x2], [Rust x1]
        assert len(groups) == 2
        python_group = [g for g in groups if len(g) > 1]
        assert len(python_group) == 1
        assert len(python_group[0]) == 2


# ── Edge cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge case tests for the deduplicator."""

    def test_invalid_url(self):
        """Invalid URLs should still be processed without crashing."""
        dedup = Deduplicator()
        results = [
            _make_result(url="not-a-url", snippet="First invalid URL content"),
            _make_result(url="also-not-a-url", snippet="Second invalid URL content"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) >= 1  # At minimum, dedup shouldn't crash

    def test_empty_url(self):
        dedup = Deduplicator()
        results = [
            _make_result(url="", snippet="Empty URL content one"),
            _make_result(url="", snippet="Empty URL content two"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_unicode_url(self):
        dedup = Deduplicator()
        results = [
            _make_result(url="https://example.com/日本語", snippet="Japanese content version one"),
            _make_result(url="https://example.com/日本語", snippet="Japanese content version two"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_very_long_url(self):
        dedup = Deduplicator()
        long_path = "/a" * 500
        results = [
            _make_result(url=f"https://example.com{long_path}", snippet="Long URL content one"),
            _make_result(url=f"https://example.com{long_path}", snippet="Long URL content two"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1

    def test_empty_snippet_and_title(self):
        """Content similarity with empty fields should not crash."""
        config = DedupConfig(max_per_domain=10)
        dedup = Deduplicator(config)
        results = [
            _make_result(title="", snippet="", url="https://a.com"),
            _make_result(title="", snippet="", url="https://b.com"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 2

    def test_custom_ignore_params(self):
        config = DedupConfig(ignore_query_params=["session_id"])
        dedup = Deduplicator(config)
        results = [
            _make_result(url="https://example.com/page", snippet="Clean page content"),
            _make_result(url="https://example.com/page?session_id=abc", snippet="Session page content"),
        ]
        deduped = dedup.deduplicate(results)
        assert len(deduped) == 1
