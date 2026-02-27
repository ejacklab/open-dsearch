use clap::Parser;
use std::fs;
use std::path::Path;

const TEMPLATE: &str = r#"# {title}

## Executive Summary

{summary}

## Technical Architecture

{architecture}

## Key Components

{components}

## Implementation Details

{implementation}

## Sources & Citations

{sources}
"#;

#[derive(Parser)]
#[command(name = "synthesize")]
#[command(about = "Synthesize research findings into a report")]
struct Args {
    #[arg(short, long)]
    input: String,
    #[arg(short, long)]
    output: String,
    #[arg(short, long, default_value = "Research Report")]
    title: String,
}

fn load_findings(input_dir: &str) -> Vec<String> {
    let mut findings = Vec::new();
    let path = Path::new(input_dir);

    if !path.exists() {
        eprintln!("Warning: Input directory {} does not exist", input_dir);
        return findings;
    }

    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().map_or(false, |ext| ext == "md") {
                if let Ok(content) = fs::read_to_string(&path) {
                    findings.push(content);
                }
            }
        }
    }

    findings
}

fn main() {
    let args = Args::parse();

    let findings = load_findings(&args.input);
    let _combined = findings.join("\n\n---\n\n");

    let report = TEMPLATE
        .replace("{title}", &args.title)
        .replace("{summary}", "TODO: Write executive summary")
        .replace("{architecture}", "TODO: Document architecture")
        .replace("{components}", "TODO: List key components")
        .replace("{implementation}", "TODO: Describe implementation")
        .replace("{sources}", "TODO: Add citations");

    fs::write(&args.output, &report).expect("Failed to write output");

    println!("Report written to {}", args.output);
    println!("Combined {} finding files", findings.len());
}
