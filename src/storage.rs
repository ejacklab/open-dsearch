use crate::models::StorageConfig;
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Vector storage with TF-IDF based semantic search
#[derive(Debug)]
pub struct VectorStorage {
    config: StorageConfig,
    embeddings: HashMap<String, Embedding>,
    /// All unique terms across all documents, mapped to document frequency count
    doc_freq: HashMap<String, usize>,
    /// Total number of documents stored
    total_docs: usize,
}

/// Embedding representation — stores raw content and token frequencies
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Embedding {
    pub id: String,
    pub vector: Vec<f32>,
    pub content: String,
    pub metadata: HashMap<String, serde_json::Value>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub accessed_at: Option<chrono::DateTime<chrono::Utc>>,
    /// Token -> frequency in this document
    #[serde(default)]
    pub token_freq: HashMap<String, f32>,
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
        let (embeddings, doc_freq, total_docs) = Self::load_from_disk(config)?;

        Ok(Self {
            config: config.clone(),
            embeddings,
            doc_freq,
            total_docs,
        })
    }

    pub fn new_empty(config: &StorageConfig) -> Result<Self> {
        Ok(Self {
            config: config.clone(),
            embeddings: HashMap::new(),
            doc_freq: HashMap::new(),
            total_docs: 0,
        })
    }

    /// Store content with metadata
    pub async fn store(
        &mut self,
        id: &str,
        content: &str,
        metadata: &HashMap<String, serde_json::Value>,
    ) -> Result<()> {
        let tokens = tokenize(content);

        // Compute token frequencies for this document
        let mut token_freq: HashMap<String, f32> = HashMap::new();
        let total_tokens = tokens.len() as f32;
        for token in &tokens {
            *token_freq.entry(token.clone()).or_default() += 1.0 / total_tokens;
        }

        // Update document frequency for each unique token
        for token in token_freq.keys() {
            *self.doc_freq.entry(token.clone()).or_default() += 1;
        }
        self.total_docs += 1;

        // Backward-compatible hash vector
        let vector = Self::generate_hash_embedding(content);

        let embedding = Embedding {
            id: id.to_string(),
            vector,
            content: content.to_string(),
            metadata: metadata.clone(),
            created_at: chrono::Utc::now(),
            accessed_at: None,
            token_freq,
        };

        self.embeddings.insert(id.to_string(), embedding);
        self.persist().await?;
        Ok(())
    }

    /// Perform semantic search using TF-IDF sparse cosine similarity
    pub async fn semantic_search(
        &self,
        query: &str,
        limit: usize,
    ) -> Result<Vec<crate::ResearchItem>> {
        let query_tokens = tokenize(query);
        let query_total = query_tokens.len() as f32;

        // Compute query token frequencies
        let mut query_tf: HashMap<&str, f32> = HashMap::new();
        for token in &query_tokens {
            *query_tf.entry(token.as_str()).or_default() += 1.0 / query_total;
        }

        let mut results: Vec<(f64, &Embedding)> = self.embeddings
            .iter()
            .map(|(_, emb)| {
                let similarity = sparse_cosine_tfidf(
                    &query_tf,
                    &emb.token_freq,
                    &self.doc_freq,
                    self.total_docs,
                );
                (similarity, emb)
            })
            .filter(|(sim, _)| *sim > 0.01)
            .collect();

        results.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));

        let items: Vec<crate::ResearchItem> = results.into_iter().take(limit).map(|(similarity, emb)| {
            let title = emb.metadata
                .get("title")
                .and_then(|v| v.as_str())
                .unwrap_or("Untitled")
                .to_string();

            crate::ResearchItem {
                id: emb.id.clone(),
                title,
                content: format!("{}...", &emb.content[..emb.content.len().min(500)]),
                url: emb.metadata.get("url").and_then(|v| v.as_str()).map(|s| s.to_string()),
                source: "vector-search".to_string(),
                relevance: similarity,
                metadata: serde_json::to_value(&emb.metadata).unwrap_or_default(),
            }
        }).collect();

        Ok(items)
    }

    /// Get an embedding by ID
    pub fn get(&self, id: &str) -> Option<&Embedding> {
        self.embeddings.get(id)
    }

    /// Delete an embedding by ID
    pub async fn delete(&mut self, id: &str) -> Result<()> {
        if let Some(emb) = self.embeddings.remove(id) {
            // Decrement doc frequency for each token
            for token in emb.token_freq.keys() {
                if let Some(freq) = self.doc_freq.get_mut(token) {
                    *freq = freq.saturating_sub(1);
                    if *freq == 0 {
                        self.doc_freq.remove(token);
                    }
                }
            }
            self.total_docs = self.total_docs.saturating_sub(1);
        }
        Ok(())
    }

    /// List all stored embedding IDs
    pub fn list(&self) -> Vec<String> {
        self.embeddings.keys().cloned().collect()
    }

    fn generate_hash_embedding(content: &str) -> Vec<f32> {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        content.hash(&mut hasher);
        let seed = hasher.finish();

        (0..128).map(|i| {
            let combined = (seed as u64).wrapping_add(i as u64);
            let pseudo_random = (combined.wrapping_mul(9301).wrapping_add(49297)) % 233280;
            pseudo_random as f32 / 233280.0
        }).collect()
    }

    fn load_from_disk(config: &StorageConfig) -> Result<(HashMap<String, Embedding>, HashMap<String, usize>, usize)> {
        let emb_path = config.vector_db_path.join("embeddings.json");
        let df_path = config.vector_db_path.join("doc_freq.json");
        let td_path = config.vector_db_path.join("total_docs.json");

        let embeddings = if emb_path.exists() {
            let content = std::fs::read_to_string(&emb_path)?;
            serde_json::from_str(&content)?
        } else {
            HashMap::new()
        };

        let doc_freq = if df_path.exists() {
            let content = std::fs::read_to_string(&df_path)?;
            serde_json::from_str(&content)?
        } else {
            HashMap::new()
        };

        let total_docs = if td_path.exists() {
            let content = std::fs::read_to_string(&td_path)?;
            serde_json::from_str(&content).unwrap_or(0)
        } else {
            0
        };

        Ok((embeddings, doc_freq, total_docs))
    }

    async fn persist(&self) -> Result<()> {
        tokio::fs::create_dir_all(&self.config.vector_db_path).await?;

        let emb_path = self.config.vector_db_path.join("embeddings.json");
        tokio::fs::write(&emb_path, serde_json::to_string_pretty(&self.embeddings)?).await?;

        let df_path = self.config.vector_db_path.join("doc_freq.json");
        tokio::fs::write(&df_path, serde_json::to_string_pretty(&self.doc_freq)?).await?;

        let td_path = self.config.vector_db_path.join("total_docs.json");
        tokio::fs::write(&td_path, serde_json::to_string(&self.total_docs)?).await?;

        Ok(())
    }
}

