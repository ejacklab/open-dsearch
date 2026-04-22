use anyhow::Result;
use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use reqwest::Client;
use std::time::Duration;
use uuid::Uuid;
use chrono::Utc;

// ── Configuration types ──────────────────────────────────────────────

/// Main configuration structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub models: ModelsConfig,
    pub storage: StorageConfig,
    pub skills: SkillsConfig,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            models: ModelsConfig {
                gemini: Some(GeminiConfig {
                    api_key: String::new(),
                    model: "gemini-2.0-flash".into(),
                    base_url: "https://generativelanguage.googleapis.com".into(),
                    max_tokens: 8192,
                    temperature: 0.7,
                    timeout: 30,
                }),
                xai: Some(XaiConfig {
                    api_key: String::new(),
                    model: "grok-beta".into(),
                    base_url: "https://api.x.ai".into(),
                    max_tokens: 4096,
                    temperature: 0.7,
                    timeout: 30,
                }),
                minimax: Some(MiniMaxConfig {
                    api_key: String::new(),
                    model: "abab6.5-chat".into(),
                    base_url: "https://api.minimax.chat".into(),
                    max_tokens: 4096,
                    temperature: 0.7,
                    timeout: 30,
                }),
            },
            storage: StorageConfig {
                enabled: false,
                vector_db_path: std::path::PathBuf::from("./data"),
                max_memory_mb: 1024,
                sessions_path: std::path::PathBuf::from("./sessions"),
            },
            skills: SkillsConfig {
                skills_path: std::path::PathBuf::from("./skills"),
                auto_load: true,
            },
        }
    }
}

/// Model configurations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelsConfig {
    pub gemini: Option<GeminiConfig>,
    pub xai: Option<XaiConfig>,
    pub minimax: Option<MiniMaxConfig>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeminiConfig {
    pub api_key: String,
    pub model: String,
    pub base_url: String,
    pub max_tokens: usize,
    pub temperature: f64,
    pub timeout: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XaiConfig {
    pub api_key: String,
    pub model: String,
    pub base_url: String,
    pub max_tokens: usize,
    pub temperature: f64,
    pub timeout: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxConfig {
    pub api_key: String,
    pub model: String,
    pub base_url: String,
    pub max_tokens: usize,
    pub temperature: f64,
    pub timeout: u64,
}

/// Storage configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageConfig {
    pub enabled: bool,
    pub vector_db_path: std::path::PathBuf,
    pub max_memory_mb: usize,
    pub sessions_path: std::path::PathBuf,
}

/// Skills configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillsConfig {
    pub skills_path: std::path::PathBuf,
    pub auto_load: bool,
}

// ── Model registry ───────────────────────────────────────────────────

/// Model registry for managing multiple AI model clients
#[derive(Debug)]
pub struct ModelRegistry {
    models: HashMap<String, Box<dyn ModelClient>>,
}

impl ModelRegistry {
    pub fn new(config: &Config) -> Result<Self> {
        let mut models: HashMap<String, Box<dyn ModelClient>> = HashMap::new();

        if let Some(ref cfg) = config.models.gemini {
            if !cfg.api_key.is_empty() {
                models.insert("gemini".to_string(), Box::new(GeminiClient::new(cfg)?));
            }
        }
        if let Some(ref cfg) = config.models.xai {
            if !cfg.api_key.is_empty() {
                models.insert("xai".to_string(), Box::new(XaiClient::new(cfg)?));
            }
        }
        if let Some(ref cfg) = config.models.minimax {
            if !cfg.api_key.is_empty() {
                models.insert("minimax".to_string(), Box::new(MiniMaxClient::new(cfg)?));
            }
        }

        Ok(Self { models })
    }

    pub fn get(&self, model_name: &str) -> Option<&dyn ModelClient> {
        self.models.get(model_name).map(|c| c.as_ref())
    }

    pub fn list_available(&self) -> Vec<String> {
        self.models.keys().cloned().collect()
    }
}

/// Trait for AI model clients
#[async_trait::async_trait]
pub trait ModelClient: Send + Sync + std::fmt::Debug {
    fn name(&self) -> &str;
    async fn search(&self, query: &str) -> Result<ModelSearchResult>;
    async fn generate(&self, prompt: &str) -> Result<String>;
    async fn analyze(&self, text: &str) -> Result<String>;
}

