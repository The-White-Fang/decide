# TASK-02: Database Layer & Persistence

## Overview
This task implements the persistence engine for `decide` using an embedded SQLite database configured with Write-Ahead Logging (WAL mode), SQLAlchemy 2.0 / SQLModel ORM entities, and database repository operations for managing administrators and client API keys.

## Module Architecture & Subtasks

| Subtask ID | Title | Target File | Description |
| :--- | :--- | :--- | :--- |
| **SUBTASK-2.1** | [SQLite Engine & WAL Configuration](file:///home/abhishek/decide/tasks/02-database-and-persistence/01-sqlite-engine-and-wal.md) | `decide/db/session.py` | Engine initialization with WAL mode pragmas, connection pooling, and FastAPI session dependencies. |
| **SUBTASK-2.2** | [ORM Models & Indexes](file:///home/abhishek/decide/tasks/02-database-and-persistence/02-orm-models-and-indexes.md) | `decide/db/models.py` | Table schemas for `users` and `api_keys` with foreign keys and indexes per PRD §5. |
| **SUBTASK-2.3** | [Repository & Query Methods](file:///home/abhishek/decide/tasks/02-database-and-persistence/03-repository-and-queries.md) | `decide/db/repository.py` | CRUD operations for user authentication, API key issuance, key revocation, and last_used updates. |

## Status
**Completed** (All 9 database unit tests passing)

## Acceptance Criteria
- [x] Connecting to the database confirms `journal_mode` is `"wal"`.
- [x] Foreign key constraints are enforced (`PRAGMA foreign_keys = ON`).
- [x] Database path `/data/decide.db` (or custom configured path) is automatically provisioned without failing if the folder doesn't exist.
- [x] Sessions properly close without connection leaks.
- [x] Schema generation matches PRD §5.1 and §5.2 SQL DDL.
- [x] Deleting a user cascades and deletes all associated API keys.
- [x] Indexes `idx_api_keys_hashed_key` and `idx_api_keys_is_active` are verified in SQLite table metadata.
- [x] Key lookups by hash execute using the `idx_api_keys_hashed_key` index.
- [x] Revocation properly updates `is_active` to `False` without deleting row history.
- [x] `update_last_used` executes cleanly in standalone background sessions.
- [x] Duplicate username or hash insertions raise proper constraint error exceptions.

## Key Dependencies
- `sqlalchemy>=2.0.0` or `sqlmodel`
- Python SQLite driver (`sqlite3`)


## Database Schema Reference (PRD Section 5)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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
