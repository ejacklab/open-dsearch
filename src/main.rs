use clap::{Parser, Subcommand};
use dsearch::*;
use std::path::PathBuf;

#[derive(Parser)]
#[command(
    name = "dsearch",
    about = "Open DSearch - A cutting-edge research platform for AI agents",
    version,
    author
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Configuration file path
    #[arg(short, long, global = true, default_value = "dsearch.toml")]
    config: PathBuf,

    /// Verbose output
    #[arg(short, long, global = true)]
    verbose: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Initialize a new DSearch project
    Init {
        /// Force overwrite existing configuration
        #[arg(long)]
        force: bool,
    },

    /// Perform a multi-model search
    Search {
        /// Search query
        #[arg(required = true)]
        query: String,

        /// Target specific models (comma-separated)
        #[arg(long, default_value = "all")]
        models: String,

        /// Maximum number of results
        #[arg(long, default_value = "10")]
        max_results: usize,

        /// Timeout in seconds
        #[arg(long, default_value = "30")]
        timeout: u64,

        /// Save session with this ID
        #[arg(long)]
        save: Option<String>,
    },

    /// Interactive research session
    Interactive {
        /// Load existing session
        #[arg(long)]
        load: Option<String>,

        /// Auto-save session when done
        #[arg(long)]
        save: Option<String>,
    },

    /// Semantic search using vector database
    Semantic {
        /// Search query
        #[arg(required = true)]
        query: String,

        /// Maximum number of results
        #[arg(long, default_value = "10")]
        limit: usize,

        /// Session ID to save results
        #[arg(long)]
        save: Option<String>,
    },

    /// List available models
    Models,

    /// Manage saved sessions
    Session {
        #[command(subcommand)]
        action: SessionActions,
    },

    /// Execute a research skill
    Skill {
        /// Skill name or path
        #[arg(required = true)]
        skill: String,

        /// Skill parameters (JSON)
        #[arg(long)]
        params: Option<String>,
    },

    /// Configuration management
    Config {
        #[command(subcommand)]
        action: ConfigActions,
    },
}

#[derive(Subcommand)]
enum SessionActions {
    /// List saved sessions
    List,

    /// Load a session
    Load {
        /// Session ID
        #[arg(required = true)]
        id: String,
    },

    /// Delete a session
    Delete {
        /// Session ID
        #[arg(required = true)]
        id: String,

        /// Confirm deletion
        #[arg(long)]
        confirm: bool,
    },
}

#[derive(Subcommand)]
enum ConfigActions {
    /// Show current configuration
    Show,

    /// Validate configuration
    Validate,