/// Tokenize text: lowercase, strip punctuation, filter short words
fn tokenize(text: &str) -> Vec<String> {
    let cleaned: String = text
        .to_lowercase()
        .chars()
        .filter(|c| c.is_alphanumeric() || c.is_whitespace())
        .collect();

    cleaned
        .split_whitespace()
        .filter(|w| w.len() > 2)
        .map(|w| w.to_string())
        .collect()
}

/// Sparse TF-IDF cosine similarity between two documents
/// Uses only the shared vocabulary between query and document
fn sparse_cosine_tfidf(
    query_tf: &HashMap<&str, f32>,
    doc_tf: &HashMap<String, f32>,
    doc_freq: &HashMap<String, usize>,
    total_docs: usize,
) -> f64 {
    if total_docs == 0 {
        return 0.0;
    }

    let mut dot = 0.0_f64;
    let mut query_norm_sq = 0.0_f64;
    let mut doc_norm_sq = 0.0_f64;

    // Compute dot product over shared terms
    for (term, &q_tf) in query_tf {
        let q_tf_f64 = q_tf as f64;
        let q_idf = (total_docs as f64 / (doc_freq.get(*term).copied().unwrap_or(1) as f64).max(1.0)).ln().max(0.0);
        let q_tfidf = q_tf_f64 * q_idf;
        query_norm_sq += q_tfidf * q_tfidf;

        if let Some(&d_tf) = doc_tf.get(*term) {
            let d_tf_f64 = d_tf as f64;
            let d_idf = (total_docs as f64 / (doc_freq.get(*term).copied().unwrap_or(1) as f64).max(1.0)).ln().max(0.0);
            let d_tfidf = d_tf_f64 * d_idf;
            dot += q_tfidf * d_tfidf;
        }
    }

    // Compute doc norm over all doc terms
    for (term, &d_tf) in doc_tf {
        let d_tf_f64 = d_tf as f64;
        let d_idf = (total_docs as f64 / (doc_freq.get(term.as_str()).copied().unwrap_or(1) as f64).max(1.0)).ln().max(0.0);
        let d_tfidf = d_tf_f64 * d_idf;
        doc_norm_sq += d_tfidf * d_tfidf;
    }

    let query_norm = query_norm_sq.sqrt();
    let doc_norm = doc_norm_sq.sqrt();

    if query_norm == 0.0 || doc_norm == 0.0 {
        0.0
    } else {
        dot / (query_norm * doc_norm)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    #[test]
    fn test_sparse_cosine_tfidf() {
        // Identical terms across 2 documents — IDF = ln(2/2) = 0, so similarity = 0
        // Use df < total_docs to get non-zero IDF
        let sim = sparse_cosine_tfidf(
            &HashMap::from([("a", 1.0)]),
            &HashMap::from([("a".to_string(), 1.0)]),
            &HashMap::from([("a".to_string(), 1)]),
            2, // term appears in 1 of 2 docs
        );
        assert!((sim - 1.0).abs() < 0.001, "identical single-term docs should have similarity 1.0, got {}", sim);

        // Orthogonal terms — no overlap, similarity = 0
        let sim2 = sparse_cosine_tfidf(
            &HashMap::from([("a", 1.0)]),
            &HashMap::from([("b".to_string(), 1.0)]),
            &HashMap::from([("a".to_string(), 1), ("b".to_string(), 1)]),
            2,
        );
        assert!(sim2.abs() < 0.001, "orthogonal terms should have similarity ~0, got {}", sim2);
    }

    #[tokio::test]
    async fn test_store_and_semantic_search() {
        let config = StorageConfig {
            enabled: true,
            vector_db_path: std::path::PathBuf::from("./test_data"),
            max_memory_mb: 1024,
            sessions_path: std::path::PathBuf::from("./sessions"),
        };

        let _ = std::fs::remove_dir_all(&config.vector_db_path);

        let mut storage = VectorStorage::new(&config).unwrap();

        let mut metadata1 = HashMap::new();
        metadata1.insert("title".to_string(), Value::String("AI Research".to_string()));
        metadata1.insert("url".to_string(), Value::String("https://example.com/ai".to_string()));

        storage.store("doc1", "Machine learning and artificial intelligence research papers", &metadata1).await.unwrap();

        let mut metadata2 = HashMap::new();
        metadata2.insert("title".to_string(), Value::String("Climate Science".to_string()));
        metadata2.insert("url".to_string(), Value::String("https://example.com/climate".to_string()));

        storage.store("doc2", "Climate change and global warming studies", &metadata2).await.unwrap();

        // Search for AI-related content
        let results = storage.semantic_search("machine learning artificial intelligence", 10).await.unwrap();
        assert!(!results.is_empty(), "search should return results");
        assert_eq!(results[0].id, "doc1");
        assert_eq!(results[0].title, "AI Research");
        assert!(results[0].relevance > 0.1);

        // Search for climate-related content
        let results2 = storage.semantic_search("climate warming", 10).await.unwrap();
        assert!(!results2.is_empty(), "climate search should return results");
        assert_eq!(results2[0].id, "doc2");
        assert_eq!(results2[0].title, "Climate Science");
        assert!(results2[0].relevance > 0.1);

        let _ = std::fs::remove_dir_all(&config.vector_db_path);
    }
}
