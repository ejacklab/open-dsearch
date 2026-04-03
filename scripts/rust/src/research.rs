use clap::Parser;
use futures::future::join_all;
use reqwest::Client;
use std::time::Instant;
use dsearch::{score_and_rank, SearchResult};

#[derive(Parser)]
struct Args {
    #[arg(short = 't', long)]
    topic: String,

    #[arg(short = 'n', long, default_value = "5")]
    top: usize,

    #[arg(long, default_value = "100")]
    max_kb: usize,

    #[arg(short = 'o', long)]
    output: Option<String>,

    #[arg(short = 'u', long)]
    urls: Option<Vec<String>>,

    #[arg(short = 'q', long = "query")]
    queries: Option<Vec<String>>,

    #[arg(long, default_value = "300")]
    timeout: usize,

    #[arg(short = 'm', long, default_value = "vectors", value_parser = ["vectors", "json", "md"])]
    mode: String,

    /// Push results to ZVec vector collection after search.
    #[arg(long)]
    index: bool,

    /// Wipe the ZVec collection before pushing (fresh start).
    #[arg(long)]
    clear: bool,

    /// ZVec collection path (default: ~/.open-dsearch/zvec_data).
    #[arg(long)]
    index_collection: Option<String>,
}

#[tokio::main]
async fn main() -> Result<(), String> {
    let args = Args::parse();
    let start = Instant::now();

    println!(
        "🔬 CCLL Autonomous Research Pipeline\n{}\nTopic: {}\n",
        "=".repeat(50),
        args.topic
    );

    let client = Client::builder()
        .user_agent("Mozilla/5.0")
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;

    let queries = args
        .queries
        .clone()
        .unwrap_or_else(|| vec![args.topic.clone()]);

    println!("[dsearch] topic : {:?}", args.topic);
    println!("[dsearch] queries : {:?}", queries);
    println!("[dsearch] count   : {}", queries.len());
    println!("[dsearch] index   : {}", args.index);

    // ── Search phases (no per-phase push — collect results ──
    let mut all_results = Vec::new();

    let gemini_results = run_gemini_phase(&client, &queries, &args.topic).await;
    all_results.extend(gemini_results);

    let minimax_results = run_minimax_phase(&client, &queries, &args.topic).await;
    all_results.extend(minimax_results);

    let kimi_results = run_kimi_phase(&client, &queries, &args.topic).await;
    all_results.extend(kimi_results);

    // xAI disabled: uncomment to re-enable
    // all_results.extend(run_xai_phases(&queries, &args.topic).await);

    if let Some(urls) = &args.urls {
        for url in urls {
            all_results.push(SearchResult {
                title: format!("User: {}", url),
                url: url.clone(),
                snippet: "User URL".to_string(),
            });
        }
    }

    println!("  Found {} total results", all_results.len());

    // ── Push to ZVec if --index ──
    if args.index {
        println!("\n[zvec] Indexing {} results...", all_results.len());
        if args.clear {
            push_zvec_clear(args.index_collection.as_deref());
        }
        push_zvec_batch(&all_results, &args.topic, "dsearch", args.index_collection.as_deref());
        println!("[zvec] Done.");
    }

    // ── Output based on mode ──
    match args.mode.as_str() {
        "json" => save_json(&all_results, &args.topic),
        "vectors" => save_vectors(&all_results, &args.topic),
        _ => run_md_report_phase(&client, all_results, &args).await?,
    }

    println!(
        "\nResearch: {}\nTime: {:.1}s",
        args.topic,
        start.elapsed().as_secs_f64()
    );
    Ok(())
}

// ── Phase runners (no ZVec push — caller collects results) ──────────────────

async fn run_gemini_phase(
    client: &Client,
    queries: &[String],
    _topic: &str,
) -> Vec<SearchResult> {
    if dsearch::get_secret("gemini").is_err() {
        return Vec::new();
    }
    println!("\nPhase: Gemini ({} queries)...", queries.len());
    for (i, q) in queries.iter().enumerate() {
        println!("[gemini] query {}: {:?}", i + 1, q);
    }
    let mut results = Vec::new();
    let futs: Vec<_> = queries
        .iter()
        .map(|q| {
            let c = client;
            let q = q.clone();
            async move { dsearch::search_gemini(c, &q, 10).await }
        })
        .collect();
    for res in join_all(futs).await {
        if let Ok(list) = res {
            results.extend(list);
        }
    }
    println!("  Gemini found {} results", results.len());
    results
}

