use crate::models::SkillsConfig;
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use reqwest::Client;
use scraper::{Html, Selector};
use std::time::Duration;
use tokio::time::sleep;

/// Skills registry for managing research skills
#[derive(Debug)]
pub struct SkillsRegistry {
    skills: HashMap<String, Box<dyn Skill>>,
    #[allow(dead_code)]
    config: SkillsConfig,
}

impl SkillsRegistry {
    pub fn new(config: &SkillsConfig) -> Result<Self> {
        let mut skills: HashMap<String, Box<dyn Skill>> = HashMap::new();
        
        // Load built-in skills
        skills.insert("web-research".to_string(), Box::new(WebResearchSkill::new()));
        skills.insert("literature-review".to_string(), Box::new(LiteratureReviewSkill::new()));
        skills.insert("data-analysis".to_string(), Box::new(DataAnalysisSkill::new()));
        skills.insert("code-review".to_string(), Box::new(CodeReviewSkill::new()));
        skills.insert("policy-research".to_string(), Box::new(PolicyResearchSkill::new()));
        
        // Load custom skills if enabled
        if config.auto_load {
            Self::load_custom_skills(&mut skills, config)?;
        }

        Ok(Self { skills, config: config.clone() })
    }

    pub fn get(&self, skill_name: &str) -> Option<&dyn Skill> {
        self.skills.get(skill_name).map(|skill| skill.as_ref())
    }

    pub fn list_available(&self) -> Vec<String> {
        self.skills.keys().cloned().collect()
    }

    pub async fn execute(&self, skill_name: &str, context: SkillContext) -> Result<SkillResult> {
        if let Some(skill) = self.get(skill_name) {
            skill.execute(context).await
        } else {
            Err(anyhow::anyhow!("Skill '{}' not found", skill_name))
        }
    }

    fn load_custom_skills(skills: &mut HashMap<String, Box<dyn Skill>>, config: &crate::models::SkillsConfig) -> Result<()> {
        let skills_path = &config.skills_path;
        
        if !skills_path.exists() {
            return Ok(());
        }

        for entry in std::fs::read_dir(skills_path)? {
            let entry = entry?;
            let path = entry.path();
            
            if path.extension().and_then(|s| s.to_str()) == Some("rs") {
                // This would be where we dynamically load Rust skill files
                // For now, we'll just add placeholder skills
                let skill_name = path.file_stem().unwrap().to_str().unwrap();
                skills.insert(skill_name.to_string(), Box::new(CustomSkill::new(skill_name)));
            }
        }

        Ok(())
    }
}

/// Skill trait for implementing research skills
#[async_trait::async_trait]
pub trait Skill: Send + Sync + std::fmt::Debug {
    fn name(&self) -> &str;
    fn description(&self) -> &str;
    async fn execute(&self, context: SkillContext) -> Result<SkillResult>;
    fn parameters_schema(&self) -> SkillSchema;
}

/// Skill execution context
#[derive(Debug, Clone)]
pub struct SkillContext {
    pub query: String,
    pub parameters: HashMap<String, serde_json::Value>,
    pub previous_results: Vec<crate::SearchResults>,
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Skill execution result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillResult {
    pub output: String,
    pub artifacts: Vec<String>,
    pub next_actions: Vec<String>,
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Skill schema for parameter validation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillSchema {
    pub parameters: Vec<SchemaParameter>,
    pub required: Vec<String>,
}

/// Schema parameter definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchemaParameter {
    pub name: String,
    pub r#type: String,
    pub description: String,
    pub required: bool,
    pub default_value: Option<serde_json::Value>,
    pub enum_values: Option<Vec<String>>,
}

/// Web research skill with real web scraping capabilities
#[derive(Debug)]
pub struct WebResearchSkill {
    name: String,
    description: String,
    client: Client,
}

impl WebResearchSkill {
    fn new() -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(30))
            .user_agent("OpenDSearch/1.0 (Research Bot; +https://github.com/ejacklab/open-dsearch)")
            .build()
            .expect("Failed to build HTTP client");
        
