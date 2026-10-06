"""Unit tests for decide.db persistence subsystem (Task 02 / Module 02)."""

from datetime import datetime
from pathlib import Path
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from decide.db.models import User, APIKey
from decide.db.repository import UserRepository, APIKeyRepository
from decide.db.session import (
    get_engine,
    init_db,
    get_session_context,
    db_session_scope,
    get_db,
)


@pytest.fixture
def test_db_session(tmp_path: Path):
    """Creates a temporary isolated SQLite database file and yields a session."""
    db_file = tmp_path / "test_decide.db"
    engine = get_engine(db_file)
    init_db(engine)

    with get_session_context(engine) as session:
        yield session


def test_sqlite_wal_pragmas(test_db_session: Session):
    """Verify that SQLite connection applies WAL journal mode and busy_timeout."""
    # Check journal_mode
    journal_mode = test_db_session.execute(text("PRAGMA journal_mode;")).scalar()
    assert str(journal_mode).lower() == "wal"

    # Check busy_timeout
    busy_timeout = test_db_session.execute(text("PRAGMA busy_timeout;")).scalar()
    assert busy_timeout == 5000

    # Check foreign_keys
    foreign_keys = test_db_session.execute(text("PRAGMA foreign_keys;")).scalar()
    assert foreign_keys == 1


def test_schema_indexes_verified_in_sqlite(test_db_session: Session):
    """Verify that required indexes exist on api_keys table per PRD §5.2."""
    indexes = test_db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='api_keys';")
    ).scalars().all()

    assert "idx_api_keys_hashed_key" in indexes
    assert "idx_api_keys_is_active" in indexes


def test_user_repository_crud(test_db_session: Session):
    """Verify UserRepository creation, count, retrieval, and password update."""
    assert UserRepository.count(test_db_session) == 0

    # Create user
    user = UserRepository.create(test_db_session, "admin_user", "hashed_pwd_123")
    assert user.id is not None
    assert user.username == "admin_user"
    assert user.password_hash == "hashed_pwd_123"
    assert user.is_active is True
    assert UserRepository.count(test_db_session) == 1

    # Get by username and id
    fetched = UserRepository.get_by_username(test_db_session, "admin_user")
    assert fetched is not None
    assert fetched.id == user.id

    fetched_by_id = UserRepository.get_by_id(test_db_session, user.id)
    assert fetched_by_id is not None
    assert fetched_by_id.username == "admin_user"

    # Update password via User instance
    updated = UserRepository.update_password(test_db_session, user, "new_hashed_pwd")
    assert updated.password_hash == "new_hashed_pwd"

    # Update password via user ID
    updated_by_id = UserRepository.update_password(test_db_session, user.id, "even_newer_pwd")
    assert updated_by_id.password_hash == "even_newer_pwd"

    # Update password for non-existent ID raises ValueError
    with pytest.raises(ValueError):
        UserRepository.update_password(test_db_session, 99999, "pwd")


def test_user_unique_constraint(test_db_session: Session):
    """Verify unique constraint on User.username."""
    UserRepository.create(test_db_session, "unique_admin", "hash1")
    with pytest.raises(IntegrityError):
        UserRepository.create(test_db_session, "unique_admin", "hash2")
    test_db_session.rollback()


def test_api_key_repository_crud(test_db_session: Session):
    """Verify APIKeyRepository creation, lookup, listing, revocation, and last_used."""
    user = UserRepository.create(test_db_session, "key_owner", "hash")

    # Create API key
    key1 = APIKeyRepository.create(
        test_db_session,
        user_id=user.id,
        name="Support Router Key",
        key_prefix="dec_123456",
        hashed_key="sha256_mock_hash_1111111111111111111111111111111111111111111111111111",
    )
    assert key1.id is not None
    assert key1.is_active is True
    assert key1.last_used_at is None

    # Get by hash
    fetched_key = APIKeyRepository.get_by_hash(
        test_db_session,
        "sha256_mock_hash_1111111111111111111111111111111111111111111111111111",
    )
    assert fetched_key is not None
    assert fetched_key.name == "Support Router Key"

    # Create second user and keys
    other_user = UserRepository.create(test_db_session, "other_owner", "hash")
    APIKeyRepository.create(
        test_db_session,
        user_id=other_user.id,
        name="Billing Router Key",
        key_prefix="dec_999999",
        hashed_key="sha256_mock_hash_2222222222222222222222222222222222222222222222222222",
    )

    # List all
    all_keys = APIKeyRepository.list_all(test_db_session)
    assert len(all_keys) == 2

    # Filter by user_id
    user1_keys = APIKeyRepository.list_all(test_db_session, user_id=user.id)
    assert len(user1_keys) == 1
    assert user1_keys[0].name == "Support Router Key"

    # Revoke key
    revoked = APIKeyRepository.revoke(test_db_session, key1.id)
    assert revoked is not None
    assert revoked.is_active is False

    # Update last used
    test_time = datetime(2026, 10, 4, 12, 0, 0)
    APIKeyRepository.update_last_used(test_db_session, key1.id, test_time)
    test_db_session.refresh(key1)
    assert key1.last_used_at == test_time


def test_api_key_hash_unique_constraint(test_db_session: Session):
    """Verify unique constraint on APIKey.hashed_key."""
    user = UserRepository.create(test_db_session, "hash_owner", "hash")
    APIKeyRepository.create(test_db_session, user.id, "K1", "dec_1", "duplicate_hash")
    with pytest.raises(IntegrityError):
        APIKeyRepository.create(test_db_session, user.id, "K2", "dec_2", "duplicate_hash")
    test_db_session.rollback()


def test_cascade_delete_keys_with_user(test_db_session: Session):
    """Verify deleting a User cascades and deletes associated API keys."""
    user = UserRepository.create(test_db_session, "user_to_delete", "hash")
    key = APIKeyRepository.create(
        test_db_session,
        user_id=user.id,
        name="Key To Cascade",
        key_prefix="dec_cascad",
        hashed_key="hash_cascade_12345",
    )

    key_id = key.id
    test_db_session.delete(user)
    test_db_session.commit()

    assert UserRepository.get_by_id(test_db_session, user.id) is None
    assert APIKeyRepository.get_by_id(test_db_session, key_id) is None


def test_db_session_scope_alias(tmp_path: Path):
    """Verify db_session_scope context manager commits cleanly."""
    db_file = tmp_path / "scope_test.db"
    engine = get_engine(db_file)
    init_db(engine)

    with db_session_scope(engine) as session:
        UserRepository.create(session, "scoped_user", "hash")

    with db_session_scope(engine) as session:
        assert UserRepository.count(session) == 1


def test_get_db_dependency(tmp_path: Path):
    """Verify get_db generator yields and closes session without leak."""
    db_file = tmp_path / "get_db_test.db"
    get_engine(db_file)
    init_db()

    gen = get_db()
    session = next(gen)
    assert isinstance(session, Session)
    assert session.is_active

    with pytest.raises(StopIteration):
        next(gen)