async fn run_minimax_phase(
    client: &Client,
    queries: &[String],
    _topic: &str,
) -> Vec<SearchResult> {
    if dsearch::get_secret("minimax").is_err() {
        return Vec::new();
    }
    println!("\nPhase: MiniMax ({} queries)...", queries.len());
    for (i, q) in queries.iter().enumerate() {
        println!("[minimax] query {}: {:?}", i + 1, q);
    }
    let mut results = Vec::new();
    let futs: Vec<_> = queries
        .iter()
        .map(|q| {
            let c = client;
            let q = q.clone();
            async move { dsearch::search_minimax(c, &q, 10).await }
        })
        .collect();
    for res in join_all(futs).await {
        if let Ok(list) = res {
            results.extend(list);
        }
    }
    println!("  MiniMax found {} results", results.len());
    results
}

async fn run_kimi_phase(
    client: &Client,
    queries: &[String],
    _topic: &str,
) -> Vec<SearchResult> {
    if dsearch::get_secret("kimi").is_err() {
        return Vec::new();
    }
    println!("\nPhase: Kimi ({} queries)...", queries.len());
    for (i, q) in queries.iter().enumerate() {
        println!("[kimi] query {}: {:?}", i + 1, q);
    }
    let mut results = Vec::new();
    let futs: Vec<_> = queries
        .iter()
        .map(|q| {
            let c = client;
            let q = q.clone();
            async move { dsearch::search_kimi(c, &q, 10).await }
        })
        .collect();
    for res in join_all(futs).await {
        if let Ok(list) = res {
            results.extend(list);
        }
    }
    println!("  Kimi found {} results", results.len());
    results
}

// ── ZVec batch push ─────────────────────────────────────────────────────────

/// Wipe the ZVec collection via python3 subprocess.
fn push_zvec_clear(collection: Option<&str>) {
    let python_script = std::path::PathBuf::from(
        "/home/smoke01/.openclaw/workspace-dave/open-dsearch/scripts/push_zvec.py",
    );

    let mut cmd = std::process::Command::new("python3");
    cmd.arg(&python_script)
        .arg("add")
        .arg("--clear");

    if let Some(col) = collection {
        cmd.arg("--collection").arg(col);
    }

    match cmd.stdout(std::process::Stdio::piped()).spawn() {
        Ok(child) => {
            match child.wait_with_output() {
                Ok(out) => {
                    if out.status.success() {
                        print!("  [zvec] cleared");
                    } else {
                        let stderr = String::from_utf8_lossy(&out.stderr);
                        eprint!("  [zvec] clear failed: {}", stderr.trim());
                    }
                }
                Err(e) => eprintln!("  [zvec] clear wait failed: {}", e),
            }
        }
        Err(e) => eprintln!("  [zvec] clear spawn failed: {}", e),
    }
}

/// Push all results to ZVec via a single python3 subprocess (batch JSONL).
/// Uses file locking (fcntl.flock) in push_zvec.py to avoid concurrent-write races.
fn push_zvec_batch(results: &[SearchResult], topic: &str, source: &str, collection: Option<&str>) {
    use std::io::Write;

    let temp_file = format!("/tmp/zvec_push_{}.jsonl", std::process::id());
    let mut file = match std::fs::File::create(&temp_file) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("  [zvec] could not create temp file: {}", e);
            return;
        }
    };

    for r in results {
        let entry = serde_json::json!({
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet,
            "source": source
        });
        if writeln!(file, "{}", entry).is_err() {
            eprintln!("  [zvec] failed to write JSONL entry");
            return;
        }
    }
    drop(file);

    // Locate push_zvec.py — use hardcoded path if available, else relative to cwd
    let python_script = std::path::PathBuf::from(
        "/home/smoke01/.openclaw/workspace-dave/open-dsearch/scripts/push_zvec.py",
    );

    let mut cmd = std::process::Command::new("python3");
    cmd.arg(&python_script)
        .arg("add")
        .arg("--batch")
        .arg("--topic")
        .arg(topic);

    if let Some(col) = collection {
        cmd.arg("--collection").arg(col);
    }

    let child = match cmd
        .stdin(std::process::Stdio::from(
            std::fs::File::open(&temp_file).unwrap(),
        ))
        .stdout(std::process::Stdio::piped())
        .spawn()
    {
        Ok(c) => c,
        Err(e) => {
            eprintln!("  [zvec] push failed (spawn): {}", e);
            let _ = std::fs::remove_file(&temp_file);
            return;
        }
    };

    match child.wait_with_output() {
        Ok(out) => {
            if !out.status.success() {
                let stderr = String::from_utf8_lossy(&out.stderr);
                eprintln!("  [zvec] push failed: {}", stderr.trim());
            } else {
                let stdout = String::from_utf8_lossy(&out.stdout);
                print!("  [zvec] {}", stdout.trim());
            }
        }
        Err(e) => eprintln!("  [zvec] push failed (wait): {}", e),
    }

    let _ = std::fs::remove_file(&temp_file);
}

