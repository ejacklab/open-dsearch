use crate::models::StorageConfig;
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Vector storage implementation (in-memory with file persistence)
#[derive(Debug)]
pub struct VectorStorage {
    config: StorageConfig,
    embeddings: HashMap<String, Embedding>,
}

/// Embedding representation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Embedding {
    pub id: String,
    pub vector: Vec<f32>,
    pub content: String,
    pub metadata: HashMap<String, serde_json::Value>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub accessed_at: Option<chrono::DateTime<chrono::Utc>>,
}

/// Search result from vector storage (maps to ResearchItem in lib.rs)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub id: String,
    pub title: String,
    pub content: String,
    pub score: f64,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl VectorStorage {
    pub fn new(config: &StorageConfig) -> Result<Self> {
        let embeddings = Self::load_embeddings_from_disk(config)?;

        Ok(Self {
            config: config.clone(),
            embeddings,
        })
    }

    /// Store content with metadata
    pub async fn store(
        &self,
        id: &str,
        content: &str,
        metadata: &HashMap<String, serde_json::Value>,
    ) -> Result<()> {
        Ok(())
        // TODO: real embedding generation + persist
    }

    /// Perform semantic search
    pub async fn semantic_search(
        &self,
        _query: &str,
        _limit: usize,
    ) -> Result<Vec<crate::ResearchItem>> {
        // TODO: real embedding search
        Ok(Vec::new())
    }

    /// Get an embedding by ID
    pub fn get(&self, id: &str) -> Option<&Embedding> {
        self.embeddings.get(id)
    }

    /// Delete an embedding by ID
    pub async fn delete(&mut self, id: &str) -> Result<()> {
        self.embeddings.remove(id);
        Ok(())
    }

    /// List all stored embedding IDs
    pub fn list(&self) -> Vec<String> {
        self.embeddings.keys().cloned().collect()
    }

    /// Generate a deterministic pseudo-embedding for content
    fn generate_embedding(&self, content: &str) -> Vec<f32> {
        let mut embedding = Vec::with_capacity(128);
        for i in 0..128 {
            let seed = content.len() as u32 + i as u32;
            embedding.push((seed as f32).sin() / 1000.0);
        }
        embedding
    }

    /// Cosine similarity between two vectors
    fn cosine_similarity(a: &[f32], b: &[f32]) -> f64 {
        if a.len() != b.len() {
            return 0.0;
        }
        let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let na = (a.iter().map(|x| x * x).sum::<f32>()).sqrt();
        let nb = (b.iter().map(|x| x * x).sum::<f32>()).sqrt();
        if na == 0.0 || nb == 0.0 {
            0.0
        } else {
            (dot / (na * nb)) as f64
        }
    }

    fn load_embeddings_from_disk(config: &StorageConfig) -> Result<HashMap<String, Embedding>> {
        let path = config.vector_db_path.join("embeddings.json");
        if path.exists() {
            let content = std::fs::read_to_string(&path)?;
            let embeddings: HashMap<String, Embedding> = serde_json::from_str(&content)?;
            Ok(embeddings)
        } else {
            Ok(HashMap::new())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cosine_similarity() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0];
        assert!((VectorStorage::cosine_similarity(&a, &b) - 1.0).abs() < 0.001);

        let c = vec![0.0, 1.0, 0.0];
        assert!(VectorStorage::cosine_similarity(&a, &c).abs() < 0.001);
    }
}
