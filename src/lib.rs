pub mod core;
pub mod models;
pub mod storage;
pub mod skills;
pub mod cli;
pub mod utils;

pub use core::*;
pub use models::*;
pub use storage::*;
pub use skills::*;
pub use cli::*;

use anyhow::Result;
use std::path::Path;

/// Main DSearch struct - the core research platform
#[derive(Debug, Clone)]
pub struct DSearch {
    pub models: ModelRegistry,
    pub storage: Option<VectorStorage>,
    pub config: Config,
}

impl DSearch {
    /// Create a new DSearch instance with configuration
    pub fn new(config: Config) -> Result<Self> {
        let models = ModelRegistry::new(&config)?;
        let storage = if config.storage.enabled {
            Some(VectorStorage::new(&config.storage)?)
        } else {
            None
        };

        Ok(Self {
            models,
            storage,
            config,
        })
    }

    /// Perform a multi-model search
    pub async fn search(&self, query: &str, params: SearchParams) -> Result<SearchResults> {
        tracing::info!("Starting multi-model search for: {}", query);
        
        // Run searches in parallel across available models
        let mut tasks = Vec::new();
        
        for model in &params.models {
            if let Some(model_client) = self.models.get(model) {
                let query = query.to_string();
                let model_client = model_client.clone();
                
                tasks.push(async move {
                    let result = model_client.search(&query).await;
                    (model.to_string(), result)
                });
            }
        }

        // Execute all searches concurrently
        let results = futures::future::join_all(tasks).await;
        
        // Combine and deduplicate results
        let combined = self.combine_results(results, &params).await?;
        
        // Store results in vector database if enabled
        if let Some(ref storage) = self.storage {
            for result in &combined.results {
                storage.store(&result.id, &result.content, &result.metadata).await?;
            }
        }

        Ok(combined)
    }

    /// Perform semantic search using vector database
    pub async fn semantic_search(&self, query: &str, limit: usize) -> Result<SearchResults> {
        if let Some(ref storage) = self.storage {
            let results = storage.semantic_search(query, limit).await?;
            Ok(SearchResults {
                query: query.to_string(),
                results,
                total: results.len(),
                models: vec!["vector".to_string()],
                timestamp: chrono::Utc::now(),
            })
        } else {
            Err(anyhow::anyhow!("Vector storage not enabled"))
        }
    }

    /// Save a research session
    pub async fn save_session(&self, id: &str, results: &SearchResults) -> Result<()> {
        let session_path = self.config.storage.sessions_path.join(id);
        std::fs::create_dir_all(&session_path)?;
        
        let session_data = serde_json::to_string_pretty(results)?;
        std::fs::write(session_path.join("session.json"), session_data)?;
        
        Ok(())
    }

    /// Load a saved research session
    pub async fn load_session(&self, id: &str) -> Result<SearchResults> {
        let session_path = self.config.storage.sessions_path.join(id);
        let session_data = std::fs::read_to_string(session_path.join("session.json"))?;
        let results: SearchResults = serde_json::from_str(&session_data)?;
        Ok(results)
    }

    /// Combine results from multiple models with deduplication
    async fn combine_results(
        &self,
        results: Vec<(String, Result<ModelSearchResult>)>,
        params: &SearchParams,
    ) -> Result<SearchResults> {
        let mut all_results = Vec::new();
        let mut models_used = Vec::new();

        for (model_name, result) in results {
            models_used.push(model_name.clone());
            match result {
                Ok(model_result) => {
                    for item in model_result.results {
                        all_results.push(ResearchItem {
                            id: format!("{}_{}", model_name, item.id),
                            title: item.title,
                            content: item.content,
                            url: item.url,
                            source: model_name.clone(),
                            relevance: item.relevance,
                            metadata: item.metadata,
                        });
                    }
                }
                Err(e) => {
                    tracing::warn!("Model {} search failed: {}", model_name, e);
                }
            }
        }

        // Sort by relevance and limit results
        all_results.sort_by(|a, b| b.relevance.partial_cmp(&a.relevance).unwrap_or(std::cmp::Ordering::Equal));
        let final_results = all_results.into_iter().take(params.max_results).collect();

        Ok(SearchResults {
            query: params.query.clone(),
            results: final_results,
            total: final_results.len(),
            models: models_used,
            timestamp: chrono::Utc::now(),
        })
    }
}

/// Configuration structure
#[derive(Debug, Clone, serde::Deserialize)]
pub struct Config {
    pub models: ModelsConfig,
    pub storage: StorageConfig,
    pub skills: SkillsConfig,
}

/// Models configuration
#[derive(Debug, Clone, serde::Deserialize)]
pub struct ModelsConfig {
    pub gemini: Option<GeminiConfig>,
    pub xai: Option<XaiConfig>,
    pub minimax: Option<MinimaxConfig>,
}

/// Storage configuration
#[derive(Debug, Clone, serde::Deserialize)]
pub struct StorageConfig {
    pub enabled: bool,
    pub vector_db_path: std::path::PathBuf,
    pub max_memory_mb: u64,
    pub sessions_path: std::path::PathBuf,
}

/// Skills configuration
#[derive(Debug, Clone, serde::Deserialize)]
pub struct SkillsConfig {
    pub skills_path: std::path::PathBuf,
    pub auto_load: bool,
}

/// Search parameters
#[derive(Debug, Clone)]
pub struct SearchParams {
    pub query: String,
    pub models: Vec<String>,
    pub max_results: usize,
    pub timeout_secs: u64,
}

/// Search results
#[derive(Debug, Clone, serde::Serialize)]
pub struct SearchResults {
    pub query: String,
    pub results: Vec<ResearchItem>,
    pub total: usize,
    pub models: Vec<String>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// Individual research item
#[derive(Debug, Clone, serde::Serialize)]
pub struct ResearchItem {
    pub id: String,
    pub title: String,
    pub content: String,
    pub url: Option<String>,
    pub source: String,
    pub relevance: f64,
    pub metadata: serde_json::Value,
}

/// Model search result (internal format)
pub struct ModelSearchResult {
    pub results: Vec<ModelSearchItem>,
}

/// Individual model search item
pub struct ModelSearchItem {
    pub id: String,
    pub title: String,
    pub content: String,
    pub url: Option<String>,
    pub relevance: f64,
    pub metadata: serde_json::Value,
}

/// Error types
#[derive(Debug, thiserror::Error)]
pub enum DSearchError {
    #[error("Configuration error: {0}")]
    Config(String),
    #[error("Model not found: {0}")]
    ModelNotFound(String),
    #[error("Search error: {0}")]
    Search(String),
    #[error("Storage error: {0}")]
    Storage(String),
    #[error("Skills error: {0}")]
    Skills(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_deserialization() {
        let config_str = r#"
        [models]
        [models.gemini]
        api_key = "test_key"
        model = "gemini-pro"

        [storage]
        enabled = true
        vector_db_path = "./data/vectors"
        max_memory_mb = 1024
        sessions_path = "./sessions"

        [skills]
        skills_path = "./skills"
        auto_load = true
        "#;

        let config: Config = toml::from_str(config_str).expect("Failed to parse config");
        assert!(config.models.gemini.is_some());
        assert!(config.storage.enabled);
        assert_eq!(config.storage.max_memory_mb, 1024);
    }
}