/// Search result from a single model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelSearchResult {
    pub results: Vec<ResearchItem>,
    pub total_results: Option<usize>,
    pub query: String,
    pub model: String,
}

/// Individual search item from a model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResearchItem {
    pub id: String,
    pub title: String,
    pub content: String,
    pub url: Option<String>,
    pub source: String,
    pub relevance: f64,
    pub published_at: Option<String>,
    pub metadata: serde_json::Value,
}

// ── Gemini client (real implementation) ─────────────────────────────

#[derive(Debug)]
pub struct GeminiClient {
    config: GeminiConfig,
    client: Client,
}

impl GeminiClient {
    pub fn new(config: &GeminiConfig) -> Result<Self> {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout))
            .build()?;
            
        Ok(Self {
            config: config.clone(),
            client,
        })
    }

    /// Generate content using Gemini's generateContent API
    async fn generate_content(&self, prompt: &str) -> Result<GeminiResponse> {
        let url = format!("{}{}:generateContent", self.config.base_url, self.config.model);
        
        let request = GeminiGenerateRequest {
            contents: vec![Content {
                role: "user".to_string(),
                parts: vec![Part {
                    text: Some(prompt.to_string()),
                    file_data: None,
                }],
            }],
            generation_config: Some(GenerationConfig {
                temperature: Some(self.config.temperature),
                top_p: Some(0.95),
                top_k: Some(40),
                max_output_tokens: Some(self.config.max_tokens as i32),
                stop_sequences: None,
            }),
            safety_settings: None,
        };

        let response = self.client
            .post(&url)
            .header("Content-Type", "application/json")
            .header("x-goog-api-key", &self.config.api_key)
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow::anyhow!("Gemini API error: {}", error_text));
        }

        let gemini_response: GeminiResponse = response.json().await?;
        Ok(gemini_response)
    }

    /// Extract text from Gemini response
    fn extract_text_from_response(&self, response: GeminiResponse) -> Result<String> {
        if let Some(candidate) = response.candidates.first() {
            if let Some(content) = candidate.content.as_ref() {
                if let Some(part) = content.parts.first() {
                    return Ok(part.text.clone().unwrap_or_default());
                }
            }
        }
        
        // If content is blocked or empty, return an informative message
        if let Some(candidate) = response.candidates.first() {
            if let Some(finish_reason) = &candidate.finish_reason {
                match finish_reason.as_str() {
                    "SAFETY" => return Err(anyhow::anyhow!("Content blocked by safety filters")),
                    "RECITATION" => return Err(anyhow::anyhow!("Content blocked due to recitation policy")),
                    "OTHER" => return Err(anyhow::anyhow!("Content blocked for other reasons")),
                    _ => {}
                }
            }
        }
        
        Ok("No content generated".to_string())
    }

    async fn internal_search(&self, query: &str) -> Result<ModelSearchResult> {
        tracing::info!("Searching with Gemini for: {}", query);

        // Create a search-specific prompt
        let search_prompt = format!(
            "You are a research assistant. Search the internet for information about '{}' and provide a comprehensive response.
            
            Format your response as a JSON object with the following structure:
            {{
                \"results\": [
                    {{
                        \"title\": \"Title of the result\",
                        \"content\": \"Brief summary or key information (2-3 sentences)\",
                        \"relevance\": 0.9,
                        \"url\": \"https://example.com\",
                        \"published_at\": \"2024-01-01\",
                        \"metadata\": {{}}
                    }}
                ]
            }}

            Focus on accuracy, relevance, and provide specific information about the topic. If you cannot find specific information, acknowledge this limitation and provide what relevant information you can.",
            query
        );

        let response = self.generate_content(&search_prompt).await?;
        let text_response = self.extract_text_from_response(response)?;
        
        // Try to parse JSON response, fall back to text parsing
        let search_items = if let Ok(parsed) = serde_json::from_str::<GeminiSearchResponse>(&text_response) {
            // Successfully parsed JSON response
            parsed.results.into_iter().map(|item| ResearchItem {
                id: format!("gemini_{}", Uuid::new_v4()),
                title: item.title,
                content: item.content,
                url: item.url,
                source: "gemini".to_string(),
                relevance: item.relevance,
                published_at: item.published_at,
                metadata: serde_json::json!({}),
            }).collect()
        } else {
            // Fallback: treat as general text and create a research result
            let content = if text_response.len() > 500 {
                format!("{}...", &text_response[..500])
            } else {
                text_response
            };

            vec![ResearchItem {
                id: format!("gemini_{}", Uuid::new_v4()),
                title: format!("Research on {}", query),
                content,
                url: None,
                source: "gemini".to_string(),
                relevance: 0.8,
                published_at: Some(Utc::now().to_rfc3339()),
                metadata: serde_json::json!({"fallback": true}),
            }]
        };

        Ok(ModelSearchResult {
            total_results: Some(search_items.len()),
            results: search_items,
            query: query.to_string(),
            model: "gemini".to_string(),
        })
    }

    async fn internal_generate(&self, prompt: &str) -> Result<String> {
        tracing::info!("Generating content with Gemini for prompt: {}", prompt);
        
        let response = self.generate_content(prompt).await?;
        let text = self.extract_text_from_response(response)?;
        
        Ok(text)
    }

    async fn internal_analyze(&self, text: &str) -> Result<String> {
        tracing::info!("Analyzing text with Gemini (length: {} chars)", text.len());
        
        let analysis_prompt = format!(
            "Analyze the following text and provide insights, key points, and a summary:
            
            Text to analyze:
            {}
            
            Please provide:
            1. A brief summary (1-2 sentences)
            2. Key insights or main points
            3. Any notable observations or analysis
            4. Overall assessment
            
            Format your response in a clear, structured way.",
            text
        );

        let response = self.generate_content(&analysis_prompt).await?;
        let analysis = self.extract_text_from_response(response)?;
        
        Ok(analysis)
    }
}

