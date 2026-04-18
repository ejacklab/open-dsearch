use anyhow::Result;
use std::collections::HashMap;
use serde::{Deserialize, Serialize};

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
                    timeout: Some(30),
                }),
                xai: Some(XaiConfig {
                    api_key: String::new(),
                    model: "grok-beta".into(),
                    base_url: "https://api.x.ai".into(),
                    max_tokens: 4096,
                    temperature: 0.7,
                    timeout: Some(30),
                }),
                minimax: Some(MiniMaxConfig {
                    api_key: String::new(),
                    model: "MiniMax-Text-01".into(),
                    base_url: "https://api.minimax.chat".into(),
                    max_tokens: 4096,
                    temperature: 0.7,
                    timeout: Some(30),
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
    #[serde(default)]
    pub timeout: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XaiConfig {
    pub api_key: String,
    pub model: String,
    pub base_url: String,
    pub max_tokens: usize,
    pub temperature: f64,
    #[serde(default)]
    pub timeout: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MiniMaxConfig {
    pub api_key: String,
    pub model: String,
    pub base_url: String,
    pub max_tokens: usize,
    pub temperature: f64,
    #[serde(default)]
    pub timeout: Option<u64>,
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
    pub results: Vec<ModelSearchItem>,
    pub total_results: Option<usize>,
    pub query: String,
    pub model: String,
}

/// Individual search item from a model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelSearchItem {
    pub id: String,
    pub title: String,
    pub content: String,
    pub url: Option<String>,
    pub relevance: f64,
    pub metadata: serde_json::Value,
}

// ── Gemini client (uses reqwest directly) ────────────────────────────

#[derive(Debug)]
pub struct GeminiClient {
    config: GeminiConfig,
    client: reqwest::Client,
}

impl GeminiClient {
    pub fn new(config: &GeminiConfig) -> Result<Self> {
        Ok(Self {
            config: config.clone(),
            client: reqwest::Client::new(),
        })
    }
}

#[async_trait::async_trait]
impl ModelClient for GeminiClient {
    fn name(&self) -> &str { "Gemini" }

    async fn search(&self, query: &str) -> Result<ModelSearchResult> {
        // TODO: Real Gemini API call via reqwest
        let _ = &self.client;
        Ok(ModelSearchResult {
            results: vec![ModelSearchItem {
                id: "gemini_001".into(),
                title: format!("Research on {}", query),
                content: format!("Placeholder Gemini result for: {}", query),
                url: None,
                relevance: 0.9,
                metadata: serde_json::json!({}),
            }],
            total_results: Some(1),
            query: query.into(),
            model: self.name().into(),
        })
    }

    async fn generate(&self, prompt: &str) -> Result<String> {
        Ok(format!("Gemini generation placeholder: {}", prompt))
    }

    async fn analyze(&self, text: &str) -> Result<String> {
        Ok(format!("Gemini analysis placeholder: {}", text))
    }
}

// ── xAI client ───────────────────────────────────────────────────────

#[derive(Debug)]
pub struct XaiClient {
    config: XaiConfig,
    client: reqwest::Client,
}

impl XaiClient {
    pub fn new(config: &XaiConfig) -> Result<Self> {
        Ok(Self {
            config: config.clone(),
            client: reqwest::Client::new(),
        })
    }
}

#[async_trait::async_trait]
impl ModelClient for XaiClient {
    fn name(&self) -> &str { "xAI" }

    async fn search(&self, query: &str) -> Result<ModelSearchResult> {
        let _ = &self.client;
        Ok(ModelSearchResult {
            results: vec![ModelSearchItem {
                id: "xai_001".into(),
                title: format!("xAI Research on {}", query),
                content: format!("Placeholder xAI result for: {}", query),
                url: None,
                relevance: 0.85,
                metadata: serde_json::json!({}),
            }],
            total_results: Some(1),
            query: query.into(),
            model: self.name().into(),
        })
    }

    async fn generate(&self, prompt: &str) -> Result<String> {
        Ok(format!("xAI generation placeholder: {}", prompt))
    }

    async fn analyze(&self, text: &str) -> Result<String> {
        Ok(format!("xAI analysis placeholder: {}", text))
    }
}

// ── MiniMax client ───────────────────────────────────────────────────

#[derive(Debug)]
pub struct MiniMaxClient {
    config: MiniMaxConfig,
    client: reqwest::Client,
}

impl MiniMaxClient {
    pub fn new(config: &MiniMaxConfig) -> Result<Self> {
        Ok(Self {
            config: config.clone(),
            client: reqwest::Client::new(),
        })
    }
}

#[async_trait::async_trait]
impl ModelClient for MiniMaxClient {
    fn name(&self) -> &str { "MiniMax" }

    async fn search(&self, query: &str) -> Result<ModelSearchResult> {
        let _ = &self.client;
        Ok(ModelSearchResult {
            results: vec![ModelSearchItem {
                id: "minimax_001".into(),
                title: format!("MiniMax Research on {}", query),
                content: format!("Placeholder MiniMax result for: {}", query),
                url: None,
                relevance: 0.88,
                metadata: serde_json::json!({}),
            }],
            total_results: Some(1),
            query: query.into(),
            model: self.name().into(),
        })
    }

    async fn generate(&self, prompt: &str) -> Result<String> {
        Ok(format!("MiniMax generation placeholder: {}", prompt))
    }

    async fn analyze(&self, text: &str) -> Result<String> {
        Ok(format!("MiniMax analysis placeholder: {}", text))
    }
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
                    timeout: Some(30),
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
