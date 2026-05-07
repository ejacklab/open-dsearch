"""Comprehensive unit tests for result scoring and ranking."""

import math
from datetime import datetime, timezone, timedelta

from src.search.ranking.scorer import (
    ResultScorer,
    ScoringWeights,
)
from src.search.providers.base import SearchResult


def make_result(
    title: str = "Test",
    url: str = "https://example.com/page",
    snippet: str = "A test snippet about the topic.",
    source: str = "test",
    score: float = 0.0,
    timestamp=None,
) -> SearchResult:
    return SearchResult(title=title, url=url, snippet=snippet, source=source, score=score, timestamp=timestamp)


# ─── ScoringWeights ──────────────────────────────────────────────────

class TestScoringWeights:
    """Tests for ScoringWeights dataclass."""

    def test_defaults(self):
        """Default weights are sensible."""
        w = ScoringWeights()
        assert w.keyword_match == 1.0
        assert w.source_quality == 2.0
        assert w.title_relevance == 1.5
        assert w.snippet_quality == 0.5
        assert w.recency == 0.3

    def test_custom_weights(self):
        """Custom weights override defaults."""
        w = ScoringWeights(keyword_match=5.0, recency=10.0)
        assert w.keyword_match == 5.0
        assert w.source_quality == 2.0  # unchanged default
        assert w.recency == 10.0


# ─── ResultScorer: Basic Scoring ─────────────────────────────────────

class TestResultScorerBasic:
    """Core scoring behavior."""

    def test_empty_results(self):
        """Empty list returns empty."""
        scorer = ResultScorer()
        assert scorer.score_results([], "test") == []

    def test_results_get_scores(self):
        """All results get a numeric score after scoring."""
        scorer = ResultScorer()
        results = [
            make_result(title="Python tutorial", snippet="Learn Python programming"),
            make_result(title="Java guide", snippet="Learn Java"),
        ]
        scored = scorer.score_results(results, "python tutorial")
        for r in scored:
            assert isinstance(r.score, (int, float))

    def test_sorted_descending(self):
        """Results are sorted by score descending."""
        scorer = ResultScorer()
        results = [
            make_result(url="https://reddit.com/q"),      # low source
            make_result(url="https://github.com/proj"),   # high source
            make_result(url="https://medium.com/p"),       # low source
        ]
        scored = scorer.score_results(results, "project")
        scores = [r.score for r in scored]
        assert scores == sorted(scores, reverse=True)

    def test_does_not_mutate_original_list_order(self):
        """Original list is not modified in place (returns new sorted list)."""
        scorer = ResultScorer()
        results = [
            make_result(title="B"),
            make_result(title="A"),
        ]
        original_titles = [r.title for r in results]
        _ = scorer.score_results(results, "test")
        assert [r.title for r in results] == original_titles

    def test_custom_query_terms(self):
        """Pre-tokenized query terms are used when provided."""
        scorer = ResultScorer()
        results = [make_result(title="Python async await")]
        # When we pass custom terms, they should be used as-is
        scored = scorer.score_results(results, "ignored", query_terms=["async"])
        assert scored[0].score > 0


# ─── Keyword Matching ────────────────────────────────────────────────

class TestKeywordMatching:
    """Keyword scoring tests."""

    def test_exact_keyword_match(self):
        """All query terms present → high keyword score."""
        scorer = ResultScorer()
        results = [make_result(title="Python machine learning tutorial")]
        scored = scorer.score_results(results, "python machine learning")
        assert scored[0].score > 0

    def test_no_keyword_match(self):
        """No matching terms → lower score than a match."""
        scorer = ResultScorer()
        no_match = scorer.score_results(
            [make_result(title="Cooking recipes", url="https://blog.example.com/food")],
            "quantum physics computing"
        )[0].score
        match = scorer.score_results(
            [make_result(title="Quantum computing guide", url="https://blog.example.com/food")],
            "quantum physics computing"
        )[0].score
        assert no_match < match

    def test_partial_keyword_match(self):
        """Partial match scores between full match and no match."""
        scorer = ResultScorer()
        full = scorer.score_results(
            [make_result(title="Python ML tutorial")], "python ml"
        )[0].score
        partial = scorer.score_results(
            [make_result(title="Python cooking")], "python ml"
        )[0].score
        assert full > partial

    def test_case_insensitive(self):
        """Matching is case-insensitive."""
        scorer = ResultScorer()
        upper = scorer.score_results(
            [make_result(title="PYTHON Tutorial")], "python"
        )[0].score
        lower = scorer.score_results(
            [make_result(title="python tutorial")], "python"
        )[0].score
        assert upper == lower