#[async_trait::async_trait]
impl ModelClient for GeminiClient {
    fn name(&self) -> &str {
        "Gemini"
    }

    async fn search(&self, query: &str) -> Result<ModelSearchResult> {
        self.internal_search(query).await
    }

    async fn generate(&self, prompt: &str) -> Result<String> {
        self.internal_generate(prompt).await
    }

    async fn analyze(&self, text: &str) -> Result<String> {
        self.internal_analyze(text).await
    }
}

// ── xAI client (real implementation) ───────────────────────────────

#[derive(Debug)]
pub struct XaiClient {
    config: XaiConfig,
    client: Client,
}

impl XaiClient {
    pub fn new(config: &XaiConfig) -> Result<Self> {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout))
            .build()?;
            
        Ok(Self {
            config: config.clone(),
            client,
        })
    }

    async fn internal_search(&self, query: &str) -> Result<ModelSearchResult> {
        tracing::info!("Searching with xAI for: {}", query);

        let url = format!("{}/v1/chat/completions", self.config.base_url);
        
        let request = XaiRequest {
            model: self.config.model.clone(),
            messages: vec![XaiMessage {
                role: "user".to_string(),
                content: format!(
                    "You are a research assistant. Search the internet for information about '{}' and provide a comprehensive response.
                    
                    Format your response as a JSON object with the following structure:
                    {{
                        \"results\": [
                            {{
                                \"title\": \"Title of the result\",
                                \"content\": \"Brief summary or key information (2-3 sentences)\",
                                \"relevance\": 0.9,
                                \"url\": \"https://example.com\",
                                \"published_at\": \"2024-01-01\",
                                \"metadata\": {{}}
                            }}
                        ]
                    }}

                    Focus on accuracy, relevance, and provide specific information about the topic. If you cannot find specific information, acknowledge this limitation and provide what relevant information you can.

                    Context: The user is asking about: {}",
                    query, query
                ),
            }],
            max_tokens: self.config.max_tokens,
            temperature: self.config.temperature,
        };

        let response = self.client
            .post(&url)
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow::anyhow!("xAI API error: {}", error_text));
        }

        let xai_response: XaiResponse = response.json().await?;
        let text_response = xai_response.choices.first().and_then(|c| c.message.content.clone()).unwrap_or_default();
        
        // Try to parse JSON response, fall back to text parsing
        let search_items = if let Ok(parsed) = serde_json::from_str::<XaiSearchResponse>(&text_response) {
            parsed.results.into_iter().map(|item| ResearchItem {
                id: format!("xai_{}", Uuid::new_v4()),
                title: item.title,
                content: item.content,
                url: item.url,
                source: "xai".to_string(),
                relevance: item.relevance,
                published_at: item.published_at,
                metadata: serde_json::json!({}),
            }).collect()
        } else {
            // Fallback: treat as general text and create a research result
            let content = if text_response.len() > 500 {
                format!("{}...", &text_response[..500])
            } else {
                text_response
            };

            vec![ResearchItem {
                id: format!("xai_{}", Uuid::new_v4()),
                title: format!("Research on {}", query),
                content,
                url: None,
                source: "xai".to_string(),
                relevance: 0.85,
                published_at: Some(Utc::now().to_rfc3339()),
                metadata: serde_json::json!({"fallback": true}),
            }]
        };

        Ok(ModelSearchResult {
            total_results: Some(search_items.len()),
            results: search_items,
            query: query.to_string(),
            model: "xai".to_string(),
        })
    }

    async fn internal_generate(&self, prompt: &str) -> Result<String> {
        tracing::info!("Generating content with xAI for prompt: {}", prompt);
        
        let request = XaiRequest {
            model: self.config.model.clone(),
            messages: vec![XaiMessage {
                role: "user".to_string(),
                content: prompt.to_string(),
            }],
            max_tokens: self.config.max_tokens,
            temperature: self.config.temperature,
        };

        let response = self.client
            .post(&format!("{}/v1/chat/completions", self.config.base_url))
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow::anyhow!("xAI API error: {}", error_text));
        }

        let xai_response: XaiResponse = response.json().await?;
        Ok(xai_response.choices.first().and_then(|c| c.message.content.clone()).unwrap_or_default())
    }

    async fn internal_analyze(&self, text: &str) -> Result<String> {
        tracing::info!("Analyzing text with xAI (length: {} chars)", text.len());
        
        let request = XaiRequest {
            model: self.config.model.clone(),
            messages: vec![XaiMessage {
                role: "user".to_string(),
                content: format!(
                    "Analyze the following text and provide insights, key points, and a summary:
                    
                    Text to analyze:
                    {}
                    
                    Please provide:
                    1. A brief summary (1-2 sentences)
                    2. Key insights or main points
                    3. Any notable observations or analysis
                    4. Overall assessment
                    
                    Format your response in a clear, structured way.",
                    text
                ),
            }],
            max_tokens: self.config.max_tokens,
            temperature: self.config.temperature,
        };

        let response = self.client
            .post(&format!("{}/v1/chat/completions", self.config.base_url))
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow::anyhow!("xAI API error: {}", error_text));
        }

        let xai_response: XaiResponse = response.json().await?;
        Ok(xai_response.choices.first().and_then(|c| c.message.content.clone()).unwrap_or_default())
    }
}

