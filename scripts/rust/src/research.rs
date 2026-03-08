use clap::Parser;
use futures::future::join_all;
use reqwest::Client;
use std::time::Instant;
use dsearch::{score_and_rank, SearchResult};

#[derive(Parser)]
struct Args {
    #[arg(short, long)] topic: String,
    #[arg(short = 'n', long, default_value = "5")] top: usize,
    #[arg(long, default_value = "100")] max_kb: usize,
    #[arg(short, long)] output: Option<String>,
    #[arg(short, long)] urls: Option<Vec<String>>,
    #[arg(short = 'q', long = "query")] queries: Option<Vec<String>>,
    #[arg(long, default_value = "300")] timeout: usize,
    #[arg(short, long, default_value = "vectors", value_parser = ["vectors", "json", "md"])] mode: String,
}

#[tokio::main]
async fn main() -> Result<(), String> {
    let args = Args::parse();
    let start = Instant::now();
    println!("🔬 CCLL Autonomous Research Pipeline\n{}\nTopic: {}\n", "=".repeat(50), args.topic);

    let client = Client::builder().user_agent("Mozilla/5.0").timeout(std::time::Duration::from_secs(30)).build().map_err(|e| e.to_string())?;
    let queries = args.queries.clone().unwrap_or_else(|| vec![args.topic.clone()]);
    println!("[dsearch] topic   : {:?}", args.topic);
    println!("[dsearch] queries : {:?}", queries);
    println!("[dsearch] count   : {}", queries.len());
    
    let mut all_results = Vec::new();
    all_results.extend(run_gemini_phase(&client, &queries, &args.topic).await);
    all_results.extend(run_minimax_phase(&client, &queries, &args.topic).await);
    all_results.extend(run_kimi_phase(&client, &queries, &args.topic).await);
    // xAI disabled - uncomment to re-enable: all_results.extend(run_xai_phases(&queries, &args.topic).await);

    if let Some(urls) = &args.urls {
        for url in urls { all_results.push(SearchResult { title: format!("User: {}", url), url: url.clone(), snippet: "User URL".to_string() }); }
    }

    println!("  Found {} total results", all_results.len());
    match args.mode.as_str() {
        "json" => save_json(&all_results, &args.topic),
        "vectors" => save_vectors(&all_results, &args.topic),
        _ => run_md_report_phase(&client, all_results, &args).await?,
    }

    println!("\nResearch: {}\nTime: {:.1}s", args.topic, start.elapsed().as_secs_f64());
    Ok(())
}

async fn run_gemini_phase(client: &Client, queries: &[String], topic: &str) -> Vec<SearchResult> {
    if dsearch::get_secret("gemini").is_err() { return Vec::new(); }
    println!("\nPhase: Gemini ({} queries)...", queries.len());
    for (i, q) in queries.iter().enumerate() {
        println!("[gemini] query {}: {:?}", i + 1, q);
    }
    let mut results = Vec::new();
    let futs: Vec<_> = queries.iter().map(|q| { let c = client; let q = q.clone(); async move { dsearch::search_gemini(c, &q, 10).await } }).collect();
    for res in join_all(futs).await { if let Ok(list) = res { results.extend(list); } }
    for r in &results { push_zvec(r, topic); }
    println!("  Gemini found {} results", results.len());
    results
}

async fn run_minimax_phase(client: &Client, queries: &[String], topic: &str) -> Vec<SearchResult> {
    if dsearch::get_secret("minimax").is_err() { return Vec::new(); }
    println!("\nPhase: MiniMax ({} queries)...", queries.len());
    for (i, q) in queries.iter().enumerate() {
        println!("[minimax] query {}: {:?}", i + 1, q);
    }
    let mut results = Vec::new();
    let futs: Vec<_> = queries.iter().map(|q| { let c = client; let q = q.clone(); async move { dsearch::search_minimax(c, &q, 10).await } }).collect();
    for res in join_all(futs).await { if let Ok(list) = res { results.extend(list); } }
    for r in &results { push_zvec(r, topic); }
    println!("  MiniMax found {} results", results.len());
    results
}

async fn run_kimi_phase(client: &Client, queries: &[String], topic: &str) -> Vec<SearchResult> {
    if dsearch::get_secret("kimi").is_err() { return Vec::new(); }
    println!("\nPhase: Kimi ({} queries)...", queries.len());
    for (i, q) in queries.iter().enumerate() {
        println!("[kimi] query {}: {:?}", i + 1, q);
    }
    let mut results = Vec::new();
    let futs: Vec<_> = queries.iter().map(|q| { let c = client; let q = q.clone(); async move { dsearch::search_kimi(c, &q, 10).await } }).collect();
    for res in join_all(futs).await { if let Ok(list) = res { results.extend(list); } }
    for r in &results { push_zvec(r, topic); }
    println!("  Kimi found {} results", results.len());
    results
}

