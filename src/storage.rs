use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use tokio::fs;
use tokio::io::AsyncWriteExt;

/// Vector storage implementation using ZVec
#[derive(Debug, Clone)]
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

/// Search result from vector storage
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
        let embeddings = Self::load_embeddings(config)?;
        
        Ok(Self {
            config: config.clone(),
            embeddings,
        })
    }

    /// Store content in vector database
    pub async fn store(&mut self, id: &str, content: &str, metadata: &HashMap<String, serde_json::Value>) -> Result<()> {
        // Generate embedding for the content
        let vector = self.generate_embedding(content).await?;
        
        let embedding = Embedding {
            id: id.to_string(),
            vector,
            content: content.to_string(),
            metadata: metadata.clone(),
            created_at: chrono::Utc::now(),
            accessed_at: None,
        };

        // Update or insert the embedding
        self.embeddings.insert(id.to_string(), embedding);
        
        // Save to disk
        self.save_embeddings().await?;
        
        Ok(())
    }

    /// Perform semantic search
    pub async fn semantic_search(&self, query: &str, limit: usize) -> Result<Vec<SearchResult>> {
        // Generate embedding for the query
        let query_vector = self.generate_embedding(query).await?;
        
        // Calculate cosine similarity with all stored embeddings
        let mut similarities = Vec::new();
        
        for embedding in self.embeddings.values() {
            let similarity = self.cosine_similarity(&query_vector, &embedding.vector);
            similarities.push((embedding, similarity));
        }

        // Sort by similarity (descending)
        similarities.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        
        // Take top results
        let top_results = similarities.into_iter()
            .take(limit)
            .filter(|(_, score)| *score > 0.3) // Threshold for relevance
            .map(|(embedding, score)| SearchResult {
                id: embedding.id.clone(),
                title: embedding.metadata.get("title")
                    .and_then(|v| v.as_str())
                    .unwrap_or("Untitled")
                    .to_string(),
                content: embedding.content.clone(),
                score,
                metadata: embedding.metadata.clone(),
            })
            .collect();

        Ok(top_results)
    }

    /// Get an embedding by ID
    pub async fn get(&mut self, id: &str) -> Option<Embedding> {
        if let Some(embedding) = self.embeddings.get_mut(id) {
            embedding.accessed_at = Some(chrono::Utc::now());
            Some(embedding.clone())
        } else {
            None
        }
    }

    /// Delete an embedding by ID
    pub async fn delete(&mut self, id: &str) -> Result<()> {
        self.embeddings.remove(id);
        self.save_embeddings().await?;
        Ok(())
    }

    /// List all stored embeddings
    pub fn list(&self) -> Vec<String> {
        self.embeddings.keys().cloned().collect()
    }

    /// Clean up old embeddings
    pub async fn cleanup(&mut self, days_old: u64) -> Result<usize> {
        let cutoff_time = chrono::Utc::now() - chrono::Duration::days(days_old as i64);
        
        let count_before = self.embeddings.len();
        
        self.embeddings.retain(|_, embedding| {
            embedding.created_at > cutoff_time
        });

        let count_after = self.embeddings.len();
        let cleaned_count = count_before - count_after;

        if cleaned_count > 0 {
            self.save_embeddings().await?;
        }

        Ok(cleaned_count)
    }

    /// Generate embedding for content
    async fn generate_embedding(&self, content: &str) -> Result<Vec<f32>> {
        // This is a placeholder implementation
        // In a real implementation, this would use an actual embedding model
        
        // Simple hash-based "embedding" for demonstration
        let mut embedding = Vec::new();
        for i in 0..128 {
            let seed = content.len() as u32 + i as u32;
            embedding.push((seed.sin() * 1000.0) as f32 / 1000.0);
        }
        
        Ok(embedding)
    }

    /// Calculate cosine similarity between two vectors
    fn cosine_similarity(&self, a: &[f32], b: &[f32]) -> f64 {
        if a.len() != b.len() {
            return 0.0;
        }

        let dot_product: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let norm_a = (a.iter().map(|x| x * x).sum::<f32>()).sqrt();
        let norm_b = (b.iter().map(|x| x * x).sum::<f32>()).sqrt();

        if norm_a == 0.0 || norm_b == 0.0 {
            0.0
        } else {
            (dot_product / (norm_a * norm_b)) as f64
        }
    }

    /// Load embeddings from disk
    async fn load_embeddings(config: &StorageConfig) -> Result<HashMap<String, Embedding>> {
        let path = config.vector_db_path.join("embeddings.json");
        
        if path.exists() {
            let content = fs::read_to_string(&path).await?;
            let embeddings: HashMap<String, Embedding> = serde_json::from_str(&content)?;
            Ok(embeddings)
        } else {
            Ok(HashMap::new())
        }
    }

    /// Save embeddings to disk
    async fn save_embeddings(&self) -> Result<()> {
        let path = self.config.vector_db_path.join("embeddings.json");
        
        // Create directory if it doesn't exist
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).await?;
        }

        let content = serde_json::to_string_pretty(&self.embeddings)?;
        let mut file = fs::File::create(path).await?;
        file.write_all(content.as_bytes()).await?;
        
        Ok(())
    }

    /// Get storage statistics
    pub fn stats(&self) -> StorageStats {
        let total_embeddings = self.embeddings.len();
        let total_size_bytes = self.embeddings.values()
            .map(|e| e.content.len() + e.vector.len() * 4)
            .sum::<usize>();
        
        let avg_embedding_size = if total_embeddings > 0 {
            total_size_bytes / total_embeddings
        } else {
            0
        };

        let oldest_timestamp = self.embeddings.values()
            .map(|e| e.created_at)
            .min()
            .unwrap_or(chrono::Utc::now());

        let newest_timestamp = self.embeddings.values()
            .map(|e| e.created_at)
            .max()
            .unwrap_or(chrono::Utc::now());

        StorageStats {
            total_embeddings,
            total_size_bytes,
            avg_embedding_size,
            oldest_timestamp,
            newest_timestamp,
        }
    }
}