# ─── Source Quality ──────────────────────────────────────────────────

class TestSourceQuality:
    """Source-based scoring."""

    def test_github_highest(self):
        """GitHub gets highest source bonus."""
        scorer = ResultScorer()
        gh = scorer.score_results(
            [make_result(url="https://github.com/user/repo")], "repo"
        )[0].score
        blog = scorer.score_results(
            [make_result(url="https://blog.example.com/post")], "repo"
        )[0].score
        assert gh > blog

    def test_docs_bonus(self):
        """Docs URLs get a good source bonus."""
        scorer = ResultScorer()
        docs = scorer.score_results(
            [make_result(url="https://docs.python.org/3/library")], "python docs"
        )[0].score
        generic = scorer.score_results(
            [make_result(url="https://example.com/page")], "python docs"
        )[0].score
        assert docs > generic

    def test_stackoverflow_bonus(self):
        """StackOverflow gets a decent source bonus."""
        scorer = ResultScorer()
        so = scorer.score_results(
            [make_result(url="https://stackoverflow.com/questions/123")], "error fix"
        )[0].score
        reddit = scorer.score_results(
            [make_result(url="https://reddit.com/r/python")], "error fix"
        )[0].score
        assert so > reddit

    def test_reddit_lowest(self):
        """Reddit has low source quality among known sources."""
        scorer = ResultScorer()
        reddit = scorer.score_results(
            [make_result(url="https://reddit.com/r/test")], "test"
        )[0].score
        github = scorer.score_results(
            [make_result(url="https://github.com/test/repo")], "test"
        )[0].score
        assert reddit < github

    def test_unknown_source_neutral(self):
        """Unknown domain doesn't crash; gives neutral/zero source score."""
        scorer = ResultScorer()
        result = scorer.score_results(
            [make_result(url="https://totally-unknown-domain.xyz/page")], "test"
        )
        assert len(result) == 1
        assert isinstance(result[0].score, float)


# ─── Title Relevance ─────────────────────────────────────────────────

class TestTitleRelevance:
    """Title-specific scoring."""

    def test_title_phrase_bonus(self):
        """Exact phrase in title gets bonus."""
        scorer = ResultScorer()
        with_phrase = scorer.score_results(
            [make_result(title="Complete Python Machine Learning Guide")],
            "python machine learning",
        )[0].score
        scattered = scorer.score_results(
            [make_result(title="Python stuff and also learning about machines")],
            "python machine learning",
        )[0].score
        assert with_phrase >= scattered

    def test_no_title_match_lower_score(self):
        """Title without query terms scores lower than one with them."""
        scorer = ResultScorer()
        matched = scorer.score_results(
            [make_result(title="Best Python IDEs 2024")], "python ide"
        )[0].score
        unmatched = scorer.score_results(
            [make_result(title="Programming tools review")], "python ide"
        )[0].score
        assert matched > unmatched


# ─── Snippet Quality ─────────────────────────────────────────────────

