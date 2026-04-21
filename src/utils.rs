use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;
use tokio::time::sleep;

/// Rate limiting configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitConfig {
    pub requests_per_minute: u32,
    pub burst_size: u32,
    pub retry_after_seconds: u64,
}

/// Rate limiter implementation
#[derive(Debug, Clone)]
pub struct RateLimiter {
    config: RateLimitConfig,
    request_count: u32,
    reset_time: std::time::Instant,
}

impl RateLimiter {
    pub fn new(config: RateLimitConfig) -> Self {
        Self {
            config,
            request_count: 0,
            reset_time: std::time::Instant::now(),
        }
    }

    /// Check if a request can be made
    pub async fn can_proceed(&mut self) -> bool {
        // Reset counter if time window has passed
        if self.reset_time.elapsed() >= Duration::from_secs(60) {
            self.request_count = 0;
            self.reset_time = std::time::Instant::now();
        }

        // Check if we're within burst limits
        if self.request_count < self.config.burst_size {
            self.request_count += 1;
            true
        } else {
            false
        }
    }

    /// Wait until a request can be made
    pub async fn wait_until_available(&mut self) {
        loop {
            if self.can_proceed().await {
                break;
            }
            sleep(Duration::from_secs(1)).await;
        }
    }

    /// Reset the rate limiter
    pub fn reset(&mut self) {
        self.request_count = 0;
        self.reset_time = std::time::Instant::now();
    }
}

/// HTTP client with retry logic
pub struct HttpClient {
    client: reqwest::Client,
    rate_limiter: RateLimiter,
}

impl HttpClient {
    pub fn new(rate_limit_config: RateLimitConfig) -> Result<Self> {
        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(30))
            .build()?;

        Ok(Self {
            client,
            rate_limiter: RateLimiter::new(rate_limit_config),
        })
    }

    /// GET request with retry logic
    pub async fn get(&mut self, url: &str, headers: Option<HashMap<String, String>>) -> Result<reqwest::Response> {
        self.rate_limiter.wait_until_available().await;

        let mut request = self.client.get(url);
        
        if let Some(headers) = headers {
            for (key, value) in headers {
                request = request.header(&key, &value);
            }
        }

        let response = request.send().await?;
        Ok(response)
    }

    /// POST request with retry logic
    pub async fn post(
        &mut self,
        url: &str,
        body: serde_json::Value,
        headers: Option<HashMap<String, String>>,
    ) -> Result<reqwest::Response> {
        self.rate_limiter.wait_until_available().await;

        let mut request = self.client.post(url).json(&body);
        
        if let Some(headers) = headers {
            for (key, value) in headers {
                request = request.header(&key, &value);
            }
        }

        let response = request.send().await?;
        Ok(response)
    }
}

/// Content extraction utilities
pub struct ContentExtractor;

impl ContentExtractor {
    /// Extract text from HTML content
    pub fn extract_text_from_html(html: &str) -> String {
        // Simple HTML to text extraction
        let text = html
            .replace("<br>", "\n")
            .replace("<p>", "\n")
            .replace("</p>", "\n")
            .replace("<li>", "\n• ")
            .replace("</li>", "")
            .replace("<h1>", "\n\n# ")
            .replace("</h1>", "\n")
            .replace("<h2>", "\n\n## ")
            .replace("</h2>", "\n")
            .replace("<h3>", "\n\n### ")
            .replace("</h3>", "\n")
            .replace("<code>", "`")
            .replace("</code>", "`")
            .replace("<strong>", "**")
            .replace("</strong>", "**")
            .replace("<em>", "*")
            .replace("</em>", "*")
            .replace("<", " ")
            .replace(">", " ")
            .replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"");

        // Clean up extra whitespace
        let text = text
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ");

        text
    }

    /// Clean text content
    pub fn clean_text(text: &str) -> String {
        text
            .lines()
            .map(|line| line.trim())
            .filter(|line| !line.is_empty())
            .collect::<Vec<_>>()
            .join("\n")
    }

    /// Extract metadata from HTML head
    pub fn extract_metadata(html: &str) -> HashMap<String, String> {
        let mut metadata = HashMap::new();
        
        // Simple metadata extraction
        if let Some(title) = Self::extract_meta_tag(html, "title") {
            metadata.insert("title".to_string(), title);
        }
        
        if let Some(description) = Self::extract_meta_tag(html, "description") {
            metadata.insert("description".to_string(), description);
        }
        
        if let Some(author) = Self::extract_meta_tag(html, "author") {
            metadata.insert("author".to_string(), author);
        }
        
        if let Some(keyword) = Self::extract_meta_tag(html, "keywords") {
            metadata.insert("keywords".to_string(), keyword);
        }

        metadata
    }

    fn extract_meta_tag(html: &str, name: &str) -> Option<String> {
        let pattern = format!(r#"<meta[^>]*name=["']{}["'][^>]*content=["']([^"']*)["']"#, name);
        Some(regex::Regex::new(&pattern).ok()?.captures(html)?.get(1)?.as_str().to_string())
    }
}

