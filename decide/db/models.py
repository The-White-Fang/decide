"""SQLAlchemy declarative models for users and API keys."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from decide.db.session import Base


class User(Base):
    """Administrative user entity."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    api_keys = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class APIKey(Base):
    """API key credential and usage telemetry entity."""

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