// ── Output helpers ───────────────────────────────────────────────────────────

fn save_json(results: &[SearchResult], topic: &str) {
    let file = format!("{}_raw.json", topic.replace(" ", "_"));
    std::fs::write(&file, serde_json::to_string_pretty(results).unwrap_or_default()).ok();
    println!("  ✓ Saved to: {}", file);
}

fn save_vectors(results: &[SearchResult], topic: &str) {
    let file = format!("{}_index.json", topic.replace(" ", "_"));
    let index: Vec<_> = results
        .iter()
        .map(|r| serde_json::json!({"title": r.title, "url": r.url}))
        .collect();
    std::fs::write(&file, serde_json::to_string_pretty(&index).unwrap()).ok();
    println!("  ✓ Index saved to: {}", file);
}

async fn run_md_report_phase(client: &Client, results: Vec<SearchResult>, args: &Args) -> Result<(), String> {
    save_json(&results, &args.topic);
    let scored = score_and_rank(
        results,
        args.top,
        &args.topic.split_whitespace().map(|s| s.to_string()).collect::<Vec<_>>(),
    );
    let file = format!("{}_fetched.md", args.topic.replace(" ", "_"));
    std::fs::write(&file, format!("# Research: {}\n\n", args.topic)).ok();
    for (i, s) in scored.iter().enumerate() {
        let page = match dsearch::fetch_url(client, &s.result.url, args.max_kb).await {
            Ok(p) => p,
            Err(_) => dsearch::FetchedPage {
                url: s.result.url.clone(),
                title: s.result.title.clone(),
                markdown: "Fetch failed".into(),
                byte_size: 0,
            },
        };
        let content = format!(
            "\n\n## Source {}: {}\n**URL:** {}\n\n{}\n",
            i + 1,
            page.title,
            page.url,
            page.markdown
        );
        let mut f =
            std::fs::OpenOptions::new()
                .append(true)
                .open(&file)
                .map_err(|e| e.to_string())?;
        use std::io::Write;
        f.write_all(content.as_bytes())
            .map_err(|e| e.to_string())?;
        println!(
            "  ✓ Fetched: {}",
            page.title.chars().take(50).collect::<String>()
        );
    }
    Ok(())
}

// ── Tests ────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn parse(args: &[&str]) -> Result<Args, clap::Error> {
        Args::try_parse_from(std::iter::once("research").chain(args.iter().copied()))
    }

    #[test]
    fn test_index_flag_default_false() {
        let args = parse(&["--topic", "test"]).unwrap();
        assert!(!args.index);
        assert!(args.index_collection.is_none());
    }

    #[test]
    fn test_index_flag_true() {
        let args = parse(&["--topic", "test", "--index"]).unwrap();
        assert!(args.index);
    }

    #[test]
    fn test_index_collection() {
        let args = parse(&["--topic", "test", "--index", "--index-collection", "/tmp/my-col"]).unwrap();
        assert!(args.index);
        assert_eq!(args.index_collection.as_deref(), Some("/tmp/my-col"));
    }

    #[test]
    fn test_clear_flag() {
        let args = parse(&["--topic", "test", "--index", "--clear"]).unwrap();
        assert!(args.clear);
        assert!(args.index);
    }

    #[test]
    fn test_topic_unchanged() {
        let args = parse(&["--topic", "kube-scheduler MIG GPU bin-packing"]).unwrap();
        assert_eq!(args.topic, "kube-scheduler MIG GPU bin-packing");
    }

    #[test]
    fn test_missing_topic_fails() {
        assert!(parse(&[]).is_err());
    }

    #[test]
    fn test_defaults() {
        let args = parse(&["--topic", "anything"]).unwrap();
        assert_eq!(args.top, 5);
        assert_eq!(args.timeout, 300);
        assert_eq!(args.mode, "vectors");
        assert_eq!(args.max_kb, 100);
        assert!(!args.index);
        assert!(args.output.is_none());
    }

    #[test]
    fn test_urls_parsed() {
        let args = parse(&[
            "--topic", "anything",
            "--urls", "https://tokio.rs",
            "--urls", "https://docs.rs",
        ]).unwrap();
        let urls = args.urls.unwrap();
        assert_eq!(urls.len(), 2);
    }

    #[test]
    fn test_multiple_queries() {
        let args = parse(&[
            "--topic", "Rust LLM",
            "--query", "Tokio vs Rayon LLM inference Rust 2026",
            "--query", "dynamic batching GPU utilization Rust LLM serving latency",
        ]).unwrap();
        let queries = args.queries.unwrap();
        assert_eq!(queries.len(), 2);
    }
}