#[async_trait::async_trait]
impl ModelClient for XaiClient {
    fn name(&self) -> &str {
        "xAI"
    }

    async fn search(&self, query: &str) -> Result<ModelSearchResult> {
        self.internal_search(query).await
    }

    async fn generate(&self, prompt: &str) -> Result<String> {
        self.internal_generate(prompt).await
    }

    async fn analyze(&self, text: &str) -> Result<String> {
        self.internal_analyze(text).await
    }
}

// ── MiniMax client (real implementation) ───────────────────────────

#[derive(Debug)]
pub struct MiniMaxClient {
    config: MiniMaxConfig,
    client: Client,
}

impl MiniMaxClient {
    pub fn new(config: &MiniMaxConfig) -> Result<Self> {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout))
            .build()?;
            
        Ok(Self {
            config: config.clone(),
            client,
        })
    }

    async fn internal_search(&self, query: &str) -> Result<ModelSearchResult> {
        tracing::info!("Searching with MiniMax for: {}", query);

        let url = format!("{}/v1/text/chatcompletion", self.config.base_url);
        
        let request = MiniMaxRequest {
            model: self.config.model.clone(),
            messages: vec![MiniMaxMessage {
                role: "user".to_string(),
                content: format!(
                    "You are a research assistant. Search the internet for information about '{}' and provide a comprehensive response.
                    
                    Format your response as a JSON object with the following structure:
                    {{
                        \"results\": [
                            {{
                                \"title\": \"Title of the result\",
                                \"content\": \"Brief summary or key information (2-3 sentences)\",
                                \"relevance\": 0.9,
                                \"url\": \"https://example.com\",
                                \"published_at\": \"2024-01-01\",
                                \"metadata\": {{}}
                            }}
                        ]
                    }}

                    Focus on accuracy, relevance, and provide specific information about the topic. If you cannot find specific information, acknowledge this limitation and provide what relevant information you can.

                    Context: The user is asking about: {}",
                    query, query
                ),
            }],
            max_tokens: self.config.max_tokens,
            temperature: self.config.temperature,
        };

        let response = self.client
            .post(&url)
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow::anyhow!("MiniMax API error: {}", error_text));
        }

        let minimax_response: MiniMaxResponse = response.json().await?;
        let text_response = minimax_response.reply.choices.first().and_then(|c| c.delta.content.clone()).unwrap_or_default();
        
        // Try to parse JSON response, fall back to text parsing
        let search_items = if let Ok(parsed) = serde_json::from_str::<MiniMaxSearchResponse>(&text_response) {
            parsed.results.into_iter().map(|item| ResearchItem {
                id: format!("minimax_{}", Uuid::new_v4()),
                title: item.title,
                content: item.content,
                url: item.url,
                source: "minimax".to_string(),
                relevance: item.relevance,
                published_at: item.published_at,
                metadata: serde_json::json!({}),
            }).collect()
        } else {
            // Fallback: treat as general text and create a research result
            let content = if text_response.len() > 500 {
                format!("{}...", &text_response[..500])
            } else {
                text_response
            };

            vec![ResearchItem {
                id: format!("minimax_{}", Uuid::new_v4()),
                title: format!("Research on {}", query),
                content,
                url: None,
                source: "minimax".to_string(),
                relevance: 0.88,
                published_at: Some(Utc::now().to_rfc3339()),
                metadata: serde_json::json!({"fallback": true}),
            }]
        };

        Ok(ModelSearchResult {
            total_results: Some(search_items.len()),
            results: search_items,
            query: query.to_string(),
            model: "minimax".to_string(),
        })
    }

    async fn internal_generate(&self, prompt: &str) -> Result<String> {
        tracing::info!("Generating content with MiniMax for prompt: {}", prompt);
        
        let request = MiniMaxRequest {
            model: self.config.model.clone(),
            messages: vec![MiniMaxMessage {
                role: "user".to_string(),
                content: prompt.to_string(),
            }],
            max_tokens: self.config.max_tokens,
            temperature: self.config.temperature,
        };

        let response = self.client
            .post(&format!("{}/v1/text/chatcompletion", self.config.base_url))
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow::anyhow!("MiniMax API error: {}", error_text));
        }

        let minimax_response: MiniMaxResponse = response.json().await?;
        Ok(minimax_response.reply.choices.first().and_then(|c| c.delta.content.clone()).unwrap_or_default())
    }

    async fn internal_analyze(&self, text: &str) -> Result<String> {
        tracing::info!("Analyzing text with MiniMax (length: {} chars)", text.len());
        
        let request = MiniMaxRequest {
            model: self.config.model.clone(),
            messages: vec![MiniMaxMessage {
                role: "user".to_string(),
                content: format!(
                    "Analyze the following text and provide insights, key points, and a summary:
                    
                    Text to analyze:
                    {}
                    
                    Please provide:
                    1. A brief summary (1-2 sentences)
                    2. Key insights or main points
                    3. Any notable observations or analysis
                    4. Overall assessment
                    
                    Format your response in a clear, structured way.",
                    text
                ),
            }],
            max_tokens: self.config.max_tokens,
            temperature: self.config.temperature,
        };

        let response = self.client
            .post(&format!("{}/v1/text/chatcompletion", self.config.base_url))
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .json(&request)
            .send()
            .await?;

        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow::anyhow!("MiniMax API error: {}", error_text));
        }

        let minimax_response: MiniMaxResponse = response.json().await?;
        Ok(minimax_response.reply.choices.first().and_then(|c| c.delta.content.clone()).unwrap_or_default())
    }
}

