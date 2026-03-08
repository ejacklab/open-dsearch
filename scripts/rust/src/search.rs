use crate::FetchedPage;
use reqwest::Client;
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
}

#[derive(Deserialize)]
struct MinimaxOrganicResult {
    title: Option<String>,
    link: Option<String>,
    snippet: Option<String>,
}

pub async fn search_minimax(client: &Client, query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let api_key = crate::get_secret("minimax")?;
    let host = std::env::var("MINIMAX_API_HOST").unwrap_or_else(|_| "https://api.minimax.io".to_string());
    let url = format!("{}/v1/coding_plan/search", host.trim_end_matches('/'));
    let body = serde_json::json!({"q": query});

    let resp = client.post(&url).header("Authorization", format!("Bearer {}", api_key))
        .header("Content-Type", "application/json").header("MM-API-Source", "dsearch")
        .json(&body).send().await.map_err(|e| e.to_string())?;

    let text = resp.text().await.map_err(|e| e.to_string())?;
    let res: MinimaxSearchResponse = serde_json::from_str(&text).map_err(|e| format!("Parse error: {}", e))?;
    let mut results = Vec::new();
    for item in res.organic.unwrap_or_default().into_iter().take(limit) {
        let (t, u, s) = (item.title.unwrap_or_default(), item.link.unwrap_or_default(), item.snippet.unwrap_or_default());
        if !t.is_empty() && !u.is_empty() { results.push(SearchResult { title: t, url: u, snippet: s }); }
    }
    if results.is_empty() { return Err("No results".to_string()); }
    Ok(results)
}

pub async fn search_gemini(client: &Client, query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let api_key = crate::get_secret("gemini")?;
    let url = format!("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={}", api_key);
    let body = serde_json::json!({
        "contents": [{"role": "user", "parts": [{ "text": format!("Search for: {}", query) }]}],
        "tools": [{ "googleSearch": {} }],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1024}
    });

    let resp = client.post(&url).header("Content-Type", "application/json").json(&body).send().await.map_err(|e| e.to_string())?;
    parse_gemini_grounding(&resp.text().await.map_err(|e| e.to_string())?, query, limit)
}

fn parse_gemini_grounding(text: &str, query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let resp: GeminiResponse = serde_json::from_str(text).map_err(|e| format!("Parse error: {}", e))?;
    let chunks = resp.candidates.and_then(|c| c.into_iter().next()).and_then(|c| c.grounding_metadata).and_then(|g| g.grounding_chunks).unwrap_or_default();
    let mut results = Vec::new();
    for chunk in chunks.into_iter().take(limit) {
        if let Some(web) = chunk.web {
            let (t, u) = (web.title.unwrap_or_default(), web.uri.unwrap_or_default());
            if !t.is_empty() && !u.is_empty() {
                results.push(SearchResult { title: t, url: u, snippet: format!("Source for: {}", query) });
            }
        }
    }
    if results.is_empty() { return Err("No results".to_string()); }
    Ok(results)
}

// --- Kimi (Moonshot AI) search via chat completion with web search tool ---

#[derive(Deserialize)]
struct KimiChatResponse {
    choices: Option<Vec<KimiChoice>>,
}

#[derive(Deserialize)]
struct KimiChoice {
    finish_reason: Option<String>,
    message: Option<KimiMessage>,
}

#[derive(Deserialize, Serialize)]
struct KimiMessage {
    role: String,
    content: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    tool_calls: Option<Vec<KimiToolCall>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    tool_call_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    name: Option<String>,
}

#[derive(Deserialize, Serialize, Clone)]
struct KimiToolCall {
    id: String,
    #[serde(rename = "type")]
    tool_type: Option<String>,
    function: KimiFunction,
}

#[derive(Deserialize, Serialize, Clone)]
struct KimiFunction {
    name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    arguments: Option<String>,
}

