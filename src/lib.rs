pub mod models;
pub mod storage;
pub mod skills;
pub mod utils;

pub use models::*;
pub use storage::VectorStorage;
pub use skills::SkillsRegistry;
pub use utils::*;

use anyhow::Result;

/// Main DSearch struct - the core research platform
#[derive(Debug)]
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
            // Try to load existing storage or create empty
            match VectorStorage::new(&config.storage) {
                Ok(storage) => Some(storage),
                Err(_) => Some(VectorStorage::new_empty(&config.storage)?),
            }
        } else {
            None
        };

        Ok(Self { models, storage, config })
    }

    /// Perform a multi-model search
    pub async fn search(&self, query: &str, params: SearchParams) -> Result<SearchResults> {
        tracing::info!("Starting multi-model search for: {}", query);

        let mut tasks: Vec<(String, Result<ModelSearchResult>)> = Vec::new();

        for model_name in &params.models {
            if let Some(model_client) = self.models.get(model_name) {
                let result = model_client.search(query).await;
                tasks.push((model_name.clone(), result));
            }
        }

        self.combine_results(tasks, &params)
    }

    /// Perform semantic search using vector database
    pub async fn semantic_search(&self, query: &str, limit: usize) -> Result<SearchResults> {
        if let Some(ref storage) = self.storage {
            let results = storage.semantic_search(query, limit).await?;
            let count = results.len();
            Ok(SearchResults {
                query: query.to_string(),
                total: count,
                results,
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

    fn combine_results(
        &self,
        results: Vec<(String, Result<ModelSearchResult>)>,
        params: &SearchParams,
    ) -> Result<SearchResults> {
        let mut all_results: Vec<ResearchItem> = Vec::new();
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

        all_results.sort_by(|a, b| {
            b.relevance.partial_cmp(&a.relevance).unwrap_or(std::cmp::Ordering::Equal)
        });

        let count = all_results.len().min(params.max_results);
        let final_results: Vec<ResearchItem> = all_results.into_iter().take(params.max_results).collect();

        Ok(SearchResults {
            query: params.query.clone(),
            total: count,
            results: final_results,
            models: models_used,
            timestamp: chrono::Utc::now(),
        })
    }
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
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SearchResults {
    pub query: String,
    pub results: Vec<ResearchItem>,
    pub total: usize,
    pub models: Vec<String>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// Individual research item
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ResearchItem {
    pub id: String,
    pub title: String,
    pub content: String,
    pub url: Option<String>,
    pub source: String,
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
