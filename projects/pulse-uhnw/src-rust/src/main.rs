use axum::{extract::State, routing::get, Json, Router};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use sqlx::postgres::PgPoolOptions;
use sqlx::{Pool, Postgres};
use uuid::Uuid;

#[cfg(test)]
mod tests;

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct Asset {
    pub id: Uuid,
    pub asset_type: String,
    pub name: String,
    pub current_valuation: Decimal,
    pub currency: String,
}

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct ValuationHistory {
    pub id: Uuid,
    pub asset_id: Uuid,
    pub old_valuation: Option<Decimal>,
    pub new_valuation: Decimal,
    pub change_reason: Option<String>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Clone)]
struct AppState {
    db: Pool<Postgres>,
}

async fn get_total_net_worth(State(state): State<AppState>) -> Json<Decimal> {
    let result: (Option<Decimal>,) = sqlx::query_as("SELECT SUM(current_valuation) FROM assets")
        .fetch_one(&state.db)
        .await
        .unwrap_or((None,));
    Json(result.0.unwrap_or(Decimal::ZERO))
}

async fn stream_valuations(State(state): State<AppState>) -> Json<Vec<Asset>> {
    let assets = sqlx::query_as::<_, Asset>("SELECT id, asset_type, name, current_valuation, currency FROM assets")
        .fetch_all(&state.db)
        .await
        .unwrap_or_default();
    Json(assets)
}

async fn export_audit_log(State(state): State<AppState>) -> String {
    let history = sqlx::query_as::<_, ValuationHistory>("SELECT id, asset_id, old_valuation, new_valuation, change_reason, updated_at FROM valuation_history ORDER BY updated_at DESC")
        .fetch_all(&state.db)
        .await
        .unwrap_or_default();
    
    // Sukchan (Proto Arch): Generating a 'Proof of Valuation' CSV
    let mut csv = String::from("ID,Asset_ID,Old_Valuation,New_Valuation,Reason,Timestamp\n");
    for entry in history {
        csv.push_str(&format!(
            "{},{},{},{},{},{}\n",
            entry.id,
            entry.asset_id,
            entry.old_valuation.unwrap_or(Decimal::ZERO),
            entry.new_valuation,
            entry.change_reason.unwrap_or_default(),
            entry.updated_at
        ));
    }
    csv
}

pub fn calculate_net_worth(assets: Vec<Asset>) -> Decimal {
    assets.iter().map(|a| a.current_valuation).sum()
}

#[tokio::main]
async fn main() {
    println!("Pulse-Core: Connecting to Secure Vault...");

    let db_url = "postgres://pulse_admin:pulse_secure_password@localhost:5432/pulse_vault";
    let pool = PgPoolOptions::new()
        .max_connections(5)
        .connect(db_url)
        .await
        .expect("Linus (Sys Arch): Failed to connect to secure vault.");

    let state = AppState { db: pool };

    let app = Router::new()
        .route("/v1/handshake", get(|| async { Json("ENCLAVE_READY") }))
        .route("/v1/net-worth", get(get_total_net_worth))
        .route("/v1/valuations/stream", get(stream_valuations))
        .route("/v1/audit/export", get(export_audit_log))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:8080").await.unwrap();
    println!("Enclave API listening on {}", listener.local_addr().unwrap());
    axum::serve(listener, app).await.unwrap();
}
