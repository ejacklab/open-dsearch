use anyhow::Result;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use crate::{ModelClient, ModelSearchResult, SearchItem};

/// Real Gemini API client implementation
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
                    text: prompt.to_string(),
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
}

#[async_trait::async_trait]
impl ModelClient for GeminiClient {
    fn name(&self) -> &str {
        "Gemini"
    }

    async fn search(&self, query: &str) -> Result<ModelSearchResult> {
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
        let search_result = if let Ok(parsed) = serde_json::from_str::<GeminiSearchResponse>(&text_response) {
            // Successfully parsed JSON response
            ModelSearchResult {
                results: parsed.results.into_iter().map(|item| SearchItem {
                    id: format!("gemini_{}", uuid::Uuid::new_v4()),
                    title: item.title,
                    content: item.content,
                    url: item.url,
                    source: "gemini".to_string(),
                    relevance: item.relevance,
                    published_at: item.published_at,
                    metadata: serde_json::json!({}),
                }).collect(),
                total_results: Some(parsed.results.len()),
                query: query.to_string(),
                model: self.name().to_string(),
            }
        } else {
            // Fallback: treat as general text and create a research result
            let content = if text_response.len() > 500 {
                format!("{}...", &text_response[..500])
            } else {
                text_response
            };

            ModelSearchResult {
                results: vec![SearchItem {
                    id: format!("gemini_{}", uuid::Uuid::new_v4()),
                    title: format!("Research on {}", query),
                    content,
                    url: None,
                    source: "gemini".to_string(),
                    relevance: 0.8,
                    published_at: Some(chrono::Utc::now().to_rfc3339()),
                    metadata: serde_json::json!({"fallback": true}),
                }],
                total_results: Some(1),
                query: query.to_string(),
                model: self.name().to_string(),
            }
        };

        Ok(search_result)
    }

    async fn generate(&self, prompt: &str) -> Result<String> {
        tracing::info!("Generating content with Gemini for prompt: {}", prompt);
        
        let response = self.generate_content(prompt).await?;
        let text = self.extract_text_from_response(response)?;
        
        Ok(text)
    }

    async fn analyze(&self, text: &str) -> Result<String> {
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

/// Gemini API structures
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

/// For structured search responses
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