use clap::Parser;
use reqwest::blocking::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Serialize, Deserialize)]
pub struct SearchResult {
    pub title: String,
    pub url: String,
    pub snippet: String,
}

fn search_gemini(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let api_key = std::env::var("GEMINI_API_KEY").map_err(|_| "GEMINI_API_KEY not set")?;

    let client = Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;

    let url = format!(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={}",
        api_key
    );

    let body = serde_json::json!({
        "contents": [{
            "parts": [{
                "text": format!("Search the web for: {}. Return a JSON array with objects containing 'title', 'url', and 'snippet' fields. Provide {} results.", query, limit)
            }]
        }],
        "tools": [{
            "function_declarations": [{
                "name": "web_search",
                "description": "Search the web for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            }]
        }]
    });

    let response = client
        .post(&url)
        .header("Content-Type", "application/json")
        .json(&body)
        .send()
        .map_err(|e| e.to_string())?;

    let text = response.text().map_err(|e| e.to_string())?;

    let parsed: serde_json::Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;

    let candidates = parsed["candidates"]
        .as_array()
        .ok_or("No candidates in response")?;

    let mut results = Vec::new();
    for candidate in candidates {
        if let Some(parts) = candidate["content"]["parts"].as_array() {
            for part in parts {
                if let Some(text) = part["text"].as_str() {
                    if let Ok(json_results) = serde_json::from_str::<Vec<SearchResult>>(text) {
                        results.extend(json_results);
                    }
                }
            }
        }
    }

    if results.is_empty() {
        return Err("No results from Gemini".to_string());
    }

    Ok(results)
}

fn search_minimax(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let api_key = std::env::var("MINIMAX_API_KEY").map_err(|_| "MINIMAX_API_KEY not set")?;
    let host =
        std::env::var("MINIMAX_API_HOST").unwrap_or_else(|_| "https://api.minimax.io".to_string());

    let client = Client::builder()
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;

    let url = format!("{}/v1/coding_plan/search", host.trim_end_matches('/'));

    let body = serde_json::json!({
        "q": query
    });

    let response = client
        .post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Content-Type", "application/json")
        .header("MM-API-Source", "dsearch")
        .json(&body)
        .send()
        .map_err(|e| e.to_string())?;

    let text = response.text().map_err(|e| e.to_string())?;

    let parsed: serde_json::Value = serde_json::from_str(&text).map_err(|e| e.to_string())?;

    let mut results = Vec::new();
    if let Some(organic) = parsed["organic"].as_array() {
        for item in organic.iter().take(limit) {
            let title = item["title"].as_str().unwrap_or("");
            let url = item["link"].as_str().unwrap_or("");
            let snippet = item["snippet"].as_str().unwrap_or("");

            if !title.is_empty() && !url.is_empty() {
                results.push(SearchResult {
                    title: title.to_string(),
                    url: url.to_string(),
                    snippet: snippet.to_string(),
                });
            }
        }
    }

    if results.is_empty() {
        return Err("No results from MiniMax".to_string());
    }

    Ok(results)
}

fn search_xai(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let _api_key = std::env::var("XAI_API_KEY").map_err(|_| "XAI_API_KEY not set")?;

    let script_path = std::path::Path::new("xai_search.py");
    let script_arg = if script_path.exists() {
        "xai_search.py"
    } else {
        "scripts/scripts/xai_search.py"
    };

    let output = std::process::Command::new("python3")
        .arg(script_arg)
        .arg(query)
        .arg("--limit")
        .arg(limit.to_string())
        .output()
        .map_err(|e| format!("Failed to execute python script: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("xAI Python script failed: {}", stderr));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    
    let json_start = stdout.find('[').unwrap_or(0);
    let json_str = &stdout[json_start..];
    
    let results: Vec<SearchResult> = serde_json::from_str(json_str)
        .map_err(|e| format!("Failed to parse xAI results: {} - output was: {}", e, stdout))?;

    if results.is_empty() {
        return Err("No results from xAI search".to_string());
    }

    Ok(results)
}

fn search_with_fallback(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    if std::env::var("XAI_API_KEY").is_ok() {
        match search_xai(query, limit) {
            Ok(results) if !results.is_empty() => return Ok(results),
            Ok(_) => eprintln!("xAI returned empty"),
            Err(e) => eprintln!("xAI failed: {}", e),
        }
    }

    if std::env::var("GEMINI_API_KEY").is_ok() {
        match search_gemini(query, limit) {
            Ok(results) if !results.is_empty() => return Ok(results),
            Ok(_) => eprintln!("Gemini returned empty"),
            Err(e) => eprintln!("Gemini failed: {}", e),
        }
    }

    if std::env::var("MINIMAX_API_KEY").is_ok() {
        match search_minimax(query, limit) {
            Ok(results) if !results.is_empty() => return Ok(results),
            Ok(_) => eprintln!("MiniMax returned empty"),
            Err(e) => eprintln!("MiniMax failed: {}", e),
        }
    }

    Err("No search API keys set. Set XAI_API_KEY, GEMINI_API_KEY, or MINIMAX_API_KEY".to_string())
}

#[derive(Parser)]
#[command(name = "web_search")]
#[command(about = "Web search using xAI (Grok), Gemini, or MiniMax")]
struct Args {
    query: String,
    #[arg(short, long, default_value = "10")]
    limit: usize,
    #[arg(short, long)]
    output: Option<String>,
}

fn main() {
    let args = Args::parse();

    match search_with_fallback(&args.query, args.limit) {
        Ok(results) => {
            if let Some(output_path) = args.output {
                let json = serde_json::to_string_pretty(&results).unwrap();
                std::fs::write(&output_path, json).unwrap();
                println!("Results written to {}", output_path);
            } else {
                for (i, r) in results.iter().enumerate() {
                    println!("{}. {}", i + 1, r.title);
                    println!("   {}", r.url);
                    let snippet = if r.snippet.len() > 200 {
                        match r.snippet.char_indices().nth(200) {
                            Some((idx, _)) => format!("{}...", &r.snippet[..idx]),
                            None => r.snippet.clone(),
                        }
                    } else {
                        r.snippet.clone()
                    };
                    println!("   {}", snippet);
                    println!();
                }
            }
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            std::process::exit(1);
        }
    }
}