/// Text processing utilities
pub struct TextProcessor;

impl TextProcessor {
    /// Split text into chunks with size limits
    pub fn chunk_text(text: &str, max_size: usize) -> Vec<String> {
        if text.len() <= max_size {
            return vec![text.to_string()];
        }

        let mut chunks = Vec::new();
        let mut current_chunk = String::new();
        let sentences = Self::split_into_sentences(text);
        
        for sentence in sentences {
            if current_chunk.len() + sentence.len() + 1 <= max_size {
                if !current_chunk.is_empty() {
                    current_chunk.push(' ');
                }
                current_chunk.push_str(&sentence);
            } else {
                if !current_chunk.is_empty() {
                    chunks.push(current_chunk);
                }
                current_chunk = sentence.to_string();
            }
        }
        
        if !current_chunk.is_empty() {
            chunks.push(current_chunk);
        }
        
        chunks
    }

    /// Split text into sentences
    fn split_into_sentences(text: &str) -> Vec<String> {
        let mut sentences = Vec::new();
        let mut current_sentence = String::new();
        
        for char in text.chars() {
            current_sentence.push(char);
            
            // Simple sentence detection
            if char == '.' || char == '!' || char == '?' {
                // Look ahead to see if this is actually the end of a sentence
                if !current_sentence.trim().ends_with("Mr.") 
                    && !current_sentence.trim().ends_with("Mrs.") 
                    && !current_sentence.trim().ends_with("Dr.") 
                    && !current_sentence.trim().ends_with("Ph.D.") {
                    sentences.push(current_sentence.trim().to_string());
                    current_sentence.clear();
                    continue;
                }
            }
            
            if char == '\n' {
                if !current_sentence.trim().is_empty() {
                    sentences.push(current_sentence.trim().to_string());
                    current_sentence.clear();
                }
            }
        }
        
        if !current_sentence.trim().is_empty() {
            sentences.push(current_sentence.trim().to_string());
        }
        
        sentences
    }

    /// Calculate text relevance score
    pub fn calculate_relevance(query: &str, content: &str) -> f64 {
        let query_words: Vec<String> = query
            .to_lowercase()
            .split_whitespace()
            .map(|s| s.trim().to_string())
            .collect();
        
        let content_words: Vec<String> = content
            .to_lowercase()
            .split_whitespace()
            .map(|s| s.trim().to_string())
            .collect();

        let mut match_count = 0;
        for query_word in &query_words {
            if content_words.contains(query_word) {
                match_count += 1;
            }
        }

        let relevance = query_words.len() as f64;
        if relevance == 0.0 {
            0.0
        } else {
            match_count as f64 / relevance
        }
    }

    /// Extract key phrases from text
    pub fn extract_key_phrases(text: &str, max_phrases: usize) -> Vec<String> {
        let words: Vec<String> = text
            .split_whitespace()
            .map(|s| s.trim().to_string())
            .collect();

        let mut phrases = Vec::new();
        
        // Extract common bigrams and trigrams
        for i in 0..words.len() - 1 {
            let bigram = format!("{} {}", words[i], words[i + 1]);
            phrases.push(bigram);
            
            if i < words.len() - 2 {
                let trigram = format!("{} {} {}", words[i], words[i + 1], words[i + 2]);
                phrases.push(trigram);
            }
        }

        // Filter and sort by frequency (simplified)
        let mut phrase_counts = HashMap::new();
        for phrase in phrases {
            *phrase_counts.entry(phrase).or_insert(0) += 1;
        }

        let mut sorted_phrases: Vec<_> = phrase_counts.into_iter().collect();
        sorted_phrases.sort_by(|a, b| b.1.cmp(&a.1));

        sorted_phrases
            .into_iter()
            .take(max_phrases)
            .map(|(phrase, _)| phrase)
            .collect()
    }
}

/// Performance monitoring utilities
pub struct PerformanceMonitor {
    metrics: HashMap<String, Vec<Duration>>,
}

impl PerformanceMonitor {
    pub fn new() -> Self {
        Self {
            metrics: HashMap::new(),
        }
    }

    /// Record a metric
    pub fn record(&mut self, name: &str, duration: Duration) {
        self.metrics.entry(name.to_string())
            .or_insert_with(Vec::new)
            .push(duration);
    }

