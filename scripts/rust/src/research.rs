use chrono::Local;
use clap::Parser;
use futures::future::join_all;
use reqwest::Client;
use std::time::Instant;

use dsearch::{
    expand_queries, expand_queries_with_sources, fetch_url, score_and_rank, SearchResult,
};

#[derive(Parser)]
#[command(name = "research")]
#[command(about = "Autonomous research pipeline - search, fetch, and synthesize in one command")]
struct Args {
    #[arg(short, long)]
    topic: String,

    #[arg(short, long, default_value = "5")]
    queries: usize,

    #[arg(short, long, default_value = "5")]
    top: usize,

    #[arg(long, default_value = "100")]
    max_kb: usize,

    #[arg(short, long)]
    output: Option<String>,

    #[arg(short, long)]
    urls: Option<Vec<String>>,
    
    // Source-specific search flags
    #[arg(long, default_value = "8")]
    google: usize,
    
    #[arg(long, default_value = "6")]
    github: usize,
    
    #[arg(long, default_value = "6")]
    official: usize,

    #[arg(long, default_value = "300")]
    timeout: usize,

    #[arg(long, default_value = "vectors", value_parser = ["vectors", "json", "md"])]
    mode: String,
}

#[tokio::main]
async fn main() -> Result<(), String> {
    let args = Args::parse();
    let start = Instant::now();

    println!("🔬 CCLL Autonomous Research Pipeline");
    println!("{}", "=".repeat(50));
    println!("Topic: {}", args.topic);
    println!();

    let client = Client::builder()
        .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;

    let query_terms: Vec<String> = args
        .topic
        .split_whitespace()
        .map(|s| s.to_string())
        .collect();

    println!("Phase 1: Expanding queries...");
    let queries = expand_queries_with_sources(
        &args.topic,
        args.google,
        args.github,
        args.official,
    );
    let queries: Vec<String> = queries.into_iter().take(args.queries * 20).collect();
    println!("  Running {} search variations", queries.len());
    println!("  - {} Google", args.google);
    println!("   - {} GitHub", args.github);
    println!("   - {} Official", args.official);

    let gemini_key = std::env::var("GEMINI_API_KEY").is_ok();
    let minimax_key = std::env::var("MINIMAX_API_KEY").is_ok();

    let mut all_results: Vec<SearchResult> = Vec::new();

    // Phase 2a: Search via Gemini (20 queries)
    if gemini_key {
        println!("\nPhase 2a: Gemini search ({} queries)...", queries.len());
        let search_futures: Vec<_> = queries
            .iter()
            .map(|q| {
                let client = &client;
                let q = q.clone();
                async move {
                    let _ = tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
                    dsearch::search_gemini(&client, &q, 10).await
                }
            })
            .collect();

        let search_results: Vec<Result<Vec<SearchResult>, String>> = join_all(search_futures).await;

        for result in search_results {
            match result {
                Ok(results) => {
                    // Push to zvec in background (non-blocking)
                    for r in &results {
                        let _ = std::process::Command::new("python3")
                            .args(&["push_zvec.py", &r.title, &r.url, &r.snippet, &args.topic])
                            .spawn();
                    }
                    all_results.extend(results);
                }
                Err(e) => eprintln!("  Gemini error: {}", e),
            }
        }
        println!("  Gemini found {} results", all_results.len());
    }

    // Phase 2b: Search via MiniMax (20 queries)
    if minimax_key {
        println!("\nPhase 2b: MiniMax search ({} queries)...", queries.len());
        let search_futures: Vec<_> = queries
            .iter()
            .map(|q| {
                let client = &client;
                let q = q.clone();
                async move {
                    let _ = tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
                    dsearch::search_minimax(&client, &q, 10).await
                }
            })
            .collect();

        let search_results: Vec<Result<Vec<SearchResult>, String>> = join_all(search_futures).await;

        for result in search_results {
            match result {
                Ok(results) => {
                    // Push to zvec in background (non-blocking)
                    for r in &results {
                        let _ = std::process::Command::new("python3")
                            .args(&["push_zvec.py", &r.title, &r.url, &r.snippet, &args.topic])
                            .spawn();
                    }
                    all_results.extend(results);
                }
                Err(e) => eprintln!("  MiniMax error: {}", e),
            }
        }
        println!("  MiniMax found {} results", all_results.len());
    }

    let xai_key = std::env::var("XAI_API_KEY").is_ok();

    // Phase 2c: Search via xAI web search (20 queries)
    if xai_key {
        println!("\nPhase 2c: xAI web search ({} queries)...", queries.len());
        let search_futures: Vec<_> = queries
            .iter()
            .map(|q| {
                let q = q.clone();
                async move {
                    let _ = tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
                    dsearch::search_xai(&q, 10).await
                }
            })
            .collect();

        let search_results: Vec<Result<Vec<SearchResult>, String>> = join_all(search_futures).await;

        let mut xai_results = 0;
        for result in search_results {
            match result {
                Ok(results) => {
                    // Push to zvec in background (non-blocking)
                    for r in &results {
                        let _ = std::process::Command::new("python3")
                            .args(&["push_zvec.py", &r.title, &r.url, &r.snippet, &args.topic])
                            .spawn();
                    }
                    xai_results += results.len();
                    all_results.extend(results);
                }
                Err(e) => eprintln!("  xAI error: {}", e),
            }
        }
        println!("  xAI web search found {} results", xai_results);
    }

    // Phase 2d: Search via xAI X search (20 queries)
    if xai_key {
        println!("\nPhase 2d: xAI X search ({} queries)...", queries.len());
        let search_futures: Vec<_> = queries
            .iter()
            .map(|q| {
                let q = q.clone();
                async move {
                    let _ = tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
                    dsearch::xai_x_search(&q, 10).await
                }
            })
            .collect();

        let search_results: Vec<Result<Vec<SearchResult>, String>> = join_all(search_futures).await;

        let mut x_results = 0;
        for result in search_results {
            match result {
                Ok(results) => {
                    // Push to zvec in background (non-blocking)
                    for r in &results {
                        let _ = std::process::Command::new("python3")
                            .args(&["push_zvec.py", &r.title, &r.url, &r.snippet, &args.topic])
                            .spawn();
                    }
                    x_results += results.len();
                    all_results.extend(results);
                }
                Err(e) => eprintln!("  xAI X search error: {}", e),
            }
        }
        println!("  xAI X search found {} results", x_results);
    }

    if let Some(urls) = &args.urls {
        for url in urls {
            all_results.push(SearchResult {
                title: format!("User-provided: {}", url),
                url: url.clone(),
                snippet: "User-specified URL for research".to_string(),
            });
        }
    }

    if all_results.is_empty() {
        eprintln!("\n⚠️  No search results found. This may be due to:");
        eprintln!("   - Missing API keys (GEMINI_API_KEY or MINIMAX_API_KEY)");
        eprintln!("   - Rate limiting");
        eprintln!("\nOptions:");
        eprintln!("   1. Set GEMINI_API_KEY (free: https://aistudio.google.com/apikey)");
        eprintln!("   2. Use --urls to specify URLs directly");
        eprintln!("   3. Try again later if rate limited");
    }

    println!("  Found {} total results", all_results.len());

    // Handle based on mode
    match args.mode.as_str() {
        "json" => {
            // Just save raw JSON
            let raw_results_file = format!("{}_raw.json", args.topic.replace(" ", "_"));
            let raw_json = serde_json::to_string_pretty(&all_results).unwrap_or_default();
            std::fs::write(&raw_results_file, &raw_json).ok();
            println!("  ✓ Saved to: {}", raw_results_file);
        }
        "vectors" => {
            // Already pushed to zvec during search (background)
            // Just save small index
            let index_file = format!("{}_index.json", args.topic.replace(" ", "_"));
            let index: Vec<_> = all_results.iter().map(|r| serde_json::json!({"title": r.title, "url": r.url})).collect();
            std::fs::write(&index_file, serde_json::to_string_pretty(&index).unwrap()).ok();
            println!("  ✓ Vectors pushed to zvec (background)");
            println!("  ✓ Index saved to: {}", index_file);
        }
        "md" | _ => {
            // Default: Full MD report (existing logic)
            let raw_results_file = format!("{}_raw.json", args.topic.replace(" ", "_"));
            let raw_json = serde_json::to_string_pretty(&all_results).unwrap_or_default();
            std::fs::write(&raw_results_file, &raw_json).ok();
            println!("  Raw results saved to: {}", raw_results_file);

            println!("\nPhase 3: Ranking & deduplication...");
            let scored = score_and_rank(all_results.clone(), args.top, &query_terms);
            println!("  Selected top {} sources for detailed fetching", scored.len());

            // Create file to append fetched content
            let fetched_file = format!("{}_fetched.md", args.topic.replace(" ", "_"));
            std::fs::write(&fetched_file, format!("# Research: {}\n\n", args.topic)).ok();
            println!("\nPhase 4: Fetching content... (appending to {})", fetched_file);

            // Fetch with streaming - append each result as it completes
            for (i, s) in scored.iter().enumerate() {
                let client = &client;
                let url = s.result.url.clone();
                let max_kb = args.max_kb;
                
                match fetch_url(client, &url, max_kb).await {
                    Ok(page) => {
                        let content = format!(
                            "\n\n## Source {}: {}\n**URL:** {}\n\n{}\n",
                            i + 1,
                            page.title,
                            page.url,
                            page.markdown
                        );
                        std::fs::OpenOptions::new()
                            .append(true)
                            .open(&fetched_file)
                            .and_then(|mut f| std::io::Write::write_all(&mut f, content.as_bytes()))
                            .ok();
                        println!("  ✓ Fetched: {}", page.title.chars().take(50).collect::<String>());
                    }
                    Err(e) => {
                        let error_msg = format!("\n\n## Source {}: FAILED\n**URL:** {}\n**Error:** {}\n", i + 1, url, e);
                        std::fs::OpenOptions::new()
                            .append(true)
                            .open(&fetched_file)
                            .and_then(|mut f| std::io::Write::write_all(&mut f, error_msg.as_bytes()))
                            .ok();
                        eprintln!("  ✗ Failed: {}", url);
                    }
                }
            }

            println!("  All content appended to: {}", fetched_file);

            let elapsed = start.elapsed();
            let summary = format!(
                "Research: {}\nResults: {}\nFile: {}\nTime: {:.1}s",
                args.topic,
                all_results.len(),
                fetched_file,
                elapsed.as_secs_f64()
            );

            println!("\n{}", summary);
        }
    }

    Ok(())
}
