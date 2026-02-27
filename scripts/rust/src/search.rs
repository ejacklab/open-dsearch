use crate::FetchedPage;
use reqwest::Client;
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub title: String,
    pub url: String,
    pub snippet: String,
}

#[derive(Deserialize)]
struct GeminiResponse {
    candidates: Option<Vec<GeminiCandidate>>,
}

#[derive(Deserialize)]
struct GeminiCandidate {
    #[serde(rename = "groundingMetadata")]
    grounding_metadata: Option<GeminiGroundingMetadata>,
}

#[derive(Deserialize)]
struct GeminiGroundingMetadata {
    #[serde(rename = "groundingChunks")]
    grounding_chunks: Option<Vec<GeminiGroundingChunk>>,
}

#[derive(Deserialize)]
struct GeminiGroundingChunk {
    web: Option<GeminiWeb>,
}

#[derive(Deserialize)]
struct GeminiWeb {
    uri: Option<String>,
    title: Option<String>,
}

#[derive(Deserialize)]
struct MinimaxSearchResponse {
    organic: Option<Vec<MinimaxOrganicResult>>,
    #[serde(rename = "related_searches")]
    related_searches: Option<Vec<MinimaxRelatedSearch>>,
}

#[derive(Deserialize)]
struct MinimaxOrganicResult {
    title: Option<String>,
    link: Option<String>,
    snippet: Option<String>,
    date: Option<String>,
}

#[derive(Deserialize)]
struct MinimaxRelatedSearch {
    query: Option<String>,
}

pub async fn search_minimax(client: &Client, query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let api_key = std::env::var("MINIMAX_API_KEY").map_err(|_| "MINIMAX_API_KEY not set")?;
    let api_host = std::env::var("MINIMAX_API_HOST").map_err(|_| "MINIMAX_API_HOST not set (e.g., https://api.minimax.io)")?;
    
    let url = format!("{}/v1/coding_plan/search", api_host.trim_end_matches('/'));

    let request_body = serde_json::json!({
        "q": query
    });

    let response = client
        .post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Content-Type", "application/json")
        .header("MM-API-Source", "dsearch")
        .json(&request_body)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let body = response.text().await.map_err(|e| e.to_string())?;
    
    let search_response: MinimaxSearchResponse = serde_json::from_str(&body)
        .map_err(|e| format!("Failed to parse Minimax response: {}", e))?;

    let organic = search_response.organic.unwrap_or_default();

    let mut results = Vec::new();
    for item in organic.into_iter().take(limit) {
        let title = item.title.unwrap_or_default();
        let url = item.link.unwrap_or_default();
        let snippet = item.snippet.unwrap_or_default();
        
        if !title.is_empty() && !url.is_empty() {
            results.push(SearchResult {
                title,
                url,
                snippet,
            });
        }
    }

    if results.is_empty() {
        return Err("No results from Minimax search".to_string());
    }

    Ok(results)
}

pub async fn search_gemini(client: &Client, query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let api_key = std::env::var("GEMINI_API_KEY").map_err(|_| "GEMINI_API_KEY not set")?;
    
    let url = format!(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={}",
        api_key
    );

    let request_body = serde_json::json!({
        "contents": [{
            "role": "user",
            "parts": [{ "text": format!("Search for: {}", query) }]
        }],
        "tools": [{ "googleSearch": {} }],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 1024
        }
    });

    let response = client
        .post(&url)
        .header("Content-Type", "application/json")
        .json(&request_body)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let body = response.text().await.map_err(|e| e.to_string())?;
    
    let gemini_response: GeminiResponse = serde_json::from_str(&body)
        .map_err(|e| format!("Failed to parse Gemini response: {}", e))?;

    let chunks = gemini_response
        .candidates
        .and_then(|c| c.into_iter().next())
        .and_then(|c| c.grounding_metadata)
        .and_then(|g| g.grounding_chunks)
        .unwrap_or_default();

    let mut results = Vec::new();
    for chunk in chunks.into_iter().take(limit) {
        if let Some(web) = chunk.web {
            let title = web.title.unwrap_or_default();
            let url = web.uri.unwrap_or_default();
            if !title.is_empty() && !url.is_empty() {
                results.push(SearchResult {
                    title,
                    url,
                    snippet: format!("Source for: {}", query),
                });
            }
        }
    }

    if results.is_empty() {
        return Err("No results from Gemini Google Search".to_string());
    }

    Ok(results)
}

