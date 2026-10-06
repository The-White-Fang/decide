# SUBTASK-8.1: Unit Test Suite

## Parent Task
[TASK-08: Testing, Quality Assurance & Benchmarks](file:///home/abhishek/decide/tasks/08-testing-and-benchmarks/index.md)

## Target Code Path
`tests/unit/`

## Objective
Implement isolated unit tests validating settings parsing, cryptographic primitives, database schema constraints, and repository methods without relying on external servers or network access.

## Functional Requirements
1. **Configuration Tests (`test_config.py`):**
   - Test default settings values against PRD §8 table.
   - Test environment variable overrides (`ADMIN_USERNAME`, `PORT`, etc.).
   - Test invalid `DEVICE` validation (e.g., rejecting `"tpu"`).
2. **Cryptography Tests (`test_crypto.py`):**
   - Test `generate_api_key()`: Assert starts with `dec_` and length is 36.
   - Test `extract_key_prefix()`: Assert exactly 10 characters.
   - Test `hash_api_key()`: Assert SHA-256 hex string format and determinism.
   - Test `hash_password()` and `verify_password()` with bcrypt.
   - Test `constant_time_compare()`: Verify matching strings return True, mismatches return False.
3. **Database Repository Tests (`test_repository.py`):**
   - In-memory SQLite session (`sqlite:///:memory:`).
   - Test user creation, password updating, and `count_users()`.
   - Test API key creation, prefix extraction, and hash uniqueness constraints.
   - Test `revoke_api_key()` sets `is_active = False`.
   - Test `update_api_key_last_used()` updates timestamp.

## Interface & Schema
```python
import pytest
from decide.crypto import generate_api_key, extract_key_prefix, hash_api_key, verify_password, hash_password
from decide.db.repository import UserRepository, APIKeyRepository

def test_api_key_generation():
    key = generate_api_key()
    assert key.startswith("dec_")
    assert len(key) == 36
    prefix = extract_key_prefix(key)
    assert len(prefix) == 10
    assert prefix == key[:10]
```

## Acceptance Criteria
- [x] 100% unit test pass rate.
- [x] Fast execution (< 5 seconds total).
- [x] Zero external network calls.

