use std::time::Instant;
use reqwest::Client;
use serde::Deserialize;

#[derive(Deserialize)]
struct GeminiResponse {
    candidates: Option<Vec<GeminiCandidate>>,
}

#[derive(Deserialize)]
struct GeminiCandidate {
    grounding_metadata: Option<GroundingMetadata>,
}

#[derive(Deserialize)]
struct GroundingMetadata {
    grounding_chunks: Option<Vec<GroundingChunk>>,
}

#[derive(Deserialize)]
struct GroundingChunk {
    web: Option<GeminiWeb>,
}

#[derive(Deserialize)]
struct GeminiWeb {
    uri: Option<String>,
    title: Option<String>,
}

async fn search(client: &Client, api_key: &str, i: usize) -> usize {
    let url = format!(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={}",
        api_key
    );

    let request_body = serde_json::json!({
        "contents": [{ "role": "user", "parts": [{ "text": format!("Search for: Model Context Protocol {}", i) }] }],
        "tools": [{ "googleSearch": {} }],
        "generationConfig": { "temperature": 0.0, "maxOutputTokens": 1024 }
    });

    let response = client.post(&url)
        .header("Content-Type", "application/json")
        .json(&request_body)
        .send()
        .await
        .unwrap();

    let body = response.text().await.unwrap();
    
    // Parse with serde_json::Value to extract chunks
    let json: serde_json::Value = serde_json::from_str(&body).unwrap();
    let chunks_count = json.get("candidates")
        .and_then(|c| c.as_array())
        .and_then(|arr| arr.first())
        .and_then(|c| c.get("groundingMetadata"))
        .and_then(|m| m.get("groundingChunks"))
        .and_then(|ch| ch.as_array())
        .map(|arr| arr.len())
        .unwrap_or(0);
    
    chunks_count
}

#[tokio::main]
async fn main() {
    let api_key = std::env::var("GEMINI_API_KEY").expect("GEMINI_API_KEY not set");
    let client = Client::new();

    println!("=== Rust (tokio) - 5 parallel calls ===");

    let start = Instant::now();

    let futures = (1..=5).map(|i| search(&client, &api_key, i));
    let results = futures::future::join_all(futures).await;
    
    let total: usize = results.iter().sum();

    let elapsed = start.elapsed().as_millis();

    println!("Time: {}ms", elapsed);
    println!("Results found: {}", total);
    println!();
}