        Self {
            name: "web-research".to_string(),
            description: "Automated web scraping and analysis".to_string(),
            client,
        }
    }

    /// Fetch and extract content from a URL
    async fn fetch_url(&self, url: &str) -> Result<String> {
        let response = self.client.get(url).send().await?;
        let status = response.status();
        
        if !status.is_success() {
            return Err(anyhow::anyhow!("HTTP {} for {}", status, url));
        }
        
        let content_type = response
            .headers()
            .get("content-type")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("text/html");
        
        if !content_type.contains("text/html") {
            return Err(anyhow::anyhow!("Non-HTML content type: {}", content_type));
        }
        
        let html = response.text().await?;
        let text = self.extract_text(&html);
        
        Ok(text)
    }

    /// Extract clean text from HTML
    fn extract_text(&self, html: &str) -> String {
        let document = Html::parse_document(html);
        
        // Try to get main content first
        let main_selectors = [
            "main",
            "article",
            "[role='main']",
            ".content",
            "#content",
            ".post-content",
            ".entry-content",
            ".article-content",
        ];
        
        for selector_str in &main_selectors {
            if let Ok(selector) = Selector::parse(selector_str) {
                if let Some(element) = document.select(&selector).next() {
                    let text: String = element.text().collect();
                    return self.clean_text(&text);
                }
            }
        }
        
        // Fallback to body content
        if let Ok(body_selector) = Selector::parse("body") {
            if let Some(body) = document.select(&body_selector).next() {
                let text: String = body.text().collect();
                return self.clean_text(&text);
            }
        }
        
        // Last resort: all text
        let text: String = document.root_element().text().collect();
        self.clean_text(&text)
    }

    /// Clean and normalize extracted text
    fn clean_text(&self, text: &str) -> String {
        text.lines()
            .map(|line| line.trim())
            .filter(|line| !line.is_empty())
            .filter(|line| !line.starts_with("<!--"))
            .filter(|line| line.len() > 10) // Filter out very short lines
            .collect::<Vec<_>>()
            .join("\n")
            .replace("\n\n\n", "\n\n") // Remove excessive newlines
    }

    /// Extract metadata from HTML
    #[allow(dead_code)]
    fn extract_metadata(&self, html: &str) -> HashMap<String, String> {
        let document = Html::parse_document(html);
        let mut metadata = HashMap::new();
        
        // Title
        if let Ok(title_selector) = Selector::parse("title") {
            if let Some(title) = document.select(&title_selector).next() {
                metadata.insert("title".to_string(), title.text().collect::<String>().trim().to_string());
            }
        }
        
        // Meta description
        if let Ok(desc_selector) = Selector::parse("meta[name='description']") {
            if let Some(desc) = document.select(&desc_selector).next() {
                if let Some(content) = desc.value().attr("content") {
                    metadata.insert("description".to_string(), content.to_string());
                }
            }
        }
        
        metadata
    }

    /// Check robots.txt (basic implementation)
    async fn check_robots_txt(&self, url: &str) -> Result<bool> {
        // Parse URL to get base domain
        if let Ok(parsed) = url.parse::<reqwest::Url>() {
            if let Some(host) = parsed.host_str() {
                let robots_url = format!("{}://{}/robots.txt", parsed.scheme(), host);
                
                match self.client.get(&robots_url).send().await {
                    Ok(response) if response.status().is_success() => {
                        if let Ok(content) = response.text().await {
                            // Check if the path is disallowed
                            let path = parsed.path();
                            return Ok(!content.contains(&format!("Disallow: {}", path)));
                        }
                    }
                    _ => {
                        // If robots.txt doesn't exist or fails, assume allowed
                        return Ok(true);
                    }
                }
            }
        }
        
        Ok(true)
    }
}

#[async_trait::async_trait]
impl Skill for WebResearchSkill {
    fn name(&self) -> &str {
        &self.name
    }

    fn description(&self) -> &str {
        &self.description
    }

