"""Container initialization and automated administrative account seeding."""

import sys
from typing import Optional
from sqlalchemy.orm import Session
from decide.config import Settings, get_settings
from decide.crypto import hash_password, generate_admin_password
from decide.db.models import User
from decide.db.repository import UserRepository


def bootstrap_admin(db: Session, settings: Optional[Settings] = None) -> Optional[str]:
    """
    Evaluates database state and seeds or updates the administrator account.
    Returns generated password if one was created dynamically, otherwise None.
    """
    cfg = settings or get_settings()
    user_count = UserRepository.count(db)

    generated_password: Optional[str] = None

    if user_count == 0:
        if cfg.admin_password:
            password_to_use = cfg.admin_password
        else:
            generated_password = generate_admin_password(24)
            password_to_use = generated_password

        hashed = hash_password(password_to_use)
        UserRepository.create(db, username=cfg.admin_username, password_hash=hashed)

        if generated_password:
            banner = f"""
================================================================================
                       DECIDE APPLIANCE BOOTSTRAP
================================================================================
 Administrator account created successfully:
 Username : {cfg.admin_username}
 Password : {generated_password}

 IMPORTANT: Save these credentials immediately. They will not be shown again.
================================================================================
"""
            sys.stdout.write(banner)
            sys.stdout.flush()

    elif cfg.force_admin_reset:
        existing_user = UserRepository.get_by_username(db, cfg.admin_username)
        if existing_user:
            if cfg.admin_password:
                new_pwd = cfg.admin_password
            else:
                generated_password = generate_admin_password(24)
                new_pwd = generated_password

            hashed = hash_password(new_pwd)
            UserRepository.update_password(db, existing_user, hashed)

            msg = f"\n[decide-bootstrap] FORCE_ADMIN_RESET active: Password for '{cfg.admin_username}' updated."
            if generated_password:
                msg += f" New password: {generated_password}\n"
            sys.stdout.write(msg + "\n")
            sys.stdout.flush()

    return generated_password