async fn run_xai_phases(queries: &[String], topic: &str) -> Vec<SearchResult> {
    if dsearch::get_secret("xai").is_err() { return Vec::new(); }
    let mut all = Vec::new();
    println!("\nPhase: xAI Web ({} queries)...", queries.len());
    for (i, q) in queries.iter().enumerate() {
        println!("[xai] query {}: {:?}", i + 1, q);
    }
    let futs: Vec<_> = queries.iter().map(|q| { let q = q.clone(); async move { dsearch::search_xai(&q, 10).await } }).collect();
    for res in join_all(futs).await { if let Ok(list) = res { all.extend(list); } }
    println!("\nPhase: xAI X ({} queries)...", queries.len());
    let futs: Vec<_> = queries.iter().map(|q| { let q = q.clone(); async move { dsearch::xai_x_search(&q, 10).await } }).collect();
    for res in join_all(futs).await { if let Ok(list) = res { all.extend(list); } }
    for r in &all { push_zvec(r, topic); }
    println!("  xAI found {} results", all.len());
    all
}

fn push_zvec(r: &SearchResult, topic: &str) {
    let _ = std::process::Command::new("python3").args(&["push_zvec.py", &r.title, &r.url, &r.snippet, topic]).spawn();
}

fn save_json(results: &[SearchResult], topic: &str) {
    let file = format!("{}_raw.json", topic.replace(" ", "_"));
    std::fs::write(&file, serde_json::to_string_pretty(results).unwrap_or_default()).ok();
    println!("  ✓ Saved to: {}", file);
}

fn save_vectors(results: &[SearchResult], topic: &str) {
    let file = format!("{}_index.json", topic.replace(" ", "_"));
    let index: Vec<_> = results.iter().map(|r| serde_json::json!({"title": r.title, "url": r.url})).collect();
    std::fs::write(&file, serde_json::to_string_pretty(&index).unwrap()).ok();
    println!("  ✓ Index saved to: {}", file);
}