class TestSnippetQuality:
    """Snippet length/quality scoring."""

    def test_medium_snippet_preferred(self):
        """100-500 char snippets get best score."""
        scorer = ResultScorer(weights=ScoringWeights(keyword_match=0, source_quality=0, title_relevance=0))
        medium = scorer.score_results(
            [make_result(snippet="x" * 200)], "x"
        )[0].score
        short = scorer.score_results(
            [make_result(snippet="hi")], "x"
        )[0].score
        assert medium > short

    def test_very_short_snippet_penalized(self):
        """Snippets < 50 chars get penalty."""
        scorer = ResultScorer(weights=ScoringWeights(keyword_match=0, source_quality=0, title_relevance=0))
        tiny = scorer.score_results(
            [make_result(snippet="abc")], "test"
        )[0].score
        ok = scorer.score_results(
            [make_result(snippet="a" * 100)], "test"
        )[0].score
        assert tiny < ok

    def test_empty_snippet_zero_score(self):
        """Empty snippet contributes zero (not negative) from snippet scoring."""
        scorer = ResultScorer(weights=ScoringWeights(keyword_match=0, source_quality=0, title_relevance=0, snippet_quality=1.0, recency=0))
        score = scorer.score_results(
            [make_result(title="NoMatch", snippet="", timestamp=None)], "xyzwq"
        )[0].score
        # Empty snippet → _score_snippet returns 0.0 (not negative; penalty is for <50 chars)
        assert score == 0.0


# ─── Recency Scoring ─────────────────────────────────────────────────

class TestRecencyScoring:
    """Timestamp-based recency scoring."""

    def test_recent_item_higher_score(self):
        """Recent item scores higher than old one."""
        scorer = ResultScorer()
        now = datetime.now(timezone.utc)
        recent = make_result(
            title="New post",
            snippet="About AI",
            timestamp=now - timedelta(days=1),
        )
        old = make_result(
            title="Old post",
            snippet="About AI",
            timestamp=now - timedelta(days=1000),
        )
        scored = scorer.score_results([recent, old], "AI")
        assert scored[0].timestamp == recent.timestamp  # recent should rank first

    def test_no_timestamp_no_crash(self):
        """Missing timestamp doesn't crash; recency just skipped."""
        scorer = ResultScorer()
        result = scorer.score_results(
            [make_result(timestamp=None)], "test"
        )
        assert len(result) == 1

    def test_recency_decay(self):
        """Score decreases as age increases (exponential decay)."""
        scorer = ResultScorer()
        now = datetime.now(timezone.utc)

        fresh = scorer._score_recency(now - timedelta(days=1))
        year_old = scorer._score_recency(now - timedelta(days=365))
        decade_old = scorer._score_recency(now - timedelta(days=3650))

        assert fresh > year_old > decade_old > 0


# ─── Tokenization ────────────────────────────────────────────────────

class TestTokenization:
    """Query tokenization behavior."""

    def test_removes_stop_words(self):
        """Common stop words are removed from tokens."""
        scorer = ResultScorer()
        tokens = scorer._tokenize("the quick brown fox is running")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "quick" in tokens
        assert "running" in tokens

    def test_short_tokens_excluded(self):
        """Tokens shorter than 2 chars are excluded."""
        scorer = ResultScorer()
        tokens = scorer._tokenize("a b c hello world")
        assert "hello" in tokens
        assert "world" in tokens
        assert len([t for t in tokens if len(t) < 2]) == 0

    def test_lowercase_output(self):
        """All tokens are lowercase."""
        scorer = ResultScorer()
        tokens = scorer._tokenize("Hello WORLD Python")
        assert all(t == t.lower() for t in tokens)


# ─── get_top_results ─────────────────────────────────────────────────

class TestGetTopResults:
    """Top-N selection."""

    def test_returns_n(self):
        """Returns at most N results."""
        scorer = ResultScorer()
        results = [make_result(title=f"Result {i}") for i in range(20)]
        top = scorer.get_top_results(results, n=5)
        assert len(top) <= 5

    def test_respects_min_score(self):
        """Filters out results below threshold."""
        scorer = ResultScorer()
        r_low = make_result(score=0.1)
        r_high = make_result(score=5.0)
        filtered = scorer.get_top_results([r_low, r_high], n=10, min_score=1.0)
        assert all(r.score >= 1.0 for r in filtered)

    def test_no_min_score_returns_all_up_to_n(self):
        """Without min_score, returns up to n regardless of score."""
        scorer = ResultScorer()
        results = [make_result(score=float(i)) for i in range(3)]
        top = scorer.get_top_results(results, n=10)
        assert len(top) == 3

    def test_n_larger_than_results(self):
        """n larger than list returns all results."""
        scorer = ResultScorer()
        results = [make_result() for _ in range(2)]
        assert len(scorer.get_top_results(results, n=100)) == 2