#[async_trait::async_trait]
impl ModelClient for MiniMaxClient {
    fn name(&self) -> &str {
        "MiniMax"
    }

    async fn search(&self, query: &str) -> Result<ModelSearchResult> {
        self.internal_search(query).await
    }

    async fn generate(&self, prompt: &str) -> Result<String> {
        self.internal_generate(prompt).await
    }

    async fn analyze(&self, text: &str) -> Result<String> {
        self.internal_analyze(text).await
    }
}

// ── API structures ──────────────────────────────────────────────────

// Gemini API structures
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeminiGenerateRequest {
    pub contents: Vec<Content>,
    pub generation_config: Option<GenerationConfig>,
    pub safety_settings: Option<Vec<SafetySetting>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Content {
    pub role: String,
    pub parts: Vec<Part>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Part {
    pub text: Option<String>,
    pub file_data: Option<FileData>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileData {
    pub mime_type: String,
    pub file_uri: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GenerationConfig {
    pub temperature: Option<f64>,
    pub top_p: Option<f64>,
    pub top_k: Option<i32>,
    pub max_output_tokens: Option<i32>,
    pub stop_sequences: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SafetySetting {
    pub category: String,
    pub threshold: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeminiResponse {
    pub candidates: Vec<Candidate>,
    pub usage_metadata: Option<UsageMetadata>,
    pub prompt_feedback: Option<PromptFeedback>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Candidate {
    pub content: Option<Content>,
    pub finish_reason: Option<String>,
    pub safety_ratings: Option<Vec<SafetyRating>>,
    pub citation_metadata: Option<CitationMetadata>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SafetyRating {
    pub category: String,
    pub probability: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CitationMetadata {
    pub citation_sources: Vec<CitationSource>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CitationSource {
    pub start_index: i32,
    pub end_index: i32,
    pub uri: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageMetadata {
    pub prompt_token_count: i32,
    pub candidates_token_count: i32,
    pub total_token_count: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptFeedback {
    pub safety_ratings: Vec<SafetyRating>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeminiSearchResponse {
    pub results: Vec<GeminiSearchItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeminiSearchItem {
    pub title: String,
    pub content: String,
    pub relevance: f64,
    pub url: Option<String>,
    pub published_at: Option<String>,
}

// xAI API structures
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XaiRequest {
    pub model: String,
    pub messages: Vec<XaiMessage>,
    pub max_tokens: usize,
    pub temperature: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XaiMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XaiResponse {
    pub id: String,
    pub object: String,
    pub created: i64,
    pub model: String,
    pub choices: Vec<XaiChoice>,
    pub usage: XaiUsage,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XaiChoice {
    pub index: i32,
    pub message: XaiMessageContent,
    pub finish_reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XaiMessageContent {
    pub role: String,
    pub content: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XaiUsage {
    pub prompt_tokens: i32,
    pub completion_tokens: i32,
    pub total_tokens: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XaiSearchResponse {
    pub results: Vec<XaiSearchItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XaiSearchItem {
    pub title: String,
    pub content: String,
    pub relevance: f64,
    pub url: Option<String>,
    pub published_at: Option<String>,
}

// MiniMax API structures
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxRequest {
    pub model: String,
    pub messages: Vec<MiniMaxMessage>,
    pub max_tokens: usize,
    pub temperature: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxMessage {
    pub role: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxResponse {
    pub base_resp: BaseResp,
    pub reply: MiniMaxReply,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BaseResp {
    pub status_code: i32,
    pub status_msg: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxReply {
    pub choices: Vec<MiniMaxChoice>,
    pub usage: MiniMaxUsage,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxChoice {
    pub delta: MiniMaxDelta,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxDelta {
    pub role: String,
    pub content: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxUsage {
    pub prompt_tokens: i32,
    pub completion_tokens: i32,
    pub total_tokens: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxSearchResponse {
    pub results: Vec<MiniMaxSearchItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxSearchItem {
    pub title: String,
    pub content: String,
    pub relevance: f64,
    pub url: Option<String>,
    pub published_at: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_registry_with_gemini() {
        let config = Config {
            models: ModelsConfig {
                gemini: Some(GeminiConfig {
                    api_key: "test_key".into(),
                    model: "gemini-2.0-flash".into(),
                    base_url: "https://generativelanguage.googleapis.com".into(),
                    max_tokens: 8192,
                    temperature: 0.7,
                    timeout: 30,
                }),
                xai: None,
                minimax: None,
            },
            storage: StorageConfig {
                enabled: false,
                vector_db_path: std::path::PathBuf::from("./data"),
                max_memory_mb: 1024,
                sessions_path: std::path::PathBuf::from("./sessions"),
            },
            skills: SkillsConfig {
                skills_path: std::path::PathBuf::from("./skills"),
                auto_load: true,
            },
        };

        let registry = ModelRegistry::new(&config).unwrap();
        assert!(registry.get("gemini").is_some());
        assert_eq!(registry.list_available().len(), 1);
    }

    #[test]
    fn test_registry_skips_empty_keys() {
        let config = Config::default();
        let registry = ModelRegistry::new(&config).unwrap();
        // Default has empty api_key strings → no clients registered
        assert!(registry.list_available().is_empty());
    }
}