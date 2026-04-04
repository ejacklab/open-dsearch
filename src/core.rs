use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;
use chrono::{DateTime, Utc};
use regex::Regex;

/// Core research engine for the DSearch platform
#[derive(Debug, Clone)]
pub struct ResearchEngine {
    config: Config,
    models: ModelRegistry,
    storage: Option<VectorStorage>,
    skills: SkillsRegistry,
}

impl ResearchEngine {
    pub fn new(config: Config) -> Result<Self> {
        let models = ModelRegistry::new(&config)?;
        let storage = if config.storage.enabled {
            Some(VectorStorage::new(&config.storage)?)
        } else {
            None
        };
        let skills = SkillsRegistry::new(&config.skills)?;

        Ok(Self {
            config,
            models,
            storage,
            skills,
        })
    }

    /// Execute a comprehensive research task
    pub async fn execute_research(&mut self, task: ResearchTask) -> Result<ResearchResult> {
        tracing::info!("🔬 Starting research task: {}", task.title);

        let mut result = ResearchResult {
            id: task.id.clone(),
            title: task.title.clone(),
            query: task.query.clone(),
            status: "in_progress".to_string(),
            start_time: Utc::now(),
            end_time: None,
            sources: Vec::new(),
            insights: Vec::new(),
            recommendations: Vec::new(),
            artifacts: Vec::new(),
            confidence_score: 0.0,
        };

        // Phase 1: Multi-model search
        tracing::info!("🌐 Phase 1: Multi-model search");
        let search_results = self.multi_model_search(&task.query, &task.parameters).await?;
        result.sources.extend(search_results.items.clone());

        // Phase 2: Content analysis and aggregation
        tracing::info!("📊 Phase 2: Content analysis");
        let analysis = self.analyze_content(&search_results).await?;
        result.insights.extend(analysis.insights.clone());

        // Phase 3: Semantic analysis using vector storage
        if let Some(ref storage) = &self.storage {
            tracing!("🔍 Phase 3: Semantic analysis");
            let semantic_results = storage.semantic_search(&task.query, 20).await?;
            result.insights.extend(semantic_results.into_iter().map(|item| {
                Insight {
                    id: item.id,
                    title: item.title,
                    content: item.content,
                    confidence: item.score,
                    source: "semantic".to_string(),
                    timestamp: Utc::now(),
                }
            }).collect());
        }

        // Phase 4: Skill-based analysis
        tracing::info!("🛠️  Phase 4: Skill-based analysis");
        for skill_name in &task.skills {
            if let Some(skill_result) = self.execute_skill(skill_name, &task.query).await? {
                result.insights.extend(skill_result.insights);
                result.artifacts.extend(skill_result.artifacts);
            }
        }

        // Phase 5: Generate insights and recommendations
        tracing::info!("💡 Phase 5: Generate insights and recommendations");
        let final_analysis = self.generate_final_analysis(&result).await?;
        result.recommendations.extend(final_analysis.recommendations);
        result.confidence_score = final_analysis.confidence_score;

        // Update result status
        result.status = "completed".to_string();
        result.end_time = Some(Utc::now());

        // Save results
        self.save_research_result(&result).await?;

        Ok(result)
    }

    /// Perform multi-model search across all configured AI models
    async fn multi_model_search(&self, query: &str, parameters: &ResearchParameters) -> Result<SearchResults> {
        let mut all_results = Vec::new();
        let mut successful_models = Vec::new();

        // Execute searches in parallel
        let mut search_tasks = Vec::new();

        for model_name in self.models.list_available() {
            let query = query.to_string();
            let parameters = parameters.clone();
            
            search_tasks.push(async move {
                let model = // This would get the model from registry
                    if let Some(model) = crate::models::ModelRegistry::new() {
                        model
                    } else {
                        return Err(anyhow::anyhow!("Model not found"));
                    }
                
                let search_params = crate::models::SearchParams {
                    query,
                    models: vec![model_name.clone()],
                    max_results: parameters.max_results,
                    timeout_secs: parameters.timeout,
                };

                crate::models::ModelRegistry::search(&model, &search_params.query, search_params).await
            });
        }

        // Execute all searches concurrently
        let search_results = futures::future::join_all(search_tasks).await;

        // Collect results
        for (model_name, result) in search_results.into_iter().enumerate() {
            match result {
                Ok(results) => {
                    all_results.extend(results.items);
                    successful_models.push(model_name);
                }
                Err(e) => {
                    tracing::warn!("Search failed for model {}: {}", model_name, e);
                }
            }
        }

        // Deduplicate and rank results
        let deduplicated_results = self.deduplicate_results(all_results);
        let ranked_results = self.rank_by_relevance(deduplicated_results);

        Ok(SearchResults {
            query: query.to_string(),
            items: ranked_results,
            total: ranked_results.len(),
            models: successful_models,
            timestamp: Utc::now(),
        })
    }