    async fn execute(&self, context: SkillContext) -> Result<SkillResult> {
        println!("🌐 Executing web research for: {}", context.query);
        
        // Get URLs to scrape from parameters or use a mock list for now
        let urls: Vec<String> = context.parameters
            .get("urls")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_else(|| {
                // For demonstration, we'll note that real implementation would
                // use a search API or web search to get URLs
                vec![]
            });
        
        let mut scraped_results = Vec::new();
        let mut errors = Vec::new();
        
        for url in urls.iter().take(5) { // Limit to 5 URLs
            println!("  📄 Fetching: {}", url);
            
            // Rate limiting - be polite
            sleep(Duration::from_millis(1000)).await;
            
            // Check robots.txt
            match self.check_robots_txt(url).await {
                Ok(false) => {
                    println!("  ⛔ Blocked by robots.txt: {}", url);
                    continue;
                }
                Ok(true) => {}
                Err(e) => {
                    println!("  ⚠️  Could not check robots.txt: {}", e);
                }
            }
            
            // Fetch and extract content
            match self.fetch_url(url).await {
                Ok(content) => {
                    let summary = if content.len() > 500 {
                        format!("{}...", &content[..500])
                    } else {
                        content.clone()
                    };
                    
                    scraped_results.push(format!("\nSource: {}\n---\n{}", url, summary));
                }
                Err(e) => {
                    errors.push(format!("{}: {}", url, e));
                }
            }
        }
        
        // Build the analysis
        let mut analysis = format!(
            "🔍 Web Research Results for: {}\n\n",
            context.query
        );
        
        if scraped_results.is_empty() {
            analysis.push_str("No URLs were scraped. To use web research, provide URLs in the 'urls' parameter.\n\n");
            analysis.push_str("Example usage:\n");
            analysis.push_str("{\"urls\": [\"https://example.com/article1\", \"https://example.com/article2\"]}\n");
        } else {
            analysis.push_str(&format!("Successfully scraped {} of {} URLs\n\n", 
                scraped_results.len(), urls.len()));
            
            for result in &scraped_results {
                analysis.push_str(result);
                analysis.push_str("\n\n");
            }
        }
        
        if !errors.is_empty() {
            analysis.push_str("\n⚠️ Errors encountered:\n");
            for error in errors {
                analysis.push_str(&format!("  - {}\n", error));
            }
        }
        
        // Add next actions based on results
        let next_actions = if scraped_results.len() >= 3 {
            vec!["data-analysis".to_string(), "literature-review".to_string()]
        } else {
            vec!["web-research".to_string()] // Suggest trying again with more sources
        };

        let mut metadata = HashMap::new();
        metadata.insert("urls_scraped".to_string(), serde_json::json!(scraped_results.len()));
        metadata.insert("urls_attempted".to_string(), serde_json::json!(urls.len()));

        Ok(SkillResult {
            output: analysis,
            artifacts: vec!["web-research-results.md".to_string()],
            next_actions,
            metadata,
        })
    }

    fn parameters_schema(&self) -> SkillSchema {
        SkillSchema {
            parameters: vec![
                SchemaParameter {
                    name: "max_results".to_string(),
                    r#type: "number".to_string(),
                    description: "Maximum number of results to return".to_string(),
                    required: false,
                    default_value: Some(serde_json::Value::Number(10.into())),
                    enum_values: None,
                },
                SchemaParameter {
                    name: "search_engines".to_string(),
                    r#type: "array".to_string(),
                    description: "List of search engines to use".to_string(),
                    required: false,
                    default_value: Some(serde_json::Value::Array(vec![
                        serde_json::Value::String("google".to_string()),
                        serde_json::Value::String("bing".to_string()),
                        serde_json::Value::String("duckduckgo".to_string()),
                    ])),
                    enum_values: None,
                },
                SchemaParameter {
                    name: "timeout".to_string(),
                    r#type: "number".to_string(),
                    description: "Search timeout in seconds".to_string(),
                    required: false,
                    default_value: Some(serde_json::Value::Number(30.into())),
                    enum_values: None,
                },
            ],
            required: vec!["query".to_string()],
        }
    }
}

/// Literature review skill
#[derive(Debug)]
pub struct LiteratureReviewSkill {
    name: String,
    description: String,
}

