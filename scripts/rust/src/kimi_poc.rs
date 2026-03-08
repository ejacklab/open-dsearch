//! Kimi POC - Test single web search with Kimi API
//! Run: cargo run --bin kimi_poc --release

use clap::Parser;
use dsearch::{get_secret, search_kimi};
use reqwest::Client;

#[derive(Parser)]
struct Args {
    #[arg(short, long, default_value = "Moonshot AI Context Caching")]
    query: String,
    #[arg(short, long, default_value = "3")]
    limit: usize,
}

#[tokio::main]
async fn main() {
    let args = Args::parse();
    println!("🔍 Kimi POC — Testing web search\n");
    println!("Query: {}", args.query);
    println!("Limit: {}\n", args.limit);

    // Step 1: Get API key
    println!("[1/3] Fetching API key from GCSM...");
    let api_key = match get_secret("kimi") {
        Ok(key) => {
            let masked = if key.len() > 8 {
                format!("{}...{}", &key[..4], &key[key.len()-4..])
            } else {
                "***".to_string()
            };
            println!("      ✓ Key found: {}\n", masked);
            key
        }
        Err(e) => {
            println!("      ✗ Failed: {}", e);
            println!("\nTo fix: Add KIMI_API_KEY to GCP Secret Manager");
            println!("  gcloud secrets create KIMI_API_KEY --project=771559838251 --data-file=- <<< $YOUR_KEY");
            std::process::exit(1);
        }
    };

    // Step 2: Create client and search
    println!("[2/3] Calling Kimi API...");
    let client = Client::builder()
        .user_agent("dsearch-poc")
        .timeout(std::time::Duration::from_secs(60))
        .build()
        .unwrap();

    match search_kimi(&client, &args.query, args.limit).await {
        Ok(results) => {
            println!("      ✓ Got {} results\n", results.len());

            // Step 3: Display results
            println!("[3/3] Results:");
            println!("{}", "─".repeat(60));
            for (i, r) in results.iter().enumerate() {
                println!("\n{}. {}", i + 1, r.title);
                println!("   URL: {}", r.url);
                println!("   Snippet: {}", r.snippet);
            }
            println!("\n{}", "─".repeat(60));
            println!("✅ Kimi POC successful!");
        }
        Err(e) => {
            println!("      ✗ Search failed: {}", e);
            std::process::exit(1);
        }
    }
}
