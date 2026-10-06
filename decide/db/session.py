"""SQLite database connection and session lifecycle management."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from decide.config import get_settings

Base = declarative_base()

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


def get_engine(database_path: Optional[Path | str] = None) -> Engine:
    """Creates or returns the SQLite database engine configured with WAL mode."""
    global _engine, _SessionFactory
    if _engine is not None and database_path is None:
        return _engine

    settings = get_settings()
    db_path = Path(database_path) if database_path else settings.database_path

    # Ensure parent directory exists for file-based SQLite databases
    if str(db_path) != ":memory:" and not str(db_path).startswith("sqlite:"):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{db_path.resolve()}"
    elif str(db_path) == ":memory:":
        db_url = "sqlite:///:memory:"
    else:
        db_url = str(db_path)

    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    _engine = engine
    _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    return engine


def get_session_factory() -> sessionmaker:
    """Returns the configured sessionmaker."""
    global _SessionFactory
    if _SessionFactory is None:
        get_engine()
    return _SessionFactory  # type: ignore


def init_db(engine: Optional[Engine] = None) -> None:
    """Initializes all database tables defined on declarative Base."""
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)


def get_db() -> Generator[Session, None, None]:
    """FastAPI request dependency yielding an isolated database session."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_session_context(engine: Optional[Engine] = None) -> Generator[Session, None, None]:
    """Context manager for standalone and background database operations."""
    if engine is not None:
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    else:
        session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
        if db.is_active:
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Alias for standalone/background tasks matching Subtask 2.1 interface
db_session_scope = get_session_context