async fn run_md_report_phase(client: &Client, results: Vec<SearchResult>, args: &Args) -> Result<(), String> {
    save_json(&results, &args.topic);
    let scored = score_and_rank(results, args.top, &args.topic.split_whitespace().map(|s| s.to_string()).collect::<Vec<_>>());
    let file = format!("{}_fetched.md", args.topic.replace(" ", "_"));
    std::fs::write(&file, format!("# Research: {}\n\n", args.topic)).ok();
    for (i, s) in scored.iter().enumerate() {
        let page = match dsearch::fetch_url(client, &s.result.url, args.max_kb).await {
            Ok(p) => p,
            Err(_) => dsearch::FetchedPage {
                url: s.result.url.clone(), title: s.result.title.clone(), markdown: "Fetch failed".into(), byte_size: 0,
            },
        };
        let content = format!("\n\n## Source {}: {}\n**URL:** {}\n\n{}\n", i + 1, page.title, page.url, page.markdown);
        let mut f = std::fs::OpenOptions::new().append(true).open(&file).map_err(|e| e.to_string())?;
        use std::io::Write; f.write_all(content.as_bytes()).map_err(|e| e.to_string())?;
        println!("  ✓ Fetched: {}", page.title.chars().take(50).collect::<String>());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse(args: &[&str]) -> Result<Args, clap::Error> {
        Args::try_parse_from(std::iter::once("research").chain(args.iter().copied()))
    }

    // --- Topic parsing ---

    #[test]
    fn test_topic_received_verbatim() {
        let args = parse(&["--topic", "kube-scheduler MIG GPU bin-packing"]).unwrap();
        println!("[test] topic parsed: {:?}", args.topic);
        assert_eq!(args.topic, "kube-scheduler MIG GPU bin-packing");
    }

    #[test]
    fn test_topic_dense_keyword_string_unchanged() {
        let topic = "MoE routing Top-k expert-choice DeepSeek-V3 expert parallelism";
        let args = parse(&["--topic", topic]).unwrap();
        println!("[test] topic parsed: {:?}", args.topic);
        assert_eq!(args.topic, topic);
    }

    #[test]
    fn test_topic_becomes_single_query() {
        let args = parse(&["--topic", "Rust async runtime Tokio work-stealing"]).unwrap();
        let queries = vec![args.topic.clone()];
        println!("[test] queries vec: {:?}", queries);
        assert_eq!(queries.len(), 1);
        assert_eq!(queries[0], "Rust async runtime Tokio work-stealing");
    }

    #[test]
    fn test_dsearch_scope_query() {
        // Real scope from 3-round clarification:
        //   Round 1: async runtime design + production LLM serving patterns
        //   Round 2: Tokio vs Rayon, dynamic batching strategies
        //   Round 3 Q2: dynamic batching patterns for GPU utilization without sacrificing latency
        //   Round 3 Q3: Rayon work-stealing vs spawn_blocking for CPU-bound matrix ops 2026
        let query = "Tokio Rayon inference dynamic batching GPU utilization latency spawn_blocking work-stealing CPU-bound matrix ops 2026 Rust LLM";
        let args = parse(&["--topic", query, "--top", "8", "--mode", "md"]).unwrap();
        println!("[test] topic  : {:?}", args.topic);
        println!("[test] top    : {}", args.top);
        println!("[test] mode   : {:?}", args.mode);
        let queries = vec![args.topic.clone()];
        println!("[test] queries: {:?}", queries);
        assert_eq!(args.topic, query);
        assert_eq!(args.top, 8);
        assert_eq!(args.mode, "md");
        // single query vec — no expansion
        assert_eq!(queries.len(), 1);
        assert_eq!(queries[0], query);
    }

    #[test]
    fn test_missing_topic_fails() {
        assert!(parse(&["--mode", "md"]).is_err());
    }

    // --- Default values ---

    #[test]
    fn test_defaults() {
        let args = parse(&["--topic", "anything"]).unwrap();
        assert_eq!(args.top, 5);
        assert_eq!(args.timeout, 300);
        assert_eq!(args.mode, "vectors");
        assert_eq!(args.max_kb, 100);
        assert!(args.output.is_none());
        assert!(args.urls.is_none());
    }

    // --- Flag overrides ---

    #[test]
    fn test_top_override() {
        let args = parse(&["--topic", "anything", "--top", "10"]).unwrap();
        assert_eq!(args.top, 10);
    }

    #[test]
    fn test_mode_md() {
        let args = parse(&["--topic", "anything", "--mode", "md"]).unwrap();
        assert_eq!(args.mode, "md");
    }

    #[test]
    fn test_mode_json() {
        let args = parse(&["--topic", "anything", "--mode", "json"]).unwrap();
        assert_eq!(args.mode, "json");
    }

    #[test]
    fn test_invalid_mode_rejected() {
        assert!(parse(&["--topic", "anything", "--mode", "xml"]).is_err());
    }

    #[test]
    fn test_urls_parsed() {
        let args = parse(&["--topic", "anything", "--urls", "https://tokio.rs", "--urls", "https://docs.rs"]).unwrap();
        let urls = args.urls.unwrap();
        assert_eq!(urls.len(), 2);
        assert!(urls.contains(&"https://tokio.rs".to_string()));
    }

    // --- Multi-query design (new) ---

    #[test]
    fn test_multiple_queries_parsed() {
        let args = parse(&[
            "--topic", "Rust parallel LLM 2026",
            "--query", "Tokio vs Rayon LLM inference Rust 2026",
            "--query", "dynamic batching GPU utilization Rust LLM serving latency",
            "--query", "Rayon work-stealing spawn_blocking CPU matrix ops Rust",
        ]).unwrap();
        let queries = args.queries.unwrap();
        println!("[test] queries ({}):", queries.len());
        for q in &queries { println!("  → {:?}", q); }
        assert_eq!(queries.len(), 3);
        assert!(queries.contains(&"Tokio vs Rayon LLM inference Rust 2026".to_string()));
        assert!(queries.contains(&"dynamic batching GPU utilization Rust LLM serving latency".to_string()));
    }

    #[test]
    fn test_topic_separate_from_queries() {
        let args = parse(&[
            "--topic", "Rust parallel LLM 2026",
            "--query", "Tokio vs Rayon LLM inference Rust 2026",
        ]).unwrap();
        println!("[test] topic  : {:?}", args.topic);
        println!("[test] queries: {:?}", args.queries);
        assert_eq!(args.topic, "Rust parallel LLM 2026");
        let queries = args.queries.unwrap();
        assert!(!queries.contains(&"Rust parallel LLM 2026".to_string()));
    }

    #[test]
    fn test_queries_vec_has_all_focused_queries() {
        // Real session scope from 3-round clarification
        let args = parse(&[
            "--topic", "Rust parallel LLM 2026",
            "--query", "Tokio vs Rayon LLM inference Rust 2026",
            "--query", "dynamic batching GPU utilization Rust LLM serving latency",
            "--query", "Rayon work-stealing spawn_blocking CPU matrix ops Rust",
            "--top", "8",
            "--mode", "md",
        ]).unwrap();
        let queries = args.queries.unwrap();
        println!("[test] topic  : {:?}", args.topic);
        println!("[test] top    : {}", args.top);
        println!("[test] mode   : {:?}", args.mode);
        println!("[test] queries ({}):", queries.len());
        for q in &queries { println!("  → {:?}", q); }
        assert_eq!(queries.len(), 3);
        assert_eq!(args.top, 8);
        assert_eq!(args.mode, "md");
    }
}
