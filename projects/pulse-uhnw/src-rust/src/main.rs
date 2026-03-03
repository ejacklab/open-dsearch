use axum::{extract::State, routing::get, Json, Router};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use sqlx::postgres::PgPoolOptions;
use sqlx::{Pool, Postgres};
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize, sqlx::FromRow)]
pub struct Asset {
    pub id: Uuid,
    pub asset_type: String,
    pub name: String,
    pub current_valuation: Decimal,
    pub currency: String,
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
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:8080").await.unwrap();
    println!("Enclave API listening on {}", listener.local_addr().unwrap());
    axum::serve(listener, app).await.unwrap();
}
