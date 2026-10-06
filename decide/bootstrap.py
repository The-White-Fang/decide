from pathlib import Path
from decide.auth.bootstrap import bootstrap_admin
from decide.config import get_settings
from decide.db.session import init_db, get_session_context, get_engine



def main():
    settings = get_settings()
    try:
        settings.ensure_db_dir()
    except PermissionError:
        # If /data is not writable (e.g. running on host outside Docker container), fallback to ./data
        if str(settings.database_path).startswith("/data"):
            fallback_dir = Path("./data")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            settings.database_path = fallback_dir / "decide.db"
        else:
            raise

    # Provision SQLite schema
    engine = get_engine(settings.database_path)
    init_db(engine)

    # Seed administrative user
    with get_session_context(engine) as session:
        bootstrap_admin(session, settings)



if __name__ == "__main__":
    main()

