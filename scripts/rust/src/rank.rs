use crate::search::SearchResult;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SourceType {
    OfficialDocs,
    EngineeringBlog,
    GitHub,
    AcademicPaper,
    Forum,
    Other,
}

impl SourceType {
    pub fn as_str(&self) -> &'static str {
        match self {
            SourceType::OfficialDocs => "Docs",
            SourceType::EngineeringBlog => "Blog",
            SourceType::GitHub => "GitHub",
            SourceType::AcademicPaper => "Paper",
            SourceType::Forum => "Forum",
            SourceType::Other => "Other",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoredResult {
    pub result: SearchResult,
    pub score: u32,
    pub source_type: SourceType,
}

pub fn score_and_rank(
    results: Vec<SearchResult>,
    top_n: usize,
    query_terms: &[String],
) -> Vec<ScoredResult> {
    // Filter out blocked domains
    let blocked_domains = ["reddit.com", "twitter.com", "x.com", "medium.com"];

    let mut scored: Vec<ScoredResult> = results
        .into_iter()
        .filter(|r| {
            let url_lower = r.url.to_lowercase();
            !blocked_domains.iter().any(|d| url_lower.contains(d))
        })
        .map(|r| {
            let (score, source_type) = score_url(&r.url, &r.snippet, query_terms);
            ScoredResult {
                result: r,
                score,
                source_type,
            }
        })
        .collect();

    scored.sort_by(|a, b| b.score.cmp(&a.score));

    let mut deduplicated: Vec<ScoredResult> = Vec::new();
    let mut seen_domains: HashMap<String, u32> = HashMap::new();

    for item in scored {
        if let Some(host) = url::Url::parse(&item.result.url)
            .ok()
            .and_then(|u| u.host_str().map(String::from))
        {
            let entry = seen_domains.entry(host.clone()).or_insert(0);
            if *entry < 3 {
                *entry += 1;
                deduplicated.push(item);
            }
        } else {
            deduplicated.push(item);
        }
    }

    deduplicated.truncate(top_n);
    deduplicated
}

fn score_url(url: &str, snippet: &str, query_terms: &[String]) -> (u32, SourceType) {
    let url_lower = url.to_lowercase();
    let snippet_lower = snippet.to_lowercase();

    let mut score = 0u32;
    let source_type = classify_url(&url_lower);

    score += match source_type {
        SourceType::OfficialDocs => 10,
        SourceType::EngineeringBlog => 8,
        SourceType::GitHub => 7,
        SourceType::AcademicPaper => 6,
        SourceType::Forum => 4,
        SourceType::Other => 2,
    };

    for term in query_terms {
        let term_lower = term.to_lowercase();
        if snippet_lower.contains(&term_lower) {
            score += 2;
        }
    }

    if url_lower.matches('/').count() < 4 {
        score += 1;
    }

    (score, source_type)
}

fn classify_url(url: &str) -> SourceType {
    if url.contains("docs.")
        || url.contains("documentation")
        || url.contains("developers.")
        || url.ends_with(".dev")
        || url.contains("developer.mozilla")
        || url.contains("learn.microsoft")
        || url.contains("cloud.google.com/docs")
        || url.contains("aws.amazon.com/documentation")
    {
        SourceType::OfficialDocs
    } else if url.contains("engineering.")
        || url.contains("/blog/")
        || url.contains("engineering blog")
        || url.contains("techblog")
        || url.contains("engineering.stripe")
        || url.contains("engineering.linkedin")
        || url.contains("engineering.fb")
        || url.contains("cloud.google.com/blog")
        || url.contains("aws.amazon.com/blogs")
    {
        SourceType::EngineeringBlog
    } else if url.contains("github.com/") && !url.contains("issues") && !url.contains("pull") {
        SourceType::GitHub
    } else if url.contains("arxiv.org")
        || url.contains(".edu/")
        || url.contains("ac.uk/")
        || url.contains("research.")
        || url.contains("papers.")
    {
        SourceType::AcademicPaper
    } else if url.contains("stackoverflow.com")
        || url.contains("stackexchange.com")
        || url.contains("reddit.com/r/")
        || url.contains("forum.")
    {
        SourceType::Forum
    } else {
        SourceType::Other
    }
}