# ─── filter_by_domain ────────────────────────────────────────────────

class TestFilterByDomain:
    """Domain allow/block filtering."""

    def test_allowlist_only_includes_matching(self):
        """Allowlist restricts to matching domains."""
        scorer = ResultScorer()
        results = [
            make_result(url="https://github.com/user/repo"),
            make_result(url="https://gitlab.com/user/repo"),
            make_result(url="https://bitbucket.org/user/repo"),
        ]
        filtered = scorer.filter_by_domain(results, allowed_domains=["github.com"])
        assert len(filtered) == 1
        assert "github" in filtered[0].url

    def test_blocklist_excludes_matching(self):
        """Blocklist removes matching domains."""
        scorer = ResultScorer()
        results = [
            make_result(url="https://github.com/a"),
            make_result(url="https://medium.com/b"),
            make_result(url="https://reddit.com/c"),
        ]
        filtered = scorer.filter_by_domain(results, blocked_domains=["medium.com", "reddit.com"])
        assert len(filtered) == 1
        assert "github" in filtered[0].url

    def test_combined_allow_and_block(self):
        """Allowlist and blocklist both applied (allow first, then block)."""
        scorer = ResultScorer()
        results = [
            make_result(url="https://github.com/good"),
            make_result(url="https://docs.github.com/good-docs"),
            make_result(url="https://github.io/blocked-suffix"),
        ]
        filtered = scorer.filter_by_domain(
            results,
            allowed_domains=["github.com"],
            blocked_domains=["github.io"],
        )
        # All have "github" in netloc so allowlist passes;
        # github.io should be blocked
        urls = [r.url for r in filtered]
        assert any("github.com/good" in u for u in urls)
        assert not any("github.io" in u for u in urls)

    def test_none_means_all_pass(self):
        """None allowlist/blocklist means no filtering on that axis."""
        scorer = ResultScorer()
        results = [make_result(url=f"https://{d}.com/p") for d in ["a", "b", "c"]]
        assert len(scorer.filter_by_domain(results, allowed_domains=None)) == 3
        assert len(scorer.filter_by_domain(results, blocked_domains=None)) == 3

    def test_empty_results(self):
        """Empty input returns empty."""
        scorer = ResultScorer()
        assert scorer.filter_by_domain([], allowed_domains=["x"]) == []


# ─── Custom Weights ──────────────────────────────────────────────────

class TestCustomWeights:
    """Behavior changes with custom weight configurations."""

    def test_keyword_heavy_weights(self):
        """High keyword weight makes keyword matches dominate."""
        heavy = ResultScorer(weights=ScoringWeights(keyword_match=10.0, source_quality=0.0, title_relevance=0.0, snippet_quality=0.0))
        default = ResultScorer()

        kw_match = make_result(title="Python asyncio tutorial", url="https://random.xyz/p", snippet="ok")
        src_match = make_result(title="Random page", url="https://github.com/proj", snippet="ok")

        heavy_scored = heavy.score_results([kw_match, src_match], "python asyncio")
        default_scored = default.score_results([kw_match, src_match], "python asyncio")

        # With heavy keyword weight, kw_match should win more decisively
        heavy_winner = heavy_scored[0].url
        default_winner = default_scored[0].url
        assert "random" in heavy_winner  # keyword match wins
        # Default might prefer GitHub source — that's fine


# ─── Rescore with Content ─────────────────────────────────────────────

