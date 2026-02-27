use clap::Parser;
use html2md::parse_html;
use reqwest::blocking::Client;
use std::time::Duration;

#[derive(Parser)]
#[command(name = "web_fetch")]
#[command(about = "Fetch URL and convert to markdown")]
struct Args {
    url: String,
    #[arg(long, default_value = "100")]
    max_kb: usize,
    #[arg(short, long)]
    output: Option<String>,
}

fn main() {
    let args = Args::parse();

    let client = Client::builder()
        .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        .timeout(Duration::from_secs(30))
        .build()
        .expect("Failed to create HTTP client");

    match client.get(&args.url).send() {
        Ok(response) => {
            if !response.status().is_success() {
                eprintln!("Error: HTTP {}", response.status());
                std::process::exit(1);
            }

            match response.text() {
                Ok(html) => {
                    let max_bytes = args.max_kb * 1024;
                    let truncated = if html.len() > max_bytes {
                        match html.char_indices().nth(max_bytes) {
                            Some((idx, _)) => &html[..idx],
                            None => &html,
                        }
                    } else {
                        &html
                    };

                    let markdown = parse_html(truncated);

                    if let Some(output_path) = args.output {
                        std::fs::write(&output_path, &markdown).unwrap();
                        println!("Content written to {}", output_path);
                    } else {
                        println!("{}", markdown);
                    }
                }
                Err(e) => {
                    eprintln!("Error reading response: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Err(e) => {
            eprintln!("Error fetching URL: {}", e);
            std::process::exit(1);
        }
    }
}
