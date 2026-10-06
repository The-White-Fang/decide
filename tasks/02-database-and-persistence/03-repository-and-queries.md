# SUBTASK-2.3: Repository & Query Methods

## Parent Task
[TASK-02: Database Layer & Persistence](file:///home/abhishek/decide/tasks/02-database-and-persistence/index.md)

## Target Code Path
`decide/db/repository.py`

## Objective
Implement reusable CRUD repository abstractions for data access operations on `users` and `api_keys`, ensuring transactional consistency and clean interface boundaries.

## Functional Requirements
1. **User Repository Operations:**
   - `get_user_by_username(db: Session, username: str) -> Optional[User]`
   - `get_user_by_id(db: Session, user_id: int) -> Optional[User]`
   - `count_users(db: Session) -> int` (used by bootstrapper to check if initial admin exists)
   - `create_user(db: Session, username: str, password_hash: str) -> User`
   - `update_user_password(db: Session, user_id: int, new_password_hash: str) -> User`
2. **API Key Repository Operations:**
   - `get_api_key_by_hash(db: Session, hashed_key: str) -> Optional[APIKey]` (indexed lookup)
   - `get_api_key_by_id(db: Session, key_id: int) -> Optional[APIKey]`
   - `list_api_keys(db: Session, user_id: Optional[int] = None) -> list[APIKey]` (ordered by `created_at DESC`)
   - `create_api_key(db: Session, user_id: int, name: str, key_prefix: str, hashed_key: str) -> APIKey`
   - `revoke_api_key(db: Session, key_id: int) -> Optional[APIKey]` (sets `is_active = False`)
   - `update_api_key_last_used(db: Session, key_id: int, timestamp: Optional[datetime] = None) -> None`

## Interface & Schema
```python
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from decide.db.models import User, APIKey

class UserRepository:
    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]: ...
    @staticmethod
    def count(db: Session) -> int: ...
    @staticmethod
    def create(db: Session, username: str, password_hash: str) -> User: ...
    @staticmethod
    def update_password(db: Session, user: User, password_hash: str) -> User: ...

class APIKeyRepository:
    @staticmethod
    def get_by_hash(db: Session, hashed_key: str) -> Optional[APIKey]: ...
    @staticmethod
    def get_by_id(db: Session, key_id: int) -> Optional[APIKey]: ...
    @staticmethod
    def list_all(db: Session) -> list[APIKey]: ...
    @staticmethod
    def create(db: Session, user_id: int, name: str, key_prefix: str, hashed_key: str) -> APIKey: ...
    @staticmethod
    def revoke(db: Session, key_id: int) -> Optional[APIKey]: ...
    @staticmethod
    def update_last_used(db: Session, key_id: int, when: Optional[datetime] = None) -> None: ...
```

## Acceptance Criteria
- [ ] Key lookups by hash execute using the `idx_api_keys_hashed_key` index.
- [ ] Revocation properly updates `is_active` to `False` without deleting row history.
- [ ] `update_last_used` executes cleanly in standalone background sessions.
- [ ] Duplicate username or hash insertions raise proper constraint error exceptions.