/// Storage statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StorageStats {
    pub total_embeddings: usize,
    pub total_size_bytes: usize,
    pub avg_embedding_size: usize,
    pub oldest_timestamp: chrono::DateTime<chrono::Utc>,
    pub newest_timestamp: chrono::DateTime<chrono::Utc>,
}

/// Session management
#[derive(Debug, Clone)]
pub struct SessionManager {
    sessions_path: std::path::PathBuf,
    max_sessions: usize,
}

impl SessionManager {
    pub fn new(sessions_path: std::path::PathBuf, max_sessions: usize) -> Self {
        Self {
            sessions_path,
            max_sessions,
        }
    }

    /// Save a session
    pub async fn save_session(&self, session_id: &str, data: &serde_json::Value) -> Result<()> {
        let session_path = self.sessions_path.join(format!("{}.json", session_id));
        
        // Create directory if it doesn't exist
        if let Some(parent) = session_path.parent() {
            fs::create_dir_all(parent).await?;
        }

        let content = serde_json::to_string_pretty(data)?;
        let mut file = fs::File::create(session_path).await?;
        file.write_all(content.as_bytes()).await?;

        // Clean up old sessions if we're over the limit
        self.cleanup_old_sessions().await?;

        Ok(())
    }

    /// Load a session
    pub async fn load_session(&self, session_id: &str) -> Result<Option<serde_json::Value>> {
        let session_path = self.sessions_path.join(format!("{}.json", session_id));
        
        if session_path.exists() {
            let content = fs::read_to_string(&session_path).await?;
            let data: serde_json::Value = serde_json::from_str(&content)?;
            Ok(Some(data))
        } else {
            Ok(None)
        }
    }

    /// List all sessions
    pub async fn list_sessions(&self) -> Result<Vec<String>> {
        let mut sessions = Vec::new();
        
        if self.sessions_path.exists() {
            for entry in fs::read_dir(&self.sessions_path).await? {
                let entry = entry?;
                let path = entry.path();
                
                if path.extension().and_then(|s| s.to_str()) == Some("json") {
                    if let Some(file_name) = path.file_name().and_then(|s| s.to_str()) {
                        let session_id = file_name.strip_suffix(".json").unwrap();
                        sessions.push(session_id.to_string());
                    }
                }
            }
        }

        sessions.sort();
        Ok(sessions)
    }

    /// Delete a session
    pub async fn delete_session(&self, session_id: &str) -> Result<bool> {
        let session_path = self.sessions_path.join(format!("{}.json", session_id));
        
        if session_path.exists() {
            fs::remove_file(session_path).await?;
            Ok(true)
        } else {
            Ok(false)
        }
    }

    /// Clean up old sessions
    async fn cleanup_old_sessions(&self) -> Result<()> {
        let sessions = self.list_sessions().await?;
        
        if sessions.len() > self.max_sessions {
            // Sort by modification time (newest first) and keep the most recent ones
            let mut session_entries: Vec<_> = sessions.into_iter().map(|s| {
                let path = self.sessions_path.join(format!("{}.json", s));
                async move {
                    (s, path.metadata().await.map(|m| m.modified().unwrap_or(std::time::UNIX_EPOCH)))
                }
            }).collect();

            // Wait for all metadata operations to complete
            let session_metadata = futures::future::join_all(session_entries).await;
            
            // Sort by modification time
            session_metadata.sort_by(|a, b| b.1.cmp(&a.1));
            
            // Delete oldest sessions
            let to_delete = session_metadata[self.max_sessions..].to_vec();
            
            for (session_id, _) in to_delete {
                self.delete_session(&session_id).await?;
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[tokio::test]
    async fn test_storage_operations() {
        let config = StorageConfig {
            enabled: true,
            vector_db_path: std::path::PathBuf::from("./test_data"),
            max_memory_mb: 1024,
            sessions_path: std::path::PathBuf::from("./test_sessions"),
        };

        let mut storage = VectorStorage::new(&config).unwrap();
        
        let mut metadata = HashMap::new();
        metadata.insert("title".to_string(), serde_json::Value::String("Test Document".to_string()));
        metadata.insert("author".to_string(), serde_json::Value::String("Test Author".to_string()));

        // Test storing content
        storage.store("test_001", "This is test content.", &metadata).await.unwrap();
        
        // Test semantic search
        let results = storage.semantic_search("test content", 5).await.unwrap();
        assert!(!results.is_empty());
        
        // Test retrieval
        let embedding = storage.get("test_001").await;
        assert!(embedding.is_some());
        
        // Test deletion
        storage.delete("test_001").await.unwrap();
        
        let stats = storage.stats();
        println!("Storage stats: {:?}", stats);
    }
}