/// Search using Kimi (Moonshot AI) chat API with web search tool enabled.
/// Kimi uses OpenAI-compatible API with tool calling for web search.
/// Requires multi-turn conversation: first call triggers tool, second call gets results.
pub async fn search_kimi(client: &Client, query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let api_key = crate::get_secret("kimi")?;
    let host = std::env::var("KIMI_API_HOST").unwrap_or_else(|_| "https://api.moonshot.ai".to_string());
    let url = format!("{}/v1/chat/completions", host.trim_end_matches('/'));

    // Step 1: Initial request with web search tool
    let messages = vec![
        KimiMessage { role: "system".to_string(), content: Some("You are a helpful search assistant. When searching, provide results with titles, URLs, and brief descriptions.".to_string()), tool_calls: None, tool_call_id: None, name: None },
        KimiMessage { role: "user".to_string(), content: Some(format!("Search the web for: {}. List the top {} most relevant sources with their titles, URLs, and brief descriptions.", query, limit)), tool_calls: None, tool_call_id: None, name: None },
    ];

    let body = serde_json::json!({
        "model": "kimi-k2-turbo-preview",
        "messages": messages,
        "temperature": 0.6,
        "tools": [{
            "type": "builtin_function",
            "function": {"name": "$web_search"}
        }]
    });

    let resp = client.post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Content-Type", "application/json")
        .json(&body)
        .send()
        .await
        .map_err(|e| e.to_string())?;

    let text = resp.text().await.map_err(|e| e.to_string())?;
    let first_response: KimiChatResponse = serde_json::from_str(&text)
        .map_err(|e| format!("Kimi parse error: {} | Response: {}", e, &text[..text.len().min(500)]))?;

    let first_choice = first_response.choices.and_then(|c| c.into_iter().next())
        .ok_or("No choices in Kimi response")?;

    // Check if we need to handle tool calls (multi-turn)
    if first_choice.finish_reason.as_deref() == Some("tool_calls") {
        // Step 2: Handle tool calls and make second request
        let assistant_message = first_choice.message.ok_or("No message in tool_calls response")?;
        let tool_calls = assistant_message.tool_calls.clone().ok_or("No tool_calls in message")?;

        // Build conversation with assistant message and tool results
        let mut messages_with_tools = vec![
            KimiMessage { role: "system".to_string(), content: Some("You are a helpful search assistant.".to_string()), tool_calls: None, tool_call_id: None, name: None },
            KimiMessage { role: "user".to_string(), content: Some(format!("Search the web for: {}. List the top {} most relevant sources with their titles, URLs, and brief descriptions.", query, limit)), tool_calls: None, tool_call_id: None, name: None },
            assistant_message,
        ];

        // Add tool results
        for tc in &tool_calls {
            if tc.function.name == "$web_search" {
                let args = tc.function.arguments.clone().unwrap_or_default();
                messages_with_tools.push(KimiMessage {
                    role: "tool".to_string(),
                    tool_call_id: Some(tc.id.clone()),
                    name: Some(tc.function.name.clone()),
                    content: Some(args),
                    tool_calls: None,
                });
            }
        }

        // Second request to get actual content
        let body2 = serde_json::json!({
            "model": "kimi-k2-turbo-preview",
            "messages": messages_with_tools,
            "temperature": 0.6
        });

        let resp2 = client.post(&url)
            .header("Authorization", format!("Bearer {}", api_key))
            .header("Content-Type", "application/json")
            .json(&body2)
            .send()
            .await
            .map_err(|e| e.to_string())?;

        let text2 = resp2.text().await.map_err(|e| e.to_string())?;
        parse_kimi_content(&text2, query, limit)
    } else {
        // No tool calls, parse content directly
        parse_kimi_content(&text, query, limit)
    }
}

