# SUBTASK-3.2: API Key Auth & In-Memory Cache

## Parent Task
[TASK-03: Authentication & Security Guard](file:///home/abhishek/decide/tasks/03-authentication-and-security/index.md)

## Target Code Path
`decide/auth/api_key.py`

## Objective
Implement high-performance FastAPI authentication dependency for incoming `POST /predict` calls, SHA-256 hash lookup, in-memory caching to achieve < 1ms latency overhead, and background telemetry updates.

## Functional Requirements
1. **Header Validation (PRD Section 7.2):**
   - Read header `X-API-Key`.
   - If missing: raise `HTTPException(status_code=401, detail="Missing X-API-Key header")`.
   - If format is invalid or does not start with `dec_`: raise `HTTPException(status_code=403, detail="Invalid API key format")`.
2. **Key Hashing & In-Memory Cache (< 1ms Target):**
   - Calculate SHA-256 hash of incoming raw key: `hash_api_key(raw_key)`.
   - Check local in-memory key cache (`dict` with timestamp TTL or LRU cache):
     - Cache hit & key is active: Proceed immediately.
     - Cache hit & key is inactive/revoked: raise `HTTPException(status_code=403, detail="API key is inactive or revoked")`.
     - Cache miss: Query database via `APIKeyRepository.get_by_hash(db, hashed_key)`.
   - If key does not exist or `is_active == False`: Cache result and raise `HTTPException(status_code=403, detail="Invalid or revoked API key")`.
   - If key is valid: Cache `(key_id, is_active)` and return key object.
3. **Cache Invalidation:**
   - Provide `invalidate_key_cache(key_id_or_hash: str)` so that when a key is revoked via the admin GUI, the cache is instantly cleared.
4. **Telemetry & Background Task:**
   - Enqueue a non-blocking background task (using FastAPI's `BackgroundTasks`) to update `last_used_at = datetime.utcnow()` in SQLite, ensuring the request critical path is not blocked by a database write.

## Interface & Schema
```python
from fastapi import Header, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from decide.db.models import APIKey
from decide.db.session import get_db

class APIKeyCache:
    def get(self, hashed_key: str) -> Optional[dict]: ...
    def set(self, hashed_key: str, data: dict) -> None: ...
    def invalidate(self, hashed_key: str) -> None: ...
    def clear(self) -> None: ...

async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
) -> APIKey:
    """
    Validates X-API-Key header against cache and database.
    Updates last_used_at in background.
    """
    ...
```

## Acceptance Criteria
- [ ] Returns 401 when `X-API-Key` is missing.
- [ ] Returns 403 when key is unrecognized or revoked (`is_active = 0`).
- [ ] Subsequent requests with the same key hit the in-memory cache with < 1ms total auth overhead.
- [ ] Revoking a key immediately denies subsequent requests.
- [ ] `last_used_at` timestamp is updated in the database asynchronously.
