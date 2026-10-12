# Product Requirement Document (PRD)

## Project: `decide`

**Version:** 1.0 (Final)

**Status:** Approved

**Author:** AI Systems Engineering

**Target:** Production-grade, self-hosted inference microservice for Fastino’s `GLiNER2.5-Decide` with integrated SQLite key management and administrative Web GUI

---

## 1. Executive Summary & Problem Statement

Modern automated pipelines require accurate, zero-shot intent routing and classification without transmitting proprietary text to external SaaS APIs or incurring variable per-token fees. Managing static API keys via environment variables limits operability and auditing in multi-service environments.

`decide` is a self-contained, turnkey Docker appliance hosting `fastino/GLiNER2.5-Decide`. It bundles an embedded SQLite database, a built-in admin Web GUI, dynamic key lifecycle management, and a high-performance REST endpoint for single-pass multi-task classification.

---

## 2. Goals & Success Metrics

### 2.1 Core Goals

- **Self-Contained Deployment:** Single `docker run` deployment with baked model weights, pre-packaged frontend assets, and embedded database management.
- **Granular Key Management:** Dynamic issuance, labeling, usage tracking, and immediate revocation of client API keys.
- **Native GUI:** Admin web portal for key management, account settings, and live model testing.
- **Automated Bootstrap:** Zero-touch administrator account seeding via runtime environment variables.

### 2.2 Key Performance Indicators (KPIs)

| Metric                   | Target       | Measurement Method                                      |
| ------------------------ | ------------ | ------------------------------------------------------- |
| **P95 Latency (CPU)**    | < 150 ms     | Single-request benchmark on modern 4-core x86_64 CPU    |
| **P95 Latency (GPU)**    | < 35 ms      | Single-request benchmark on NVIDIA T4/L4 GPU            |
| **Auth Lookup Overhead** | < 1 ms       | Hashed key retrieval via SQLite index + in-memory cache |
| **Container Readiness**  | < 12 seconds | Container start to `/health` returning `200 OK`         |
| **Availability Target**  | 99.9%        | Production uptime in containerized deployment           |

---

## 3. System Architecture & Component Interaction

```
[ External Client / Microservice ]          [ System Administrator ]
                |                                      |
                | POST /predict                        | GET/POST /admin/*
                | (Header: X-API-Key)                  | (Session Cookie)
                v                                      v
+-------------------------------------------------------------------------+
| Docker Container: decide                                                |
|                                                                         |
|   +--------------------------+          +---------------------------+   |
|   |   Inference Controller   |          |    Admin Web GUI Engine   |   |
|   |   `POST /predict`        |          |    (Jinja2 + HTMX + CSS)  |   |
|   +------------+-------------+          +-------------+-------------+   |
|                |                                      |                 |
|                v                                      v                 |
|         [ Auth Interceptor ]                 [ Admin Auth Guard ]       |
|                |                                      |                 |
|                +------------------+-------------------+                 |
|                                   |                                     |
|                                   v                                     |
|                [ Key / User Repository (SQLAlchemy) ]                   |
|                                   |                                     |
|                                   v                                     |
|                         [ SQLite (WAL Mode) ]                           |
|                         Path: /data/decide.db                           |
|                                                                         |
|   +-----------------------------------------------------------------+   |
|   | Model Execution Engine                                          |   |
|   | - Framework: PyTorch 2.x + gliner2                              |   |
|   | - Checkpoint: fastino/GLiNER2.5-Decide (Pre-baked in image)     |   |
|   | - Context: Single-process in-memory model worker                |   |
|   +-----------------------------------------------------------------+   |
+-------------------------------------------------------------------------+
                                    |
                    Mounted Volume: [ /data ]

```

---

## 4. Technical Stack

- **Language & Runtime:** Python 3.11
- **Web Server & API Framework:** FastAPI + Uvicorn
- **Model Inference Engine:** PyTorch + `gliner2` (`AutoExtractor`)
- **Persistence:** SQLite with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`)
- **ORM:** SQLAlchemy 2.0 / SQLModel
- **Frontend:** Server-rendered Jinja2 templates accelerated with HTMX and Tailwind CSS (bundled locally; no runtime Node.js dependency)
- **Cryptographic Primitives:**
- Password Hashing: `bcrypt`
- API Key Storage: SHA-256 digest lookup
- Key Generation: Cryptographically secure pseudo-random token generation (`secrets.token_urlsafe`)

---

## 5. Database Schema & Data Integrity

The database file resides at `/data/decide.db`. Tables are automatically initialized at container startup.

### 5.1 `users` Table

Stores administrative credentials.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

```

### 5.2 `api_keys` Table

Stores issued application credentials and usage telemetry.

```sql
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    hashed_key TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    last_used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_api_keys_hashed_key ON api_keys(hashed_key);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);

```

---

## 6. Functional Specifications

### 6.1 Container Initialization & Admin Seeding

1. **Schema Check:** Upon boot, verify existence of `/data/decide.db`; apply schema definitions if absent.
2. **Admin Bootstrap:**

- Evaluate `ADMIN_USERNAME` (defaults to `admin`) and `ADMIN_PASSWORD`.
- If `users` table contains zero records:
- If `ADMIN_PASSWORD` is supplied, create admin account immediately.
- If `ADMIN_PASSWORD` is missing, generate a cryptographically secure 24-character password, insert the admin, and output credentials clearly to stdout.

- If an admin record exists and `FORCE_ADMIN_RESET=true`, update the existing admin password to `ADMIN_PASSWORD`.