fn parse_kimi_content(text: &str, query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let parsed: serde_json::Value = serde_json::from_str(text)
        .map_err(|e| format!("Kimi content parse error: {}", e))?;

    let content = parsed["choices"][0]["message"]["content"]
        .as_str()
        .ok_or("No content in Kimi response")?;

    // Extract markdown links as search results
    let mut results = Vec::new();
    let link_regex = regex::Regex::new(r"\[([^\]]+)\]\((https?://[^)]+)\)").unwrap();

    for cap in link_regex.captures_iter(content).take(limit) {
        let title = cap.get(1).map(|m| m.as_str().to_string()).unwrap_or_default();
        let url = cap.get(2).map(|m| m.as_str().to_string()).unwrap_or_default();
        if !title.is_empty() && !url.is_empty() {
            results.push(SearchResult {
                title,
                url,
                snippet: format!("Kimi result for: {}", query),
            });
        }
    }

    if results.is_empty() {
        // Fallback: try to extract URLs from plain text
        let url_regex = regex::Regex::new(r"https?://[^\s\)\]>]+").unwrap();
        for cap in url_regex.captures_iter(content).take(limit) {
            let url = cap.get(0).map(|m| m.as_str().to_string()).unwrap_or_default();
            if !url.is_empty() {
                results.push(SearchResult {
                    title: format!("Source: {}", &url[..url.len().min(50)]),
                    url,
                    snippet: format!("Kimi result for: {}", query),
                });
            }
        }
    }

    if results.is_empty() {
        return Err("No results from Kimi".to_string());
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
        if let Some(ref d) = self.allowed_domains { args.extend([ "--allowed-domains".into(), d.clone() ]); }
        if let Some(ref d) = self.excluded_domains { args.extend([ "--excluded-domains".into(), d.clone() ]); }
        if self.enable_image_understanding { args.push("--enable-image-understanding".into()); }
        if let Some(ref h) = self.allowed_handles { args.extend([ "--allowed-handles".into(), h.clone() ]); }
        if let Some(ref h) = self.excluded_handles { args.extend([ "--excluded-handles".into(), h.clone() ]); }
        if let Some(ref f) = self.from_date { args.extend([ "--from-date".into(), f.clone() ]); }
        if let Some(ref t) = self.to_date { args.extend([ "--to-date".into(), t.clone() ]); }
        if self.enable_video_understanding { args.push("--enable-video-understanding".into()); }
        if let Some(ref m) = self.model { args.extend([ "--model".into(), m.clone() ]); }
        if let Some(t) = self.timeout { args.extend([ "--timeout".into(), t.to_string() ]); }
        args
    }
}

pub async fn search_xai_with_params(query: &str, limit: usize, params: XaiSearchParams) -> Result<Vec<SearchResult>, String> {
    let _key = crate::get_secret("xai")?;
    let script = if std::path::Path::new("scripts/xai_search.py").exists() { 
        "scripts/xai_search.py" 
    } else if std::path::Path::new("xai_search.py").exists() {
        "xai_search.py"
    } else { 
        ".agents/skills/dsearch/scripts/xai_search.py" 
    };
    let mut args = vec![script.to_string(), query.to_string(), "--limit".to_string(), limit.to_string()];
    args.extend(params.to_args());

    let output = tokio::task::spawn_blocking(move || { std::process::Command::new("python3").args(&args).output() }).await
        .map_err(|e| e.to_string())?.map_err(|e| e.to_string())?;

    if !output.status.success() { return Err(format!("xAI failed: {}", String::from_utf8_lossy(&output.stderr))); }
    let stdout = String::from_utf8_lossy(&output.stdout);
    let json_start = stdout.find('[').unwrap_or(0);
    serde_json::from_str(&stdout[json_start..]).map_err(|e| format!("JSON error: {}", e))
}

pub async fn search_xai(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    search_xai_with_params(query, limit, XaiSearchParams::default()).await
}

pub async fn xai_x_search_with_params(query: &str, limit: usize, params: XaiSearchParams) -> Result<Vec<SearchResult>, String> {
    let _key = crate::get_secret("xai")?;
    let script = if std::path::Path::new("scripts/xai_search.py").exists() { 
        "scripts/xai_search.py" 
    } else if std::path::Path::new("xai_search.py").exists() {
        "xai_search.py"
    } else { 
        ".agents/skills/dsearch/scripts/xai_search.py" 
    };
    let mut args = vec![script.to_string(), query.to_string(), "--limit".to_string(), limit.to_string(), "--x-search".to_string()];
    args.extend(params.to_args());

    let output = tokio::task::spawn_blocking(move || { std::process::Command::new("python3").args(&args).output() }).await
        .map_err(|e| e.to_string())?.map_err(|e| e.to_string())?;

    if !output.status.success() { return Err(format!("xAI X failed: {}", String::from_utf8_lossy(&output.stderr))); }
    let stdout = String::from_utf8_lossy(&output.stdout);
    let json_start = stdout.find('[').unwrap_or(0);
    serde_json::from_str(&stdout[json_start..]).map_err(|e| format!("JSON error: {}", e))
}