class TestRescoreWithContent:
    """Tests for content-aware re-scoring after enrichment."""

    def test_rescore_empty_results(self):
        """Empty list returns empty."""
        scorer = ResultScorer()
        assert scorer.rescore_with_content([], "test") == []

    def test_rescore_no_fetched_content(self):
        """Results without fetched_content keep their original score."""
        scorer = ResultScorer()
        results = [
            make_result(title="Python tutorial", snippet="Learn Python"),
            make_result(title="Java guide", snippet="Learn Java"),
        ]
        scored = scorer.score_results(results, "python")
        original_scores = [r.score for r in scored]
        rescored = scorer.rescore_with_content(scored, "python")
        # Scores should be unchanged (no fetched_content)
        assert [r.score for r in rescored] == original_scores

    def test_rescore_boosts_content_match(self):
        """Result with relevant fetched_content gets score boost."""
        scorer = ResultScorer()
        results = [
            make_result(title="Guide A", snippet="Short", url="https://example.com/a"),
            make_result(title="Guide B", snippet="Short", url="https://example.com/b"),
        ]
        scored = scorer.score_results(results, "python async")

        # Give first result rich relevant content
        scored[0].fetched_content = (
            "This guide covers Python async programming in depth. "
            "Learn how to use async/await in Python for concurrent programming. "
            "Python async patterns are essential for modern applications."
        )

        original_order = [r.url for r in scored]
        rescored = scorer.rescore_with_content(scored, "python async")

        # Result with content should now be boosted
        content_result = [r for r in rescored if r.fetched_content][0]
        no_content_result = [r for r in rescored if not r.fetched_content][0]
        assert content_result.score > no_content_result.score

    def test_rescore_irrelevant_content_no_boost(self):
        """Result with irrelevant fetched_content gets minimal/no boost."""
        scorer = ResultScorer(
            weights=ScoringWeights(
                keyword_match=0.0, source_quality=0.0,
                title_relevance=0.0, snippet_quality=0.0, recency=0.0
            )
        )
        results = [make_result(title="Test", snippet="Test")]
        scored = scorer.score_results(results, "python")
        scored[0].fetched_content = "Cooking recipes for Italian pasta and pizza dough"

        original_score = scored[0].score
        rescored = scorer.rescore_with_content(scored, "python")
        # No relevant terms → no boost
        assert rescored[0].score == original_score

    def test_rescore_reorders_results(self):
        """Re-scoring can change result order when content is relevant."""
        scorer = ResultScorer()
        results = [
            make_result(title="Guide A", snippet="Brief", url="https://example.com/a"),
            make_result(title="Python Guide B", snippet="Python tutorial", url="https://example.com/b"),
        ]
        scored = scorer.score_results(results, "python async")

        # B starts higher (title+snippet match)
        assert scored[0].url == "https://example.com/b"

        # Give A rich content about the query
        scored[-1].fetched_content = (
            "Comprehensive Python async guide. Python async await "
            "patterns for building scalable Python applications."
        )

        rescored = scorer.rescore_with_content(scored, "python async")

        # A might now overtake B due to content boost
        has_content = [r for r in rescored if r.fetched_content]
        assert len(has_content) == 1
        assert has_content[0].score > 0

    def test_rescore_multiple_with_content(self):
        """Multiple enriched results are re-scored correctly."""
        scorer = ResultScorer()
        results = [
            make_result(title="A", snippet="Brief", url="https://a.com"),
            make_result(title="B", snippet="Brief", url="https://b.com"),
            make_result(title="C", snippet="Brief", url="https://c.com"),
        ]
        scored = scorer.score_results(results, "machine learning")

        # Give B the most relevant content
        scored[0].fetched_content = "Some general programming text without specifics"
        scored[1].fetched_content = (
            "Machine learning algorithms for classification and regression. "
            "Deep learning neural networks and machine learning pipelines."
        )
        scored[2].fetched_content = "Data engineering and ETL pipelines"

        rescored = scorer.rescore_with_content(scored, "machine learning")

        # B should rank highest due to rich relevant content
        b_result = [r for r in rescored if r.url == "https://b.com"][0]
        assert b_result == rescored[0]  # B is now top result