#[derive(Debug, Clone, Default)]
pub struct XaiSearchParams {
    pub allowed_domains: Option<String>,
    pub excluded_domains: Option<String>,
    pub enable_image_understanding: bool,
    pub allowed_handles: Option<String>,
    pub excluded_handles: Option<String>,
    pub from_date: Option<String>,
    pub to_date: Option<String>,
    pub enable_video_understanding: bool,
    pub model: Option<String>,
    pub timeout: Option<u64>,
}

impl XaiSearchParams {
    fn to_args(&self) -> Vec<String> {
        let mut args = Vec::new();
        
        if let Some(ref domains) = self.allowed_domains {
            args.push("--allowed-domains".to_string());
            args.push(domains.clone());
        }
        if let Some(ref domains) = self.excluded_domains {
            args.push("--excluded-domains".to_string());
            args.push(domains.clone());
        }
        if self.enable_image_understanding {
            args.push("--enable-image-understanding".to_string());
        }
        if let Some(ref handles) = self.allowed_handles {
            args.push("--allowed-handles".to_string());
            args.push(handles.clone());
        }
        if let Some(ref handles) = self.excluded_handles {
            args.push("--excluded-handles".to_string());
            args.push(handles.clone());
        }
        if let Some(ref from) = self.from_date {
            args.push("--from-date".to_string());
            args.push(from.clone());
        }
        if let Some(ref to) = self.to_date {
            args.push("--to-date".to_string());
            args.push(to.clone());
        }
        if self.enable_video_understanding {
            args.push("--enable-video-understanding".to_string());
        }
        if let Some(ref model) = self.model {
            args.push("--model".to_string());
            args.push(model.clone());
        }
        if let Some(timeout) = self.timeout {
            args.push("--timeout".to_string());
            args.push(timeout.to_string());
        }
        
        args
    }
}