pub async fn xai_x_search(query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    xai_x_search_with_params(query, limit, XaiSearchParams::default()).await
}

pub async fn search_with_fallback(client: &Client, query: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let timeout = std::time::Duration::from_secs(66 * 60);
    let (g_key, m_key, k_key) = (crate::get_secret("gemini").is_ok(), crate::get_secret("minimax").is_ok(), crate::get_secret("kimi").is_ok());
    if !g_key && !m_key && !k_key { return Err("No keys".to_string()); }

    let mut all_results = Vec::new();
    if g_key || m_key || k_key {
        all_results.extend(perform_fallback_search(client, query, limit, timeout, g_key, m_key, k_key).await);
    }
    // xAI disabled

    if all_results.is_empty() { return Err("No results".to_string()); }
    Ok(all_results)
}

async fn perform_fallback_search(client: &Client, query: &str, limit: usize, timeout: std::time::Duration, g_key: bool, m_key: bool, k_key: bool) -> Vec<SearchResult> {
    let mut results = Vec::new();
    if g_key && m_key && k_key {
        if let Ok((g_res, m_res, k_res)) = tokio::time::timeout(timeout, async {
            tokio::join!(
                search_gemini(client, query, limit),
                search_minimax(client, query, limit),
                search_kimi(client, query, limit)
            )
        }).await {
            if let Ok(res) = g_res { results.extend(res); }
            if let Ok(res) = m_res { results.extend(res); }
            if let Ok(res) = k_res { results.extend(res); }
        }
    } else if g_key && m_key {
        if let Ok((g_res, m_res)) = tokio::time::timeout(timeout, async { tokio::join!(search_gemini(client, query, limit), search_minimax(client, query, limit)) }).await {
            if let Ok(res) = g_res { results.extend(res); }
            if let Ok(res) = m_res { results.extend(res); }
        }
    } else if g_key && k_key {
        if let Ok((g_res, k_res)) = tokio::time::timeout(timeout, async { tokio::join!(search_gemini(client, query, limit), search_kimi(client, query, limit)) }).await {
            if let Ok(res) = g_res { results.extend(res); }
            if let Ok(res) = k_res { results.extend(res); }
        }
    } else if m_key && k_key {
        if let Ok((m_res, k_res)) = tokio::time::timeout(timeout, async { tokio::join!(search_minimax(client, query, limit), search_kimi(client, query, limit)) }).await {
            if let Ok(res) = m_res { results.extend(res); }
            if let Ok(res) = k_res { results.extend(res); }
        }
    } else if g_key {
        if let Ok(Ok(res)) = tokio::time::timeout(timeout, search_gemini(client, query, limit)).await { results.extend(res); }
    } else if m_key {
        if let Ok(Ok(res)) = tokio::time::timeout(timeout, search_minimax(client, query, limit)).await { results.extend(res); }
    } else if k_key {
        if let Ok(Ok(res)) = tokio::time::timeout(timeout, search_kimi(client, query, limit)).await { results.extend(res); }
    }
    results
}

pub fn expand_queries(topic: &str) -> Vec<String> {
    expand_queries_with_sources(topic, 8, 6, 6)
}

