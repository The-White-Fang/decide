# SUBTASK-3.1: Admin Seeding & Bootstrap

## Parent Task
[TASK-03: Authentication & Security Guard](file:///home/abhishek/decide/tasks/03-authentication-and-security/index.md)

## Target Code Path
`decide/auth/bootstrap.py`

## Objective
Implement runtime bootstrap routines to seed the primary administrative account on container boot, generate secure credentials if unset, and handle password override flags.

## Functional Requirements
1. **Bootstrap Evaluation (PRD Section 6.1):**
   - Check if `users` table contains zero records via `UserRepository.count(db)`.
   - If zero users exist:
     - Check `settings.admin_password`.
     - If provided, hash with bcrypt and create user with `username = settings.admin_username`.
     - If unset, generate a 24-character random password using `generate_admin_password()`, hash it, create the user, and print a clear, formatted credential box to `sys.stdout`.
2. **Password Override Handling (`FORCE_ADMIN_RESET`):**
   - If users already exist and `settings.force_admin_reset` is `True`:
     - Locate the admin user by `settings.admin_username`.
     - If `settings.admin_password` is provided, update password hash.
     - If `settings.admin_password` is unset, generate new 24-char password, update password hash, and log new password to `sys.stdout`.
3. **Logging & Security Visibility:**
   - Format stdout banner clearly so container operators running `docker logs` can immediately view the generated credentials.

## Interface & Schema
```python
from sqlalchemy.orm import Session
from decide.config import Settings
from decide.crypto import hash_password, generate_admin_password
from decide.db.repository import UserRepository

def bootstrap_admin(db: Session, settings: Settings) -> None:
    """
    Evaluates database state and bootstraps or updates the administrator account.
    Logs auto-generated credentials to stdout if generated dynamically.
    """
    ...
```

## Acceptance Criteria
- [ ] Fresh container startup without `ADMIN_PASSWORD` prints generated 24-character password to stdout.
- [ ] Subsequent container restarts do not alter existing credentials unless `FORCE_ADMIN_RESET=true`.
- [ ] Setting `FORCE_ADMIN_RESET=true` successfully resets the password to the new value or auto-generated value.
- [ ] Passwords stored in database are never plaintext and verify with `bcrypt.checkpw`.