    /// Execute a specific research skill
    async fn execute_skill(&self, skill_name: &str, query: &str) -> Result<Option<SkillExecutionResult>> {
        if let Some(skill) = self.skills.get(skill_name) {
            let context = crate::skills::SkillContext {
                query: query.to_string(),
                parameters: HashMap::new(),
                previous_results: Vec::new(),
                metadata: HashMap::new(),
            };

            let result = skill.execute(context).await?;
            
            Ok(Some(SkillExecutionResult {
                skill_name: skill_name.to_string(),
                output: result.output,
                artifacts: result.artifacts,
                insights: vec![],
                confidence: 0.8,
            }))
        } else {
            tracing::warn!("Skill not found: {}", skill_name);
            Ok(None)
        }
    }

    /// Deduplicate search results
    fn deduplicate_results(&self, results: Vec<SearchItem>) -> Vec<SearchItem> {
        let mut unique_results = Vec::new();
        let mut seen_urls = std::collections::HashSet::new();
        let mut seen_titles = std::collections::HashSet::new();

        for mut result in results {
            let content_hash = self.hash_content(&result.content);
            
            // Remove duplicate content
            if seen_urls.contains(&result.url) || seen_titles.contains(&result.title) {
                continue;
            }

            seen_urls.insert(result.url.clone());
            seen_titles.insert(result.title.clone());
            unique_results.push(result);
        }

        unique_results
    }

    /// Rank search results by relevance
    fn rank_by_relevance(&self, results: Vec<SearchItem>) -> Vec<SearchItem> {
        let mut mut_results = results;
        
        mut_results.sort_by(|a, b| {
            b.relevance.partial_cmp(&a.relevance).unwrap_or(std::cmp::Ordering::Equal)
        });

        mut_results
    }

    /// Generate final analysis and recommendations
    async fn generate_final_analysis(&self, result: &ResearchResult) -> Result<FinalAnalysis> {
        let mut recommendations = Vec::new();
        let confidence_score = self.calculate_confidence(result);

        // Generate recommendations based on insights
        for insight in &result.insights {
            if insight.confidence > 0.7 {
                recommendations.push(Recommendation {
                    id: format!("rec_{}", insight.id),
                    title: format!("Further research: {}", insight.title),
                    description: insight.content.clone(),
                    priority: insight.confidence,
                    action: "research".to_string(),
                });
            }
        }

        Ok(FinalAnalysis {
            recommendations,
            confidence_score,
            summary: self.generate_summary(result),
        })
    }

    /// Calculate overall confidence score
    fn calculate_confidence(&self, result: &ResearchResult) -> f64 {
        if result.insights.is_empty() {
            return 0.0;
        }

        let total_confidence: f64 = result.insights.iter()
            .map(|insight| insight.confidence)
            .sum();
        
        total_confidence / result.insights.len() as f64
    }

    /// Generate a summary of research findings
    fn generate_summary(&self, result: &ResearchResult) -> String {
        format!(
            "Research completed for: {}\n\nKey findings:\n1. {} sources analyzed\n2. {} insights generated\n3. {} recommendations provided\n\nOverall confidence: {:.1}%",
            result.title,
            result.sources.len(),
            result.insights.len(),
            result.recommendations.len(),
            result.confidence_score * 100.0
        )
    }

    /// Save research result to storage
    async fn save_research_result(&self, result: &ResearchResult) -> Result<()> {
        if let Some(ref storage) = &self.storage {
            let metadata = serde_json::json!({
                "title": result.title,
                "query": result.query,
                "status": result.status,
                "confidence": result.confidence_score,
                "sources_count": result.sources.len(),
                "insights_count": result.insights.len(),
            });

            storage.store(
                &result.id,
                &serde_json::to_string(result)?,
                &metadata.into(),
            ).await?;
        }

        Ok(())
    }

    /// Hash content for deduplication
    fn hash_content(&self, content: &str) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::Hasher;