pub fn expand_queries_with_sources(topic: &str, google: usize, github: usize, official: usize) -> Vec<String> {
    let mut queries = Vec::new();
    for i in 0..google { queries.push(match i {
        0 => format!("{}", topic), 1 => format!("{} tutorial", topic), 2 => format!("{} guide", topic),
        3 => format!("{} explained", topic), 4 => format!("{} basics", topic), 5 => format!("{} introduction", topic),
        6 => format!("{} overview", topic), 7 => format!("{} deep dive", topic), _ => format!("{} {}", topic, i),
    }); }
    for i in 0..github { queries.push(match i {
        0 => format!("{} site:github.com stars:>1000", topic), 1 => format!("{} github repository", topic),
        2 => format!("{} github stars", topic), 3 => format!("{} site:github.com", topic),
        4 => format!("{} github stars:>500", topic), 5 => format!("{} popular github", topic), _ => format!("{} github {}", topic, i),
    }); }
    let official_sources = vec![
        format!("{} site:anthropic.com", topic), format!("{} site:openai.com", topic),
        format!("{} site:github.com", topic), format!("{} site:grokipedia.com", topic),
        format!("{} documentation", topic), format!("{} official website", topic),
    ];
    for i in 0..official {
        if i < official_sources.len() { queries.push(official_sources[i].clone()); }
        else { queries.push(format!("{} official {}", topic, i)); }
    }
    if queries.is_empty() { queries = vec![
        format!("{} official documentation", topic), format!("{} engineering blog", topic),
        format!("{} github repository", topic), format!("{} tutorial guide", topic), format!("{} architecture deep dive", topic),
    ]; }
    queries
}

pub async fn synthesize_with_llm(client: &Client, topic: &str, sources: Vec<FetchedPage>) -> Result<String, String> {
    let (g_key, m_key) = (crate::get_secret("gemini").ok(), crate::get_secret("minimax").ok());
    if g_key.is_none() && m_key.is_none() { return Err("No LLM keys".to_string()); }
    
    let mut content_summary = String::new();
    for (i, page) in sources.iter().enumerate().take(10) {
        content_summary.push_str(&format!("\n\n=== Source {} ===\nTitle: {}\nURL: {}\n\nContent:\n{}", 
            i + 1, page.title, page.url, &page.markdown[..page.markdown.len().min(3000)]));
    }
    
    let prompt = format!(r#"You are a research analyst. Create a comprehensive, well-structured research report about: {}
Source materials: {}
Report:"#, topic, content_summary);
    
    if let Some(api_key) = g_key {
        if let Ok(res) = synthesize_gemini(client, &prompt, &api_key).await { return Ok(res); }
    }
    if let Some(api_key) = m_key {
        if let Ok(res) = synthesize_minimax(client, &prompt, &api_key).await { return Ok(res); }
    }
    Err("LLM synthesis failed".to_string())
}

async fn synthesize_gemini(client: &Client, prompt: &str, api_key: &str) -> Result<String, String> {
    let url = format!("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={}", api_key);
    let body = serde_json::json!({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}});
    let resp = client.post(&url).header("Content-Type", "application/json").json(&body).send().await.map_err(|e| e.to_string())?;
    let parsed: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    parsed["candidates"].as_array().and_then(|c| c.first()).and_then(|c| c["content"]["parts"].as_array()).and_then(|p| p.first()).and_then(|p| p["text"].as_str()).map(|s| s.to_string()).ok_or("Gemini parse error".to_string())
}

async fn synthesize_minimax(client: &Client, prompt: &str, api_key: &str) -> Result<String, String> {
    let host = std::env::var("MINIMAX_API_HOST").unwrap_or_else(|_| "https://api.minimax.io".to_string());
    let url = format!("{}/v1/text/chatcompletion_v2?Model=abab6.5s-chat", host.trim_end_matches('/'));
    let body = serde_json::json!({"model": "abab6.5s-chat", "messages": [{"role": "user", "content": prompt}]});
    let resp = client.post(&url).header("Authorization", format!("Bearer {}", api_key)).header("Content-Type", "application/json").json(&body).send().await.map_err(|e| e.to_string())?;
    let parsed: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    parsed["choices"].as_array().and_then(|c| c.first()).and_then(|c| c["message"]["content"].as_str()).map(|s| s.to_string()).ok_or("MiniMax parse error".to_string())
}

