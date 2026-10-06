"""API Key authentication dependency and in-memory cache layer."""

import threading
from typing import Dict, Optional, Any
from fastapi import Header, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from decide.crypto import hash_api_key
from decide.db.models import APIKey
from decide.db.repository import APIKeyRepository
from decide.db.session import get_db, get_session_context


class KeyCacheItem:
    def __init__(self, key_id: int, is_active: bool, name: str, hashed_key: str):
        self.key_id = key_id
        self.is_active = is_active
        self.name = name
        self.hashed_key = hashed_key


class APIKeyCache:
    """Thread-safe in-memory cache for API key validation (< 1 ms lookup)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cache: Dict[str, KeyCacheItem] = {}

    def get(self, hashed_key: str) -> Optional[KeyCacheItem]:
        with self._lock:
            return self._cache.get(hashed_key)

    def set(self, hashed_key: str, item: KeyCacheItem) -> None:
        with self._lock:
            self._cache[hashed_key] = item

    def invalidate(self, hashed_key: str) -> None:
        with self._lock:
            if hashed_key in self._cache:
                del self._cache[hashed_key]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


# Global singleton cache instance
key_cache = APIKeyCache()


def _async_update_last_used(key_id: int) -> None:
    """Background task to update key last_used_at in SQLite."""
    try:
        with get_session_context() as session:
            APIKeyRepository.update_last_used(session, key_id)
    except Exception:
        pass


def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> APIKey:
    """
    Validates X-API-Key header against the in-memory cache and SQLite.
    Achieves < 1ms auth lookup overhead via caching.
    Schedules background last_used_at update.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    if not isinstance(x_api_key, str) or not x_api_key.startswith("dec_") or len(x_api_key) < 10:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Key is invalid, expired, or revoked.",
        )

    hashed = hash_api_key(x_api_key)

    # 1. Fast in-memory cache lookup
    cached = key_cache.get(hashed)
    if cached is not None:
        if not cached.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Key is invalid, expired, or revoked.",
            )
        # Background telemetry update
        background_tasks.add_task(_async_update_last_used, cached.key_id)
        # Build mock APIKey representation for caller
        key_obj = APIKey(
            id=cached.key_id,
            name=cached.name,
            hashed_key=cached.hashed_key,
            is_active=cached.is_active,
        )
        return key_obj

    # 2. Database lookup
    key_record = APIKeyRepository.get_by_hash(db, hashed)
    if not key_record or not key_record.is_active:
        # Cache negative result (as inactive)
        key_cache.set(
            hashed,
            KeyCacheItem(
                key_id=key_record.id if key_record else 0,
                is_active=False,
                name="",
                hashed_key=hashed,
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Key is invalid, expired, or revoked.",
        )

    # 3. Cache active result
    key_cache.set(
        hashed,
        KeyCacheItem(
            key_id=key_record.id,
            is_active=True,
            name=key_record.name,
            hashed_key=key_record.hashed_key,
        ),
    )

    # 4. Schedule background telemetry update
    background_tasks.add_task(_async_update_last_used, key_record.id)
    return key_record