impl LiteratureReviewSkill {
    fn new() -> Self {
        Self {
            name: "literature-review".to_string(),
            description: "Academic paper search and summarization".to_string(),
        }
    }
}

#[async_trait::async_trait]
impl Skill for LiteratureReviewSkill {
    fn name(&self) -> &str {
        &self.name
    }

    fn description(&self) -> &str {
        &self.description
    }

    async fn execute(&self, context: SkillContext) -> Result<SkillResult> {
        println!("📚 Executing literature review for: {}", context.query);
        
        let analysis = format!(
            "Literature review completed for: {}\n\nThis would:\n1. Search academic databases (PubMed, arXiv, IEEE, etc.)\n2. Extract and summarize key papers\n3. Identify research gaps and trends\n4. Provide citations and bibliographic information\n\nResearch focus: {}", 
            context.query, context.query
        );

        Ok(SkillResult {
            output: analysis,
            artifacts: vec!["literature-review-summary.md".to_string()],
            next_actions: vec!["data-analysis".to_string()],
            metadata: HashMap::new(),
        })
    }

    fn parameters_schema(&self) -> SkillSchema {
        SkillSchema {
            parameters: vec![
                SchemaParameter {
                    name: "databases".to_string(),
                    r#type: "array".to_string(),
                    description: "Academic databases to search".to_string(),
                    required: false,
                    default_value: Some(serde_json::Value::Array(vec![
                        serde_json::Value::String("pubmed".to_string()),
                        serde_json::Value::String("arxiv".to_string()),
                        serde_json::Value::String("ieee".to_string()),
                    ])),
                    enum_values: None,
                },
                SchemaParameter {
                    name: "year_range".to_string(),
                    r#type: "object".to_string(),
                    description: "Publication year range filter".to_string(),
                    required: false,
                    default_value: Some(serde_json::Value::Object(serde_json::Map::new())),
                    enum_values: None,
                },
            ],
            required: vec!["query".to_string()],
        }
    }
}

/// Data analysis skill
#[derive(Debug)]
pub struct DataAnalysisSkill {
    name: String,
    description: String,
}

impl DataAnalysisSkill {
    fn new() -> Self {
        Self {
            name: "data-analysis".to_string(),
            description: "Statistical analysis and visualization".to_string(),
        }
    }
}

#[async_trait::async_trait]
impl Skill for DataAnalysisSkill {
    fn name(&self) -> &str {
        &self.name
    }

    fn description(&self) -> &str {
        &self.description
    }

    async fn execute(&self, context: SkillContext) -> Result<SkillResult> {
        println!("📊 Executing data analysis for: {}", context.query);
        
        let analysis = format!(
            "Data analysis completed for: {}\n\nThis would:\n1. Perform statistical analysis on collected data\n2. Generate charts and visualizations\n3. Identify patterns and correlations\n4. Provide insights and recommendations\n\nAnalysis scope: {}", 
            context.query, context.query
        );

        Ok(SkillResult {
            output: analysis,
            artifacts: vec!["data-analysis-report.md".to_string()],
            next_actions: vec![],
            metadata: HashMap::new(),
        })
    }

    fn parameters_schema(&self) -> SkillSchema {
        SkillSchema {
            parameters: vec![
                SchemaParameter {
                    name: "analysis_type".to_string(),
                    r#type: "string".to_string(),
                    description: "Type of analysis to perform".to_string(),
                    required: false,
                    default_value: Some(serde_json::Value::String("descriptive".to_string())),
                    enum_values: Some(vec![
                        "descriptive".to_string(),
                        "inferential".to_string(),
                        "predictive".to_string(),
                    ]),
                },
            ],
            required: vec![],
        }
    }
}

/// Code review skill
#[derive(Debug)]
pub struct CodeReviewSkill {
    name: String,
    description: String,
}

impl CodeReviewSkill {
    fn new() -> Self {
        Self {
            name: "code-review".to_string(),
            description: "Programming language analysis".to_string(),
        }
    }
}

#[async_trait::async_trait]
impl Skill for CodeReviewSkill {
    fn name(&self) -> &str {
        &self.name
    }

