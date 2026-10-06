"""Database repository access layer for User and APIKey entities."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from decide.db.models import User, APIKey


class UserRepository:
    """Repository operations for administrative users."""

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def count(db: Session) -> int:
        stmt = select(func.count(User.id))
        return db.execute(stmt).scalar_one() or 0

    @staticmethod
    def create(db: Session, username: str, password_hash: str) -> User:
        user = User(username=username, password_hash=password_hash, is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_password(db: Session, user: User | int, password_hash: str) -> User:
        if isinstance(user, int):
            user_obj = UserRepository.get_by_id(db, user)
            if not user_obj:
                raise ValueError(f"User with id {user} not found.")
        else:
            user_obj = user
        user_obj.password_hash = password_hash
        user_obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user_obj)
        return user_obj


class APIKeyRepository:
    """Repository operations for API keys and usage tracking."""

    @staticmethod
    def get_by_hash(db: Session, hashed_key: str) -> Optional[APIKey]:
        stmt = select(APIKey).where(APIKey.hashed_key == hashed_key)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_id(db: Session, key_id: int) -> Optional[APIKey]:
        stmt = select(APIKey).where(APIKey.id == key_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def list_all(db: Session, user_id: Optional[int] = None) -> List[APIKey]:
        stmt = select(APIKey)
        if user_id is not None:
            stmt = stmt.where(APIKey.user_id == user_id)
        stmt = stmt.order_by(APIKey.created_at.desc())
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def create(db: Session, user_id: int, name: str, key_prefix: str, hashed_key: str) -> APIKey:
        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            hashed_key=hashed_key,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return api_key

    @staticmethod
    def revoke(db: Session, key_id: int) -> Optional[APIKey]:
        stmt = select(APIKey).where(APIKey.id == key_id)
        api_key = db.execute(stmt).scalar_one_or_none()
        if api_key:
            api_key.is_active = False
            db.commit()
            db.refresh(api_key)
        return api_key

    @staticmethod
    def update_last_used(db: Session, key_id: int, when: Optional[datetime] = None) -> None:
        timestamp = when or datetime.utcnow()
        stmt = update(APIKey).where(APIKey.id == key_id).values(last_used_at=timestamp)
        db.execute(stmt)
        db.commit()
