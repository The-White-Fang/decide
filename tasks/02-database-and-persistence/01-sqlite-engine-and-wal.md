# SUBTASK-2.1: SQLite Engine & WAL Configuration

## Parent Task
[TASK-02: Database Layer & Persistence](file:///home/abhishek/decide/tasks/02-database-and-persistence/index.md)

## Target Code Path
`decide/db/session.py`

## Objective
Establish the SQLite database engine, configure Write-Ahead Logging (WAL mode), set appropriate concurrency timeouts (`busy_timeout`), and create session lifecycles for dependency injection into FastAPI routes and background tasks.

## Functional Requirements
1. **SQLite PRAGMA Tuning:**
   - Execute `PRAGMA journal_mode=WAL;` on every new connection via SQLAlchemy event listener (`connect`).
   - Execute `PRAGMA busy_timeout=5000;` to prevent lock contention issues.
   - Execute `PRAGMA foreign_keys=ON;` to enforce foreign key integrity.
2. **Directory & Database File Validation:**
   - Ensure the directory containing the SQLite database (e.g. `/data`) exists prior to creating the SQLite engine; create it if missing.
3. **Session Factory & Context Management:**
   - Create `sessionmaker` bound to the engine with `expire_on_commit=False`.
   - Provide a generator dependency `get_db()` yielding a session and closing it upon completion.
   - Provide a standalone context manager `db_session_scope()` for background tasks and bootstrap operations outside of HTTP request lifecycles.
4. **Table Auto-Creation:**
   - Provide `init_db()` to run `Base.metadata.create_all(bind=engine)` upon container startup.

## Interface & Schema
```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from collections.abc import Generator
from decide.config import get_settings

Base = declarative_base()

def get_engine():
    ...

def init_db() -> None:
    """Verifies path, binds engine, and creates tables if they do not exist."""
    ...

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for request-scoped database sessions."""
    ...

def get_session_context():
    """Context manager for standalone / background database operations."""
    ...
```

## Acceptance Criteria
- [ ] Connecting to the database confirms `journal_mode` is `"wal"`.
- [ ] Foreign key constraints are enforced (`PRAGMA foreign_keys = ON`).
- [ ] Database path `/data/decide.db` (or custom configured path) is automatically provisioned without failing if the folder doesn't exist.
- [ ] Sessions properly close without connection leaks.