    fn description(&self) -> &str {
        &self.description
    }

    async fn execute(&self, context: SkillContext) -> Result<SkillResult> {
        println!("💻 Executing code review for: {}", context.query);
        
        let analysis = format!(
            "Code review completed for: {}\n\nThis would:\n1. Analyze code for best practices\n2. Identify security vulnerabilities\n3. Suggest performance improvements\n4. Check for code consistency and standards\n\nReview focus: {}", 
            context.query, context.query
        );

        Ok(SkillResult {
            output: analysis,
            artifacts: vec!["code-review-report.md".to_string()],
            next_actions: vec!["web-research".to_string()],
            metadata: HashMap::new(),
        })
    }

    fn parameters_schema(&self) -> SkillSchema {
        SkillSchema {
            parameters: vec![
                SchemaParameter {
                    name: "programming_languages".to_string(),
                    r#type: "array".to_string(),
                    description: "Programming languages to analyze".to_string(),
                    required: false,
                    default_value: Some(serde_json::Value::Array(vec![])),
                    enum_values: None,
                },
            ],
            required: vec![],
        }
    }
}

/// Policy research skill
#[derive(Debug)]
pub struct PolicyResearchSkill {
    name: String,
    description: String,
}

impl PolicyResearchSkill {
    fn new() -> Self {
        Self {
            name: "policy-research".to_string(),
            description: "Government document analysis".to_string(),
        }
    }
}

#[async_trait::async_trait]
impl Skill for PolicyResearchSkill {
    fn name(&self) -> &str {
        &self.name
    }

    fn description(&self) -> &str {
        &self.description
    }

    async fn execute(&self, context: SkillContext) -> Result<SkillResult> {
        println!("🏛️ Executing policy research for: {}", context.query);
        
        let analysis = format!(
            "Policy research completed for: {}\n\nThis would:\n1. Search government databases and archives\n2. Analyze policy documents and regulations\n3. Identify policy impacts and implications\n4. Provide policy recommendations\n\nResearch scope: {}", 
            context.query, context.query
        );

        Ok(SkillResult {
            output: analysis,
            artifacts: vec!["policy-research-summary.md".to_string()],
            next_actions: vec![],
            metadata: HashMap::new(),
        })
    }

    fn parameters_schema(&self) -> SkillSchema {
        SkillSchema {
            parameters: vec![
                SchemaParameter {
                    name: "jurisdictions".to_string(),
                    r#type: "array".to_string(),
                    description: "Geographic jurisdictions to search".to_string(),
                    required: false,
                    default_value: Some(serde_json::Value::Array(vec![])),
                    enum_values: None,
                },
            ],
            required: vec![],
        }
    }
}

/// Custom skill placeholder
#[derive(Debug)]
pub struct CustomSkill {
    name: String,
    description: String,
}

impl CustomSkill {
    fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            description: "Custom research skill".to_string(),
        }
    }
}

#[async_trait::async_trait]
impl Skill for CustomSkill {
    fn name(&self) -> &str {
        &self.name
    }

    fn description(&self) -> &str {
        &self.description
    }

    async fn execute(&self, context: SkillContext) -> Result<SkillResult> {
        Ok(SkillResult {
            output: format!("Custom skill '{}' executed for query: {}", self.name, context.query),
            artifacts: vec![format!("custom-skill-{}.md", self.name)],
            next_actions: vec![],
            metadata: HashMap::new(),
        })
    }

    fn parameters_schema(&self) -> SkillSchema {
        SkillSchema {
            parameters: vec![],
            required: vec![],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_skills_registry() {
        let config = SkillsConfig {
            skills_path: std::path::PathBuf::from("./skills"),
            auto_load: true,
        };

        let registry = SkillsRegistry::new(&config).unwrap();
        
        assert_eq!(registry.list_available().len(), 5); // Built-in skills
        
        let context = SkillContext {
            query: "test query".to_string(),
            parameters: HashMap::new(),
            previous_results: vec![],
            metadata: HashMap::new(),
        };

        let result = registry.execute("web-research", context).await.unwrap();
        assert!(result.output.contains("test query"));
    }
}