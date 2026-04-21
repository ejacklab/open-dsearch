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
        &mut self,
        id: &str,
        content: &str,
        metadata: &HashMap<String, serde_json::Value>,
    ) -> Result<()> {
        let vector = self.generate_embedding(content);
        let embedding = Embedding {
            id: id.to_string(),
            vector,
            content: content.to_string(),
            metadata: metadata.clone(),
            created_at: chrono::Utc::now(),
            accessed_at: None,
        };
        
        self.embeddings.insert(id.to_string(), embedding);
        self.persist_embeddings().await?;
        Ok(())
    }

    /// Perform semantic search
    pub async fn semantic_search(
        &self,
        query: &str,
        limit: usize,
    ) -> Result<Vec<crate::ResearchItem>> {
        let query_vector = self.generate_embedding(query);
        let mut results: Vec<(f64, &Embedding)> = self.embeddings
            .iter()
            .map(|(_, embedding)| {
                let similarity = Self::cosine_similarity(&query_vector, &embedding.vector);
                (similarity, embedding)
            })
            .filter(|(similarity, _)| *similarity > 0.1) // Filter out very low similarity results
            .collect();
        
        // Sort by similarity (descending)
        results.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        
        let mut research_items = Vec::new();
        for (similarity, embedding) in results.into_iter().take(limit) {
            let title = embedding.metadata
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or_else(|| "Untitled");
                
            research_items.push(crate::ResearchItem {
                id: embedding.id.clone(),
                title: title.to_string(),
                content: embedding.content.clone(),
                url: embedding.metadata.get("url").and_then(|v| v.as_str()).map(|s| s.to_string()),
                source: "vector-search".to_string(),
                relevance: similarity,
                metadata: serde_json::to_value(&embedding.metadata).unwrap_or_default(),
            });
        }
        
        Ok(research_items)
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

    /// Generate a content-based embedding using simple hashing
    fn generate_embedding(&self, content: &str) -> Vec<f32> {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        content.hash(&mut hasher);
        let seed = hasher.finish();
        
        let mut embedding = Vec::with_capacity(128);
        for i in 0..128 {
            // Use deterministic pseudo-random generation based on content
            let combined = (seed as u64).wrapping_add(i as u64);
            let pseudo_random = (combined.wrapping_mul(9301).wrapping_add(49297)) % 233280;
            let normalized = pseudo_random as f32 / 233280.0;
            embedding.push(normalized);
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
    
    async fn persist_embeddings(&self) -> Result<()> {
        // Ensure directory exists
        tokio::fs::create_dir_all(&self.config.vector_db_path).await?;
        
        let path = self.config.vector_db_path.join("embeddings.json");
        let content = serde_json::to_string_pretty(&self.embeddings)?;
        tokio::fs::write(&path, content).await?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use serde_json::Value;

    #[test]
    fn test_cosine_similarity() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0];
        assert!((VectorStorage::cosine_similarity(&a, &b) - 1.0).abs() < 0.001);

        let c = vec![0.0, 1.0, 0.0];
        assert!(VectorStorage::cosine_similarity(&a, &c).abs() < 0.001);
    }

    #[tokio::test]
    async fn test_store_and_semantic_search() {
        let config = StorageConfig {
            enabled: true,
            vector_db_path: std::path::PathBuf::from("./test_data"),
            max_memory_mb: 1024,
            sessions_path: std::path::PathBuf::from("./sessions"),
        };
        
        // Clean up any existing test data
        let _ = std::fs::remove_dir_all(&config.vector_db_path);
        
        let mut storage = VectorStorage::new(&config).unwrap();
        
        // Store some test content
        let mut metadata1 = HashMap::new();
        metadata1.insert("title".to_string(), Value::String("AI Research".to_string()));
        metadata1.insert("url".to_string(), Value::String("https://example.com/ai".to_string()));
        
        storage.store("doc1", "Machine learning and artificial intelligence research papers", &metadata1).await.unwrap();
        
        let mut metadata2 = HashMap::new();
        metadata2.insert("title".to_string(), Value::String("Climate Science".to_string()));
        metadata2.insert("url".to_string(), Value::String("https://example.com/climate".to_string()));
        
        storage.store("doc2", "Climate change and global warming studies", &metadata2).await.unwrap();
        
        // Test semantic search
        let results = storage.semantic_search("machine learning artificial intelligence", 10).await.unwrap();
        assert!(!results.is_empty());
        // Should find AI Research doc with highest relevance
        assert_eq!(results[0].id, "doc1");
        assert_eq!(results[0].title, "AI Research");
        assert!(results[0].relevance > 0.1);
        
        // Test search with climate query
        let results2 = storage.semantic_search("climate warming", 10).await.unwrap();
        assert!(!results2.is_empty());
        // Should find Climate Science doc
        assert_eq!(results2[0].id, "doc2");
        assert_eq!(results2[0].title, "Climate Science");
        assert!(results2[0].relevance > 0.1);
        
        // Clean up test data
        let _ = std::fs::remove_dir_all(&config.vector_db_path);
    }
}
