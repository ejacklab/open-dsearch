use anyhow::Result;
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
        #[arg(long)]
        force: bool,
    },
    /// Perform a multi-model search
    Search {
        #[arg(required = true)]
        query: String,
        #[arg(long, default_value = "all")]
        models: String,
        #[arg(long, default_value = "10")]
        max_results: usize,
        #[arg(long, default_value = "30")]
        timeout: u64,
        #[arg(long)]
        save: Option<String>,
    },
    /// Interactive research session
    Interactive {
        #[arg(long)]
        load: Option<String>,
        #[arg(long)]
        save: Option<String>,
    },
    /// Semantic search using vector database
    Semantic {
        #[arg(required = true)]
        query: String,
        #[arg(long, default_value = "10")]
        limit: usize,
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
        #[arg(required = true)]
        skill: String,
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
    List,
    Load { id: String },
    Delete { id: String, #[arg(long)] confirm: bool },
}

#[derive(Subcommand)]
enum ConfigActions {
    Show,
    Validate,
    Template { #[arg(short, long, default_value = "dsearch.toml")] output: PathBuf },
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

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

            let model_list: Vec<String> = if models == "all" {
                vec!["gemini".into(), "xai".into(), "minimax".into()]
            } else {
                models.split(',').map(|s| s.trim().to_string()).collect()
            };

            let params = SearchParams {
                query: query.clone(),
                models: model_list,
                max_results,
                timeout_secs: timeout,
            };

            let results = dsearch.search(&params.query.clone(), params).await?;
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
            let models = dsearch.models.list_available();
            println!("🤖 Available AI Models:");
            for m in models {
                println!("  ✓ {}", m);
            }
        }
        Commands::Session { action } => match action {
            SessionActions::List => {
                let dir = PathBuf::from("./sessions");
                if !dir.exists() {
                    println!("📁 No saved sessions found.");
                } else {
                    println!("📚 Saved Sessions:");
                    for entry in std::fs::read_dir(&dir)? {
                        let entry = entry?;
                        if let Some(name) = entry.file_name().to_str() {
                            if name.ends_with(".json") {
                                println!("  📄 {}", name.strip_suffix(".json").unwrap());
                            }
                        }
                    }
                }
            }
            SessionActions::Load { id } => {
                let config = load_config(&cli.config)?;
                let dsearch = DSearch::new(config)?;
                let results = dsearch.load_session(&id).await?;
                print_results(&results);
            }
            SessionActions::Delete { id, confirm } => {
                let path = PathBuf::from("./sessions").join(format!("{}.json", id));
                if !path.exists() {
                    println!("❌ Session '{}' not found.", id);
                } else if confirm {
                    std::fs::remove_file(&path)?;
                    println!("✅ Session '{}' deleted.", id);
                } else {
                    println!("⚠️  Use --confirm to delete session '{}'.", id);
                }
            }
        },
        Commands::Skill { skill, params: _params } => {
            println!("🛠️  Executing skill: {}", skill);
            println!("⏳ Skill execution is under development.");
        }
        Commands::Config { action } => match action {
            ConfigActions::Show => {
                if cli.config.exists() {
                    let content = std::fs::read_to_string(&cli.config)?;
                    println!("⚙️  Current Configuration:\n{}", content);
                } else {
                    println!("❌ Configuration file not found at: {}", cli.config.display());
                }
            }
            ConfigActions::Validate => {
                match load_config(&cli.config) {
                    Ok(_config) => println!("✅ Configuration is valid!"),
                    Err(e) => println!("❌ Validation failed: {}", e),
                }
            }
            ConfigActions::Template { output } => {
                let template = include_str!("../config/dsearch.toml.template");
                std::fs::write(&output, template)?;
                println!("✅ Template generated at: {}", output.display());
            }
        },
    }

    Ok(())
}

fn init_config(config_path: &PathBuf, force: bool) -> Result<()> {
    if config_path.exists() && !force {
        anyhow::bail!("Configuration file already exists. Use --force to overwrite.");
    }
    let template = include_str!("../config/dsearch.toml.template");
    std::fs::write(config_path, template)?;
    println!("✅ Configuration initialized at: {}", config_path.display());
    Ok(())
}

fn load_config(config_path: &PathBuf) -> Result<Config> {
    let content = std::fs::read_to_string(config_path)?;
    let config: Config = toml::from_str(&content)?;
    Ok(config)
}

fn print_results(results: &SearchResults) {
    println!("\n🔍 Search Results for: {}", results.query);
    println!("📊 Total: {} | Models: {}", results.total, results.models.join(", "));
    println!("{}", "─".repeat(60));
    for (i, item) in results.results.iter().enumerate() {
        println!("\n{}. [{}] {}", i + 1, item.source, item.title);
        if let Some(url) = &item.url {
            println!("   📍 {}", url);
        }
        println!("   📄 {}", item.content);
        println!("   ⭐ {:.2}", item.relevance);
    }
}

async fn interactive_search(dsearch: &DSearch, load: Option<String>, save: Option<String>) -> Result<()> {
    println!("🚀 Open DSearch Interactive Mode!");
    let mut results = if let Some(id) = &load {
        dsearch.load_session(id).await?
    } else {
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
        std::io::Write::flush(&mut std::io::stdout())?;
        let mut input = String::new();
        std::io::stdin().read_line(&mut input)?;
        match input.trim() {
            "quit" | "exit" => {
                if let Some(id) = &save {
                    dsearch.save_session(id, &results).await?;
                    println!("💾 Session saved as: {}", id);
                }
                println!("👋 Goodbye!");
                break;
            }
            "help" => {
                println!("📖 Commands: help, quit/exit, clear, <query>");
            }
            "clear" => {
                results = SearchResults {
                    query: String::new(),
                    results: Vec::new(),
                    total: 0,
                    models: Vec::new(),
                    timestamp: chrono::Utc::now(),
                };
                println!("🧹 Cleared.");
            }
            "" => continue,
            query => {
                let params = SearchParams {
                    query: query.into(),
                    models: vec!["gemini".into(), "xai".into(), "minimax".into()],
                    max_results: 10,
                    timeout_secs: 30,
                };
                results = dsearch.search(&params.query.clone(), params).await?;
                print_results(&results);
            }
        }
    }
    Ok(())
}