    /// Get average time for a metric
    pub fn average(&self, name: &str) -> Option<Duration> {
        self.metrics.get(name).map(|times| {
            let total: Duration = times.iter().sum();
            total / times.len() as u32
        })
    }

    /// Get metrics summary
    pub fn summary(&self) -> HashMap<String, (Duration, usize)> {
        let mut summary = HashMap::new();
        
        for (name, times) in &self.metrics {
            if let Some(avg) = self.average(name) {
                summary.insert(name.clone(), (avg, times.len()));
            }
        }
        
        summary
    }

    /// Clear all metrics
    pub fn clear(&mut self) {
        self.metrics.clear();
    }
}

/// File system utilities
pub struct FileUtils;

impl FileUtils {
    /// Ensure directory exists
    pub async fn ensure_dir(path: &std::path::Path) -> Result<()> {
        if !path.exists() {
            tokio::fs::create_dir_all(path).await?;
        }
        Ok(())
    }

    /// Read text file asynchronously
    pub async fn read_text_file(path: &std::path::Path) -> Result<String> {
        let content = tokio::fs::read_to_string(path).await?;
        Ok(content)
    }

    /// Write text file asynchronously
    pub async fn write_text_file(path: &std::path::Path, content: &str) -> Result<()> {
        if let Some(parent) = path.parent() {
            Self::ensure_dir(parent).await?;
        }
        
        tokio::fs::write(path, content).await?;
        Ok(())
    }

    /// Get file size
    pub async fn get_file_size(path: &std::path::Path) -> Result<u64> {
        let metadata = tokio::fs::metadata(path).await?;
        Ok(metadata.len())
    }

    /// List files in directory
    pub fn list_files(path: &std::path::Path, recursive: bool) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<Vec<std::path::PathBuf>>> + Send + '_>> {
        Box::pin(async move {
            let mut files = Vec::new();

            if path.is_file() {
                files.push(path.to_path_buf());
                return Ok(files);
            }

            if path.is_dir() {
                let mut entries = tokio::fs::read_dir(path).await?;

                while let Some(entry) = entries.next_entry().await? {
                    let p = entry.path();

                    if p.is_file() {
                        files.push(p);
                    } else if p.is_dir() && recursive {
                        let sub_files = Self::list_files(&p, recursive).await?;
                        files.extend(sub_files);
                    }
                }
            }

            Ok(files)
        })
    }
    }
/// Progress tracking utilities
pub struct ProgressTracker {
    current: usize,
    total: usize,
    start_time: std::time::Instant,
}

impl ProgressTracker {
    pub fn new(total: usize) -> Self {
        Self {
            current: 0,
            total,
            start_time: std::time::Instant::now(),
        }
    }

    /// Update progress
    pub fn update(&mut self, increment: usize) {
        self.current = (self.current + increment).min(self.total);
    }

    /// Get progress percentage
    pub fn percentage(&self) -> f64 {
        if self.total == 0 {
            100.0
        } else {
            (self.current as f64 / self.total as f64) * 100.0
        }
    }

    /// Get estimated time remaining
    pub fn estimated_time_remaining(&self) -> Option<Duration> {
        if self.current == 0 {
            return None;
        }

        let elapsed = self.start_time.elapsed();
        let rate = elapsed.as_secs_f64() / self.current as f64;
        let remaining = (self.total - self.current) as f64 * rate;
        
        Some(Duration::from_secs_f64(remaining))
    }

    /// Get progress summary
    pub fn summary(&self) -> String {
        format!(
            "{}/{} ({:.1}%) - ETA: {}",
            self.current,
            self.total,
            self.percentage(),
            self.estimated_time_remaining()
                .map(|eta| format!("{:.1}s", eta.as_secs_f64()))
                .unwrap_or_else(|| "N/A".to_string())
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_rate_limiter() {
        let config = RateLimitConfig {
            requests_per_minute: 10,
            burst_size: 3,
            retry_after_seconds: 1,
        };

        let mut limiter = RateLimiter::new(config);
        
        // Should be able to make 3 requests immediately
        for i in 0..3 {
            assert!(limiter.can_proceed().await);
        }
        
        // Should be blocked after burst limit
        assert!(!limiter.can_proceed().await);
    }

    #[test]
    fn test_text_chunking() {
        let long_text = "This is a long text that needs to be chunked into smaller pieces for processing. ".repeat(10);
        let chunks = TextProcessor::chunk_text(&long_text, 100);
        
        assert!(!chunks.is_empty());
        assert!(chunks.iter().all(|chunk| chunk.len() <= 100));
    }

    #[test]
    fn test_relevance_scoring() {
        let query = "machine learning";
        let content = "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.";
        let relevance = TextProcessor::calculate_relevance(query, content);
        
        assert!(relevance > 0.0);
        assert!(relevance <= 1.0);
    }
}