# SUBTASK-2.2: ORM Models & Indexes

## Parent Task
[TASK-02: Database Layer & Persistence](file:///home/abhishek/decide/tasks/02-database-and-persistence/index.md)

## Target Code Path
`decide/db/models.py`

## Objective
Define SQLAlchemy 2.0 ORM model classes for `users` and `api_keys`, including exact column data types, relationships, foreign keys, and required database indexes matching PRD Section 5.

## Functional Requirements
1. **User Model (`users` table):**
   - `id`: `Integer`, Primary Key, autoincrement.
   - `username`: `String`, unique, nullable=False, indexed.
   - `password_hash`: `String`, nullable=False.
   - `is_active`: `Boolean`, nullable=False, default=True.
   - `created_at`: `DateTime`, default=`datetime.utcnow`, nullable=False.
   - `updated_at`: `DateTime`, default=`datetime.utcnow`, onupdate=`datetime.utcnow`, nullable=False.
   - Relationship: `api_keys` -> 1-to-many relationship with `cascade="all, delete-orphan"`.
2. **APIKey Model (`api_keys` table):**
   - `id`: `Integer`, Primary Key, autoincrement.
   - `user_id`: `Integer`, ForeignKey(`users.id`, ondelete=`CASCADE`), nullable=False.
   - `name`: `String`, nullable=False (friendly label e.g., "Customer Support Router").
   - `key_prefix`: `String(10)`, nullable=False (e.g. `dec_k9fJ2m`).
   - `hashed_key`: `String(64)`, unique, nullable=False (SHA-256 hex digest).
   - `is_active`: `Boolean`, nullable=False, default=True.
   - `last_used_at`: `DateTime`, nullable=True (updated on successful inference).
   - `created_at`: `DateTime`, default=`datetime.utcnow`, nullable=False.
   - Relationship: `user` -> `User` model.
3. **Indexes (PRD Section 5.2):**
   - `idx_api_keys_hashed_key`: B-Tree index on `api_keys.hashed_key` for sub-millisecond key lookups.
   - `idx_api_keys_is_active`: B-Tree index on `api_keys.is_active` for filtering active keys.

## Interface & Schema
```python
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from decide.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    key_prefix = Column(String(10), nullable=False)
    hashed_key = Column(String(64), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_hashed_key", "hashed_key"),
        Index("idx_api_keys_is_active", "is_active"),
    )
```

## Acceptance Criteria
- [ ] Schema generation matches PRD §5.1 and §5.2 SQL DDL.
- [ ] Deleting a user cascades and deletes all associated API keys.
- [ ] Indexes `idx_api_keys_hashed_key` and `idx_api_keys_is_active` are verified in SQLite table metadata.