    /// Export configuration template
    Template {
        /// Output file path
        #[arg(short, long, default_value = "dsearch.toml")]
        output: PathBuf,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialize logging
    if cli.verbose {
        tracing_subscriber::fmt::init();
    }

    match cli.command {
        Commands::Init { force } => {
            init_config(&cli.config, force)?;
        }

        Commands::Search { query, models, max_results, timeout, save } => {
            let config = load_config(&cli.config)?;
            let dsearch = DSearch::new(config)?;
            
            let model_list = if models == "all" {
                vec!["gemini", "xai", "minimax"]
            } else {
                models.split(',').map(|s| s.trim().to_string()).collect()
            };

            let params = SearchParams {
                query,
                models: model_list,
                max_results,
                timeout_secs: timeout,
            };

            let results = dsearch.search(&params.query, params.clone()).await?;
            
            print_results(&results);
            
            if let Some(session_id) = save {
                dsearch.save_session(&session_id, &results).await?;
                println!("Session saved as: {}", session_id);
            }
        }

        Commands::Interactive { load, save } => {
            let config = load_config(&cli.config)?;
            let dsearch = DSearch::new(config)?;
            
            interactive_search(&dsearch, load, save).await?;
        }

        Commands::Semantic { query, limit, save } => {
            let config = load_config(&cli.config)?;
            let dsearch = DSearch::new(config)?;
            
            let results = dsearch.semantic_search(&query, limit).await?;
            print_results(&results);
            
            if let Some(session_id) = save {
                dsearch.save_session(&session_id, &results).await?;
                println!("Session saved as: {}", session_id);
            }
        }

        Commands::Models => {
            let config = load_config(&cli.config)?;
            let dsearch = DSearch::new(config)?;
            
            list_models(&dsearch).await?;
        }

        Commands::Session { action } => {
            match action {
                SessionActions::List => {
                    list_sessions().await?;
                }
                SessionActions::Load { id } => {
                    let config = load_config(&cli.config)?;
                    let dsearch = DSearch::new(config)?;
                    
                    let results = dsearch.load_session(&id).await?;
                    print_results(&results);
                }
                SessionActions::Delete { id, confirm } => {
                    delete_session(&id, confirm).await?;
                }
            }
        }

        Commands::Skill { skill, params } => {
            let config = load_config(&cli.config)?;
            let dsearch = DSearch::new(config)?;
            
            execute_skill(&dsearch, &skill, params).await?;
        }

        Commands::Config { action } => {
            match action {
                ConfigActions::Show => {
                    show_config(&cli.config)?;
                }
                ConfigActions::Validate => {
                    validate_config(&cli.config)?;
                }
                ConfigActions::Template { output } => {
                    generate_config_template(&output)?;
                }
            }
        }
    }

    Ok(())
}

fn init_config(config_path: &PathBuf, force: bool) -> Result<()> {
    if config_path.exists() && !force {
        return Err(anyhow::anyhow!("Configuration file already exists. Use --force to overwrite."));
    }

    let template = include_str!("../config/dsearch.toml.template");
    std::fs::write(config_path, template)?;
    
    println!("✅ Configuration initialized at: {}", config_path.display());
    println!("\n📝 Edit the configuration file to add your API keys and preferences.");
    println!("   Run 'dsearch config show' to verify your configuration.");
    
    Ok(())
}

fn load_config(config_path: &PathBuf) -> Result<Config> {
    let config_content = std::fs::read_to_string(config_path)?;
    let config: Config = toml::from_str(&config_content)?;
    Ok(config)
}

fn print_results(results: &SearchResults) {
    println!("\n🔍 Search Results for: {}", results.query);
    println!("📊 Total results: {}", results.total);
    println!("🤖 Models used: {}", results.models.join(", "));
    println!("⏰ Search time: {}", results.timestamp.format("%Y-%m-%d %H:%M:%S UTC"));
    println!("{}", "─".repeat(60));

    for (i, item) in results.results.iter().enumerate() {
        println!("\n{}. [{}] {}", i + 1, item.source, item.title);
        if let Some(url) = &item.url {
            println!("   📍 {}", url);
        }
        println!("   📄 {}", item.content);
        println!("   ⭐ Relevance: {:.2}", item.relevance);
    }
}

async fn interactive_search(dsearch: &DSearch, load: Option<String>, save: Option<String>) -> Result<()> {
    println!("🚀 Welcome to Open DSearch Interactive Mode!");
    
    let mut results = if let Some(session_id) = load {
        println!("📂 Loading session: {}", session_id);
        dsearch.load_session(&session_id).await?
    } else {
        println!("💡 Enter your research queries. Type 'quit' to exit.");
        println!("💡 Use 'help' for available commands.");
        
        // Start with empty results
        SearchResults {
            query: String::new(),
            results: Vec::new(),
            total: 0,
            models: Vec::new(),
            timestamp: chrono::Utc::now(),
        }
    };

    loop {
        print!("\n🔍 dsearch> ");
        std::io::Write::flush(&mut std::io::stdout()).unwrap();
        
        let mut input = String::new();
        std::io::stdin().read_line(&mut input).unwrap();
        let input = input.trim();
        
        match input {
            "quit" | "exit" => {
                if let Some(session_id) = save {
                    dsearch.save_session(&session_id, &results).await?;
                    println!("💾 Session saved as: {}", session_id);
                }
                println!("👋 Goodbye!");
                break;
            }
            "help" => {
                print_help();
            }
            "clear" => {
                results = SearchResults {
                    query: String::new(),
                    results: Vec::new(),
                    total: 0,
                    models: Vec::new(),
                    timestamp: chrono::Utc::now(),
                };
                println!("🧹 Results cleared.");
            }
            "" => {
                continue;
            }
            _ => {
                println!("🔍 Searching for: {}", input);
                let params = SearchParams {
                    query: input.to_string(),
                    models: vec!["gemini", "xai", "minimax"],
                    max_results: 10,
                    timeout_secs: 30,
                };
                
                let new_results = dsearch.search(input, params).await?;
                results = new_results;
                print_results(&results);
            }
        }
    }
    
    Ok(())
}

fn print_help() {
    println!("📖 Available commands:");
    println!("  help       - Show this help message");
    println!("  quit/exit  - Exit interactive mode");
    println!("  clear      - Clear current results");
    println!("  <query>    - Search for the given query");
    println!("  <command>  - Any other text is treated as a search query");
}

async fn list_models(dsearch: &DSearch) -> Result<()> {
    println!("🤖 Available AI Models:");
    
    let models = dsearch.models.list_available();
    for model in models {
        println!("  ✓ {}", model);
    }
    
    Ok(())
}

async fn list_sessions() -> Result<()> {
    let sessions_dir = PathBuf::from("./sessions");
    
    if !sessions_dir.exists() {
        println!("📁 No saved sessions found.");
        return Ok(());
    }
    
    let entries = std::fs::read_dir(sessions_dir)?;
    println!("📚 Saved Sessions:");
    
    for entry in entries {
        if let Ok(entry) = entry {
            if let Some(file_name) = entry.file_name().to_str() {
                if file_name.ends_with(".json") {
                    let session_id = file_name.strip_suffix(".json").unwrap();
                    println!("  📄 {}", session_id);
                }
            }
        }
    }
    
    Ok(())
}

async fn delete_session(id: &str, confirm: bool) -> Result<()> {
    let session_file = PathBuf::from("./sessions").join(format!("{}.json", id));
    
    if !session_file.exists() {
        println!("❌ Session '{}' not found.", id);
        return Ok(());
    }
    
    if !confirm {
        print!("⚠️  Are you sure you want to delete session '{}'? (y/N): ", id);
        std::io::Write::flush(&mut std::io::stdout()).unwrap();
        
        let mut input = String::new();
        std::io::stdin().read_line(&mut input).unwrap();
        
        if input.trim().to_lowercase() != "y" {
            println!("❌ Deletion cancelled.");
            return Ok(());
        }
    }
    
    std::fs::remove_file(session_file)?;
    println!("✅ Session '{}' deleted.", id);
    
    Ok(())
}

async fn execute_skill(dsearch: &DSearch, skill_name: &str, params: Option<String>) -> Result<()> {
    println!("🛠️  Executing skill: {}", skill_name);
    
    // Parse parameters if provided
    let params_json = if let Some(params_str) = params {
        Some(serde_json::from_str(&params_str)?)
    } else {
        None
    };
    
    // This is a placeholder - actual skill execution would be implemented
    // in the skills module
    println!("🚀 Skill execution started...");
    println!("⏳ This feature is under development.");
    
    Ok(())
}

fn show_config(config_path: &PathBuf) -> Result<()> {
    println!("⚙️  Current Configuration:");
    println!("{}", "─".repeat(40));
    
    if config_path.exists() {
        let config_content = std::fs::read_to_string(config_path)?;
        println!("{}", config_content);
    } else {
        println!("❌ Configuration file not found at: {}", config_path.display());
        println!("💡 Run 'dsearch init' to create a new configuration file.");
    }
    
    Ok(())
}

fn validate_config(config_path: &PathBuf) -> Result<()> {
    println!("🔍 Validating configuration...");
    
    match load_config(config_path) {
        Ok(config) => {
            println!("✅ Configuration is valid!");
            println!("📊 Models configured: {}", 
                config.models.gemini.is_some() as i32 + 
                config.models.xai.is_some() as i32 + 
                config.models.minimax.is_some() as i32);
            println!("💾 Storage enabled: {}", config.storage.enabled);
            println!("🛠️  Skills auto-load: {}", config.skills.auto_load);
        }
        Err(e) => {
            println!("❌ Configuration validation failed: {}", e);
            println!("💡 Check your configuration file and try again.");
        }
    }
    
    Ok(())
}

fn generate_config_template(output_path: &PathBuf) -> Result<()> {
    let template = include_str!("../config/dsearch.toml.template");
    std::fs::write(output_path, template)?;
    
    println!("✅ Configuration template generated at: {}", output_path.display());
    
    Ok(())
}