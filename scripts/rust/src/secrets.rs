use std::process::Command;
use std::collections::HashMap;
use std::sync::Mutex;
use lazy_static::lazy_static;

lazy_static! {
    static ref SECRET_CACHE: Mutex<HashMap<String, String>> = Mutex::new(HashMap::new());
}

const DEFAULT_GCP_PROJECT: &str = "764461751740";

pub fn get_secret(provider: &str) -> Result<String, String> {
    // 1. Check cache
    if let Ok(cache) = SECRET_CACHE.lock() {
        if let Some(secret) = cache.get(provider) {
            return Ok(secret.clone());
        }
    }

    let (gcsm_name, env_name, project_id) = match provider {
        "gemini" => ("GEMINI_API_KEY", "GEMINI_API_KEY", DEFAULT_GCP_PROJECT),
        "minimax" => ("MINIMAX_API_KEY", "MINIMAX_API_KEY", DEFAULT_GCP_PROJECT),
        "xai" => ("XAI_API_KEY", "XAI_API_KEY", DEFAULT_GCP_PROJECT),
        "kimi" => ("KIMI_API_KEY", "KIMI_API_KEY", DEFAULT_GCP_PROJECT),
        _ => return Err(format!("Unknown provider: {}", provider)),
    };

    // 2. Try GCP Secret Manager (GCSM) FIRST as per user instructions
    match Command::new("gcloud")
        .args(&[
            "secrets", "versions", "access", "latest",
            &format!("--secret={}", gcsm_name),
            &format!("--project={}", project_id),
        ])
        .output() {
            Ok(output) if output.status.success() => {
                let secret = String::from_utf8_lossy(&output.stdout).trim().to_string();
                if !secret.is_empty() {
                    if let Ok(mut cache) = SECRET_CACHE.lock() {
                        cache.insert(provider.to_string(), secret.clone());
                    }
                    return Ok(secret);
                }
            },
            _ => {} // Fallback to env var
        }

    // 3. Try Environment Variable
    if let Ok(secret) = std::env::var(env_name) {
        if let Ok(mut cache) = SECRET_CACHE.lock() {
            cache.insert(provider.to_string(), secret.clone());
        }
        return Ok(secret);
    }

    Err(format!("Secret not found for {} (checked GCSM and {})", provider, env_name))
}