pub async fn search_xai_with_params(
    query: &str, 
    limit: usize,
    params: XaiSearchParams,
) -> Result<Vec<SearchResult>, String> {
    let _api_key = std::env::var("XAI_API_KEY").map_err(|_| "XAI_API_KEY not set")?;
    
    let script_path = std::path::Path::new("xai_search.py");
    let script_arg = if script_path.exists() {
        "xai_search.py"
    } else {
        "scripts/scripts/xai_search.py"
    };

    let mut cmd_args = vec![
        script_arg.to_string(),
        query.to_string(),
        "--limit".to_string(),
        limit.to_string(),
    ];
    cmd_args.extend(params.to_args());

    let output = match tokio::task::spawn_blocking(move || {
        let mut cmd = std::process::Command::new("python3");
        for arg in &cmd_args {
            cmd.arg(arg);
        }
        cmd.output()
    }).await {
        Ok(Ok(output)) => output,
        Ok(Err(e)) => return Err(format!("Failed to execute python script: {}", e)),
        Err(e) => return Err(format!("Task failed: {}", e)),
    };

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

pub async fn search_xai(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    search_xai_with_params(query, limit, XaiSearchParams::default()).await
}

pub async fn xai_x_search_with_params(
    query: &str, 
    limit: usize,
    params: XaiSearchParams,
) -> Result<Vec<SearchResult>, String> {
    let _api_key = std::env::var("XAI_API_KEY").map_err(|_| "XAI_API_KEY not set")?;
    
    let script_path = std::path::Path::new("xai_search.py");
    let script_arg = if script_path.exists() {
        "xai_search.py"
    } else {
        "scripts/scripts/xai_search.py"
    };

    let mut cmd_args = vec![
        script_arg.to_string(),
        query.to_string(),
        "--limit".to_string(),
        limit.to_string(),
        "--x-search".to_string(),
    ];
    cmd_args.extend(params.to_args());

    let output = match tokio::task::spawn_blocking(move || {
        let mut cmd = std::process::Command::new("python3");
        for arg in &cmd_args {
            cmd.arg(arg);
        }
        cmd.output()
    }).await {
        Ok(Ok(output)) => output,
        Ok(Err(e)) => return Err(format!("Failed to execute python script: {}", e)),
        Err(e) => return Err(format!("Task failed: {}", e)),
    };

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

pub async fn xai_x_search(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    xai_x_search_with_params(query, limit, XaiSearchParams::default()).await
}

pub async fn search_with_fallback(client: &Client, query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let timeout = std::time::Duration::from_secs(66 * 60);
    
    let gemini_key = std::env::var("GEMINI_API_KEY").is_ok();
    let minimax_key = std::env::var("MINIMAX_API_KEY").is_ok();
    let xai_key = std::env::var("XAI_API_KEY").is_ok();
    
    if !gemini_key && !minimax_key && !xai_key {
        return Err("No search API keys set. Set XAI_API_KEY, GEMINI_API_KEY, or MINIMAX_API_KEY".to_string());
    }
    
    let mut all_results: Vec<SearchResult> = Vec::new();
    
    if gemini_key && minimax_key {
        let gemini_fut = search_gemini(client, query, limit);
        let minimax_fut = search_minimax(client, query, limit);
        
        match tokio::time::timeout(timeout, async {
            tokio::join!(gemini_fut, minimax_fut)
        }).await {
            Ok((gemini_result, minimax_result)) => {
                if let Ok(results) = gemini_result {
                    if !results.is_empty() {
                        eprintln!("  ✓ Gemini search succeeded");
                        all_results.extend(results);
                    }
                }
                if let Ok(results) = minimax_result {
                    if !results.is_empty() {
                        eprintln!("  ✓ MiniMax search succeeded");
                        all_results.extend(results);
                    }
                }
            }
            Err(_) => eprintln!("  Search timeout after 66 minutes"),
        }
    } else if gemini_key {
        match tokio::time::timeout(timeout, search_gemini(client, query, limit)).await {
            Ok(Ok(results)) if !results.is_empty() => {
                eprintln!("  ✓ Gemini search succeeded");
                all_results.extend(results);
            }
            Ok(Ok(_)) => eprintln!("  Gemini returned empty"),
            Ok(Err(e)) => eprintln!("  Gemini failed: {}", e),
            Err(_) => eprintln!("  Gemini search timeout"),
        }
    } else if minimax_key {
        match tokio::time::timeout(timeout, search_minimax(client, query, limit)).await {
            Ok(Ok(results)) if !results.is_empty() => {
                eprintln!("  ✓ MiniMax search succeeded");
                all_results.extend(results);
            }
            Ok(Ok(_)) => eprintln!("  MiniMax returned empty"),
            Ok(Err(e)) => eprintln!("  MiniMax failed: {}", e),
            Err(_) => eprintln!("  MiniMax search timeout"),
        }
    }
    
    if xai_key {
        match tokio::time::timeout(timeout, search_xai(query, limit)).await {
            Ok(Ok(results)) if !results.is_empty() => {
                eprintln!("  ✓ xAI web search succeeded");
                all_results.extend(results);
            }
            Ok(Ok(_)) => eprintln!("  xAI web search returned empty"),
            Ok(Err(e)) => eprintln!("  xAI web search failed: {}", e),
            Err(_) => eprintln!("  xAI web search timeout"),
        }

        match tokio::time::timeout(timeout, xai_x_search(query, limit)).await {
            Ok(Ok(results)) if !results.is_empty() => {
                eprintln!("  ✓ xAI X search succeeded");
                all_results.extend(results);
            }
            Ok(Ok(_)) => eprintln!("  xAI X search returned empty"),
            Ok(Err(e)) => eprintln!("  xAI X search failed: {}", e),
            Err(_) => eprintln!("  xAI X search timeout"),
        }
    }
    
    if all_results.is_empty() {
        return Err("No results from any search API".to_string());
    }
    
    Ok(all_results)
}

pub fn expand_queries(topic: &str) -> Vec<String> {
    expand_queries_with_sources(topic, 8, 6, 6)
}

pub fn expand_queries_with_sources(
    topic: &str,
    google: usize,
    github: usize,
    official: usize,
) -> Vec<String> {
    let mut queries = Vec::new();
    
    // General queries (Google results) - generate google count
    for i in 0..google {
        let q = match i {
            0 => format!("{}", topic),
            1 => format!("{} tutorial", topic),
            2 => format!("{} guide", topic),
            3 => format!("{} explained", topic),
            4 => format!("{} basics", topic),
            5 => format!("{} introduction", topic),
            6 => format!("{} overview", topic),
            7 => format!("{} deep dive", topic),
            _ => format!("{} {}", topic, i),
        };
        queries.push(q);
    }
    
    // GitHub (high stars) - generate github count
    for i in 0..github {
        let q = match i {
            0 => format!("{} site:github.com stars:>1000", topic),
            1 => format!("{} github repository", topic),
            2 => format!("{} github stars", topic),
            3 => format!("{} site:github.com", topic),
            4 => format!("{} github stars:>500", topic),
            5 => format!("{} popular github", topic),
            _ => format!("{} github {}", topic, i),
        };
        queries.push(q);
    }
    
    // Official/important sources - generate official count
    let official_sources = vec![
        format!("{} site:anthropic.com", topic),
        format!("{} site:openai.com", topic),
        format!("{} site:github.com", topic),
        format!("{} site:grokipedia.com", topic),
        format!("{} documentation", topic),
        format!("{} official website", topic),
    ];
    for i in 0..official {
        if i < official_sources.len() {
            queries.push(official_sources[i].clone());
        } else {
            queries.push(format!("{} official {}", topic, i));
        }
    }
    
    // If no specific counts, use default queries
    if queries.is_empty() {
        queries = vec![
            format!("{} official documentation", topic),
            format!("{} engineering blog", topic),
            format!("{} github repository", topic),
            format!("{} tutorial guide", topic),
            format!("{} architecture deep dive", topic),
        ];
    }
    
    queries
}

pub async fn synthesize_with_llm(client: &Client, topic: &str, sources: Vec<FetchedPage>) -> Result<String, String> {
    let gemini_key = std::env::var("GEMINI_API_KEY").ok();
    let minimax_key = std::env::var("MINIMAX_API_KEY").ok();
    
    if gemini_key.is_none() && minimax_key.is_none() {
        return Err("No LLM API key set for synthesis".to_string());
    }
    
    let mut content_summary = String::new();
    for (i, page) in sources.iter().enumerate().take(10) {
        content_summary.push_str(&format!("\n\n=== Source {} ===\nTitle: {}\nURL: {}\n\nContent:\n{}", 
            i + 1, page.title, page.url, &page.markdown[..page.markdown.len().min(3000)]));
    }
    
    let prompt = format!(r#"You are a research analyst. Create a comprehensive, well-structured research report about: {}

Analyze the following source materials and create a clean, professional report with:
1. Executive Summary (2-3 paragraphs)
2. Key Findings (bullet points)
3. Technical Details
4. Useful Resources/Links

Source materials:
{}

Requirements:
- Write in professional technical documentation style
- Extract and synthesize key information
- Remove noise like navigation, ads, footers
- Format with proper markdown headings
- Include source URLs where relevant
- Do not include raw HTML or boilerplate content
- Make it readable and informative

Report:"#, topic, content_summary);
    
    // Try Gemini first
    if let Some(api_key) = gemini_key {
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={}",
            api_key
        );
        
        let body = serde_json::json!({
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192
            }
        });
        
        match client.post(&url)
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await {
                Ok(response) => {
                    if let Ok(text) = response.text().await {
                        if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&text) {
                            if let Some(text_result) = parsed["candidates"].as_array()
                                .and_then(|c| c.first())
                                .and_then(|c| c["content"]["parts"].as_array())
                                .and_then(|p| p.first())
                                .and_then(|p| p["text"].as_str()) {
                                return Ok(text_result.to_string());
                            }
                        }
                    }
                }
                Err(e) => eprintln!("  Gemini synthesis error: {}", e),
            }
    }
    
    // Try MiniMax
    if let Some(api_key) = minimax_key {
        let host = std::env::var("MINIMAX_API_HOST").unwrap_or_else(|_| "https://api.minimax.io".to_string());
        let url = format!("{}/v1/text/chatcompletion_v2?Model=abab6.5s-chat", host.trim_end_matches('/'));
        
        let body = serde_json::json!({
            "model": "abab6.5s-chat",
            "messages": [{
                "role": "user",
                "content": prompt
            }]
        });
        
        match client.post(&url)
            .header("Authorization", format!("Bearer {}", api_key))
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await {
                Ok(response) => {
                    if let Ok(text) = response.text().await {
                        if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&text) {
                            if let Some(text_result) = parsed["choices"].as_array()
                                .and_then(|c| c.first())
                                .and_then(|c| c["message"]["content"].as_str()) {
                                return Ok(text_result.to_string());
                            }
                        }
                    }
                }
                Err(e) => eprintln!("  MiniMax synthesis error: {}", e),
            }
    }
    
    Err("LLM synthesis failed".to_string())
}