#[cfg(test)]
fn parse_minimax_response(text: &str, limit: usize) -> Result<Vec<SearchResult>, String> {
    let res: MinimaxSearchResponse = serde_json::from_str(text).map_err(|e| format!("Parse error: {}", e))?;
    let mut results = Vec::new();
    for item in res.organic.unwrap_or_default().into_iter().take(limit) {
        let (t, u, s) = (item.title.unwrap_or_default(), item.link.unwrap_or_default(), item.snippet.unwrap_or_default());
        if !t.is_empty() && !u.is_empty() { results.push(SearchResult { title: t, url: u, snippet: s }); }
    }
    if results.is_empty() { return Err("No results".to_string()); }
    Ok(results)
}

#[cfg(test)]
mod tests {
    use super::*;

    // --- Gemini response parsing ---

    #[test]
    fn test_gemini_parses_valid_response() {
        let json = r#"{
            "candidates": [{
                "groundingMetadata": {
                    "groundingChunks": [
                        {"web": {"uri": "https://tokio.rs", "title": "Tokio Docs"}},
                        {"web": {"uri": "https://docs.rs/tokio", "title": "tokio crate"}}
                    ]
                }
            }]
        }"#;
        let results = parse_gemini_grounding(json, "tokio async", 10).unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].url, "https://tokio.rs");
        assert_eq!(results[0].title, "Tokio Docs");
        assert!(results[0].snippet.contains("tokio async"));
    }

    #[test]
    fn test_gemini_respects_limit() {
        let json = r#"{
            "candidates": [{
                "groundingMetadata": {
                    "groundingChunks": [
                        {"web": {"uri": "https://a.com", "title": "A"}},
                        {"web": {"uri": "https://b.com", "title": "B"}},
                        {"web": {"uri": "https://c.com", "title": "C"}}
                    ]
                }
            }]
        }"#;
        let results = parse_gemini_grounding(json, "query", 2).unwrap();
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_gemini_skips_empty_title_or_url() {
        let json = r#"{
            "candidates": [{
                "groundingMetadata": {
                    "groundingChunks": [
                        {"web": {"uri": "", "title": "No URL"}},
                        {"web": {"uri": "https://valid.com", "title": ""}},
                        {"web": {"uri": "https://good.com", "title": "Good"}}
                    ]
                }
            }]
        }"#;
        let results = parse_gemini_grounding(json, "query", 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].url, "https://good.com");
    }

    #[test]
    fn test_gemini_empty_chunks_returns_err() {
        let json = r#"{"candidates": [{"groundingMetadata": {"groundingChunks": []}}]}"#;
        assert!(parse_gemini_grounding(json, "query", 10).is_err());
    }

    #[test]
    fn test_gemini_missing_candidates_returns_err() {
        let json = r#"{"candidates": null}"#;
        assert!(parse_gemini_grounding(json, "query", 10).is_err());
    }

    // --- MiniMax response parsing ---

    #[test]
    fn test_minimax_parses_valid_response() {
        let json = r#"{
            "organic": [
                {"title": "Rust Book", "link": "https://doc.rust-lang.org", "snippet": "The Rust Programming Language"},
                {"title": "Rustonomicon", "link": "https://doc.rust-lang.org/nomicon", "snippet": "Advanced Rust"}
            ]
        }"#;
        let results = parse_minimax_response(json, 10).unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].title, "Rust Book");
        assert_eq!(results[1].url, "https://doc.rust-lang.org/nomicon");
    }

    #[test]
    fn test_minimax_respects_limit() {
        let json = r#"{
            "organic": [
                {"title": "A", "link": "https://a.com", "snippet": ""},
                {"title": "B", "link": "https://b.com", "snippet": ""},
                {"title": "C", "link": "https://c.com", "snippet": ""}
            ]
        }"#;
        let results = parse_minimax_response(json, 2).unwrap();
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_minimax_skips_missing_title_or_url() {
        let json = r#"{
            "organic": [
                {"title": "", "link": "https://no-title.com", "snippet": ""},
                {"title": "No URL", "link": "", "snippet": ""},
                {"title": "Good", "link": "https://good.com", "snippet": "snippet"}
            ]
        }"#;
        let results = parse_minimax_response(json, 10).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].url, "https://good.com");
    }

    #[test]
    fn test_minimax_empty_organic_returns_err() {
        let json = r#"{"organic": []}"#;
        assert!(parse_minimax_response(json, 10).is_err());
    }

    // --- xAI JSON passthrough parsing ---

    #[test]
    fn test_xai_json_parses_result_array() {
        let json = r#"[
            {"title": "xAI Blog", "url": "https://x.ai/blog", "snippet": "Latest from xAI"},
            {"title": "Grok API", "url": "https://x.ai/api", "snippet": "API docs"}
        ]"#;
        let results: Vec<SearchResult> = serde_json::from_str(json).unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].title, "xAI Blog");
        assert_eq!(results[1].snippet, "API docs");
    }

    #[test]
    fn test_xai_json_with_prefix_noise() {
        // xAI Python script may emit log lines before the JSON array
        let stdout = "Searching...\nFound results:\n[{\"title\":\"T\",\"url\":\"https://t.com\",\"snippet\":\"s\"}]";
        let json_start = stdout.find('[').unwrap_or(0);
        let results: Vec<SearchResult> = serde_json::from_str(&stdout[json_start..]).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].url, "https://t.com");
    }

    // --- XaiSearchParams args construction ---

    #[test]
    fn test_xai_params_empty_produces_no_args() {
        let args = XaiSearchParams::default().to_args();
        assert!(args.is_empty());
    }

    #[test]
    fn test_xai_params_allowed_domains() {
        let p = XaiSearchParams { allowed_domains: Some("tokio.rs,docs.rs".into()), ..Default::default() };
        let args = p.to_args();
        assert!(args.contains(&"--allowed-domains".to_string()));
        assert!(args.contains(&"tokio.rs,docs.rs".to_string()));
    }

    #[test]
    fn test_xai_params_x_search_flag_not_in_params() {
        // --x-search is added by xai_x_search_with_params, NOT via XaiSearchParams
        let args = XaiSearchParams::default().to_args();
        assert!(!args.contains(&"--x-search".to_string()));
    }

    // --- Kimi Integration Tests (require KIMI_API_KEY in GCSM or env) ---

    #[test]
    #[ignore = "Requires KIMI_API_KEY in GCP Secret Manager or environment"]
    fn test_kimi_search_live() {
        // Integration test - run with: cargo test test_kimi_search_live -- --ignored --nocapture
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let key = crate::get_secret("kimi").expect("KIMI_API_KEY not found in GCSM or env");
            assert!(!key.is_empty(), "KIMI_API_KEY is empty");

            let client = Client::builder()
                .user_agent("dsearch-test")
                .timeout(std::time::Duration::from_secs(60))
                .build()
                .unwrap();

            let results = search_kimi(&client, "Moonshot AI Kimi", 3)
                .await
                .expect("Kimi search failed");

            println!("[kimi_live] Got {} results:", results.len());
            for (i, r) in results.iter().enumerate() {
                println!("  {}. {} -> {}", i + 1, r.title, r.url);
            }

            assert!(!results.is_empty(), "Expected at least one result");
        });
    }

    #[test]
    fn test_kimi_key_available() {
        // Quick check if KIMI_API_KEY is available (doesn't fail test, just reports)
        match crate::get_secret("kimi") {
            Ok(key) => {
                let masked = if key.len() > 8 {
                    format!("{}...{}", &key[..4], &key[key.len()-4..])
                } else {
                    "***".to_string()
                };
                println!("[kimi_key] ✓ KIMI_API_KEY available: {}", masked);
            }
            Err(e) => {
                println!("[kimi_key] ✗ KIMI_API_KEY not available: {}", e);
                println!("[kimi_key] To add: gcloud secrets create KIMI_API_KEY --project=771559838251 --data-file=- <<< $YOUR_KEY");
            }
        }
        // Always pass - this is just informational
    }
}
