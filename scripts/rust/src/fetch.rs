use html2md::parse_html;
use regex::Regex;
use reqwest::Client;
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FetchedPage {
    pub url: String,
    pub title: String,
    pub markdown: String,
    pub byte_size: usize,
}

pub async fn fetch_url(client: &Client, url: &str, max_kb: usize) -> Result<FetchedPage, String> {
    let response = client.get(url).send().await.map_err(|e| e.to_string())?;
    
    if !response.status().is_success() {
        return Err(format!("HTTP {}", response.status()));
    }

    let html = response.text().await.map_err(|e| e.to_string())?;
    let byte_size = html.len();
    let truncated = if html.len() > max_kb * 1024 {
        html[..max_kb * 1024].to_string()
    } else {
        html.clone()
    };

    let cleaned = strip_scripts_and_styles(&truncated);
    let title = extract_title(&cleaned);
    let markdown = parse_html(&cleaned);

    Ok(FetchedPage {
        url: url.to_string(),
        title,
        markdown,
        byte_size,
    })
}

fn strip_scripts_and_styles(html: &str) -> String {
    let script_regex = Regex::new(r"(?is)<script[^>]*>.*?</script>").unwrap();
    let style_regex = Regex::new(r"(?is)<style[^>]*>.*?</style>").unwrap();
    let onload_regex = Regex::new(r#"(?is)\s+on\w+\s*=\s*["'][^"']*["']"#).unwrap();
    let noscript_regex = Regex::new(r"(?is)<noscript[^>]*>.*?</noscript>").unwrap();
    
    let cleaned = script_regex.replace_all(html, "");
    let cleaned = style_regex.replace_all(&cleaned, "");
    let cleaned = noscript_regex.replace_all(&cleaned, "");
    let cleaned = onload_regex.replace_all(&cleaned, "");
    cleaned.to_string()
}

fn extract_title(html: &str) -> String {
    let document = Html::parse_document(html);
    let title_selector = Selector::parse("title").unwrap();
    
    document
        .select(&title_selector)
        .next()
        .map(|el| el.text().collect::<String>().trim().to_string())
        .unwrap_or_else(|| "Untitled".to_string())
}