        let mut hasher = DefaultHasher::new();
        hasher.write(content.as_bytes());
        format!("{:x}", hasher.finish())
    }

    /// Get research task history
    pub async fn get_research_history(&self, limit: usize) -> Result<Vec<ResearchResult>> {
        let mut history = Vec::new();
        
        if let Some(ref storage) = &self.storage {
            let all_embeddings = storage.list();
            
            for embedding_id in all_embeddings.into_iter().take(limit) {
                if let Some(embedding) = storage.get(&embedding_id).await {
                    // Parse embedding content as ResearchResult
                    match serde_json::from_str(&embedding.content) {
                        Ok(result) => history.push(result),
                        Err(e) => {
                            tracing::warn!("Failed to parse research result: {}", e);
                        }
                    }
                }
            }
        }

        Ok(history)
    }
}

/// Research task definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResearchTask {
    pub id: String,
    pub title: String,
    pub query: String,
    pub parameters: ResearchParameters,
    pub skills: Vec<String>,
    pub priority: TaskPriority,
}

/// Research parameters
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResearchParameters {
    pub max_results: usize,
    pub timeout: u64,
    pub enable_vector_search: bool,
    pub enable_skills: bool,
    pub custom_parameters: HashMap<String, serde_json::Value>,
}

/// Task priority
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaskPriority {
    Low,
    Medium,
    High,
    Critical,
}

/// Research result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResearchResult {
    pub id: String,
    pub title: String,
    pub query: String,
    pub status: String,
    pub start_time: DateTime<Utc>,
    pub end_time: Option<DateTime<Utc>>,
    pub sources: Vec<SearchItem>,
    pub insights: Vec<Insight>,
    pub recommendations: Vec<Recommendation>,
    pub artifacts: Vec<String>,
    pub confidence_score: f64,
}

/// Individual insight
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Insight {
    pub id: String,
    pub title: String,
    pub content: String,
    pub confidence: f64,
    pub source: String,
    pub timestamp: DateTime<Utc>,
}

/// Recommendation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Recommendation {
    pub id: String,
    pub title: String,
    pub description: String,
    pub priority: f64,
    pub action: String,
}

/// Search results from multiple models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResults {
    pub query: String,
    pub items: Vec<SearchItem>,
    pub total: usize,
    pub models: Vec<String>,
    pub timestamp: DateTime<Utc>,
}

/// Skill execution result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillExecutionResult {
    pub skill_name: String,
    pub output: String,
    pub artifacts: Vec<String>,
    pub insights: Vec<Insight>,
    pub confidence: f64,
}

/// Final analysis result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FinalAnalysis {
    pub recommendations: Vec<Recommendation>,
    pub confidence_score: f64,
    pub summary: String,
}

/// Enhanced content processing
pub struct ContentProcessor;

impl ContentProcessor {
    /// Extract key entities from text
    pub fn extract_entities(text: &str) -> Vec<Entity> {
        let mut entities = Vec::new();
        
        // Simple entity extraction patterns
        let patterns = vec![
            (r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", "PERSON"),
            (r"\b[A-Z]{2,}\b", "ORGANIZATION"),
            (r"\b\d{4}\b", "DATE"),
            (r"\b[A-Z]{2,}\b", "LOCATION"),
        ];

        for (pattern, entity_type) in patterns {
            if let Ok(regex) = Regex::new(pattern) {
                for capture in regex.find_iter(text) {
                    entities.push(Entity {
                        text: capture.as_str().to_string(),
                        r#type: entity_type.to_string(),
                        start: capture.start(),
                        end: capture.end(),
                    });
                }
            }
        }

        entities
    }

    /// Summarize text
    pub fn summarize_text(text: &str, max_sentences: usize) -> String {
        let sentences = TextProcessor::split_into_sentences(text);
        
        if sentences.len() <= max_sentences {
            sentences.join(". ")
        } else {
            // Simple summarization - take first and last sentences
            let mut summary = sentences[..(max_sentences/2)].to_vec();
            summary.extend(sentences[sentences.len() - (max_sentences/2)..].to_vec());
            summary.join(". ")
        }
    }
}

/// Entity extracted from text
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entity {
    pub text: String,
    pub r#type: String,
    pub start: usize,
    pub end: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_research_engine_creation() {
        let config = Config::default();
        let engine = ResearchEngine::new(config);
        assert!(engine.is_ok());
    }

    #[test]
    fn test_content_processing() {
        let text = "John Doe works at Google in California. The year is 2024.";
        let entities = ContentProcessor::extract_entities(text);
        
        assert!(!entities.is_empty());
        assert!(entities.iter().any(|e| e.text == "John Doe"));
    }
}