3. **Engine Boot:** Load `fastino/GLiNER2.5-Decide` onto the selected compute target (`cuda` or `cpu`). Bind Uvicorn to port `8000`.

### 6.2 Key Generation Lifecycle

- **Raw Key Format:** `dec_<32_random_alphanumeric_characters>` (e.g., `dec_k9fJ2m0xL7qW1vN8...`).
- **Generation Contract:**

1. The user creates a key via the Web GUI by providing a label (e.g., "Customer Support Router").
2. The service creates the raw secret, generates a SHA-256 hash, and extracts the first 10 characters as the `key_prefix`.
3. The service writes `key_prefix` and `hashed_key` to SQLite.
4. The raw secret is returned to the user **once** via a modal with a clipboard copy utility. The plain secret is never persisted or retrievable again.

### 6.3 Admin Web Portal (`/admin`)

- **Authentication Route (`/admin/login`):** Standard form login yielding an HTTP-only, secure, `SameSite=Lax` session cookie.
- **Dashboard (`/admin`):**
- **API Key Table:** Displays Key Label, Prefix (`dec_a1b2...`), Creation Date, Last Used Timestamp, and Status badge (Active/Revoked).
- **Revoke Action:** Instant revocation button triggering an asynchronous HTMX call updating `is_active = 0`.
- **Generation Modal:** Form allowing instant issuance of new labeled keys.

- **Interactive Playground (`/admin/playground`):**
- Input field for sample text.
- JSON / Key-Value editor for task labels (e.g., `category: [billing, support, general]`).
- Live "Test Predict" button executing classification via internal bindings and displaying JSON response + model latency.

---

## 7. API Endpoint Specifications

### 7.1 Health & Readiness Probe

`GET /health`

- **Auth:** None (Public)
- **Response (200 OK):**

```json
{
	"status": "healthy",
	"model_loaded": true,
	"device": "cuda:0"
}
```

### 7.2 Text Classification / Intent Routing

`POST /predict`

- **Authentication:** Mandatory header `X-API-Key: <secret_key>`
- **Validation Behavior:**
- Hashes incoming header value with SHA-256.
- Queries SQLite for active key matching `hashed_key`.
- If valid: Dispatches background task to update `last_used_at` timestamp.
- If invalid: Returns `401 Unauthorized` or `403 Forbidden`.

- **Request Body (`application/json`):**

```json
{
	"text": "My order arrived broken and I want a replacement immediately.",
	"tasks": {
		"intent": ["refund", "replacement", "tracking", "general_inquiry"],
		"urgency": ["low", "normal", "critical"]
	}
}
```

- **Response Body (`200 OK`):**

```json
{
	"result": {
		"intent": "replacement",
		"urgency": "critical"
	},
	"confidence": {
		"intent": {
			"refund": 0.0002,
			"replacement": 0.9995,
			"tracking": 0.0002,
			"general_inquiry": 0.0001
		},
		"urgency": {
			"low": 0.0618,
			"normal": 0.0713,
			"critical": 0.8669
		}
	}
}
```

- **Error Status Codes:**
- `401 Unauthorized`: Missing `X-API-Key` header.
- `403 Forbidden`: Key is invalid, expired, or revoked.
- `422 Unprocessable Entity`: Request body violates schema (missing fields, invalid JSON).
- `500 Internal Server Error`: Unhandled model inference failure.

---

## 8. Configuration & Environment Variables

| Variable            | Type    | Required | Default           | Description                                                     |
| ------------------- | ------- | -------- | ----------------- | --------------------------------------------------------------- |
| `ADMIN_USERNAME`    | String  | No       | `admin`           | Username for the primary administrative account                 |
| `ADMIN_PASSWORD`    | String  | No       | _Auto-generated_  | Password for admin (printed to log on creation if unset)        |
| `FORCE_ADMIN_RESET` | Boolean | No       | `false`           | If `true`, overrides existing admin password on container start |
| `DATABASE_PATH`     | String  | No       | `/data/decide.db` | Absolute path to SQLite database inside container               |
| `SECRET_KEY`        | String  | No       | _Auto-generated_  | Secret key for signing admin session cookies                    |
| `DEVICE`            | String  | No       | `auto`            | Device mapping: `auto`, `cpu`, or `cuda`                        |
| `PORT`              | Integer | No       | `8000`            | Port on which the FastAPI application listens                   |
| `WORKERS`           | Integer | No       | `1`               | Uvicorn worker count (keep at 1 for PyTorch VRAM safety)        |

---

## 9. Containerization & Storage Layout

### 9.1 Container Volumes

- `/data`: Persistent host directory or named Docker volume hosting `decide.db` and SQLite journal/WAL files.

### 9.2 Build-Time Baking

- Model weights for `fastino/GLiNER2.5-Decide` are fetched during `docker build` and stored at `/root/.cache/huggingface/` inside the image layer.
- Containers must start and function with zero external internet connectivity.

---

## 10. Security & Threat Mitigation

- **Timing Attacks:** Validation checks against cached/stored hashes run in constant time.
- **Credential Leakage:** Plaintext keys are never stored, logged, or serialized after generation.
- **Denial of Service (Resource Exhaustion):**
- Maximum character limit enforced on input `text` (default: 8,000 characters per request).
- Maximum task schemas per request capped at 20 tasks, 50 labels each.

- **Web UI Protection:** CSRF tokens required on all mutating admin routes; session cookies configured with `HttpOnly`, `SameSite=Lax`, and `Secure` (when deployed over TLS).
