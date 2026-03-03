# Pulse — UHNW Wealth Management

**Vision:** "Quiet Luxury" for the 0.1%. Wealth-flow for the Billionaire's Son.
**Status:** Phase 2 (Data Integrity) | **Date:** 2026-03-03

---

## 🏛️ 10-Character Team Status

| Role | Persona | Current Task | Status |
| :--- | :--- | :--- | :--- |
| **Product** | Phoebe | Defining "Flow" Data Models | 🚧 |
| **Design** | Didi | Flow Visualizer (Sankey-lite) | ✅ |
| **Growth** | Gigi | Invite-Only Onboarding (NFC) | ✅ |
| **Lead Dev** | Dave | Enclave API & Data Resilience | ✅ |
| **Jr Dev** | Yaoyao | Reactive Pulse ViewModels | ✅ |
| **Sys Arch** | Linus | Rust Core & Postgres Integration | ✅ |
| **Proto Arch** | Sukchan | Precision Decimal Handshake | ✅ |
| **Sr QA** | Sandy | Offline State Verification | ⏳ |
| **Jr QA** | Muimui | Haptic Integrity Testing | ⏳ |
| **Sr DevOps** | Liang | Dockerized Vault Environment | ✅ |

---

## 🏗️ Tech Stack

- **Frontend:** SwiftUI (iOS Native) - Integrated with Enclave API.
- **Backend:** Rust (Axum) - Connected to PostgreSQL.
- **Database:** PostgreSQL (Isolated Schema) - Seeded with $2.4B portfolio.
- **Infrastructure:** Dockerized local vault for dev/test.

---

## 🚀 Accomplishments (Sprint 4)

- **End-to-End Data Flow:** Rust now queries Postgres and serves a real `/v1/net-worth` endpoint.
- **SwiftUI Integration:** The Pulse Card now polls the real API every 10s.
- **Resilience:** Added "Offline" indicators (Stale Data UI) for spotty jet connectivity.
- **Seed Data:** Initialized the "Billionaire Portfolio" with high-precision values.
