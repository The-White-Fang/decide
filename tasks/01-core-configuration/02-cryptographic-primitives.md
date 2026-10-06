# SUBTASK-1.2: Cryptographic Primitives

## Parent Task
[TASK-01: Core Configuration & Cryptographic Utilities](file:///home/abhishek/decide/tasks/01-core-configuration/index.md)

## Target Code Path
`decide/crypto.py`

## Objective
Implement secure cryptographic utilities for password hashing, API key token generation, prefix extraction, SHA-256 digest computation, and constant-time verification.

## Functional Requirements
1. **Password Hashing & Verification (PRD Section 4):**
   - Use `bcrypt` for hashing admin passwords.
   - Functions: `hash_password(plain_password: str) -> str`, `verify_password(plain_password: str, hashed_password: str) -> bool`.
2. **API Key Generation & Formatting (PRD Section 6.2):**
   - Format: `dec_<32_random_alphanumeric_characters>` using `secrets.token_urlsafe(24)` or alphanumeric character selection ensuring 32 characters after prefix.
   - Example output: `dec_k9fJ2m0xL7qW1vN8abC3dEfGhIjKlMnOp`.
   - Function: `generate_api_key() -> str`.
3. **Key Prefix Extraction & SHA-256 Hashing:**
   - Extract first 10 characters of the raw key string as `key_prefix` (e.g. `dec_k9fJ2m`).
   - Compute hex digest of SHA-256 for database lookup: `hash_api_key(raw_key: str) -> str`.
   - Functions: `extract_key_prefix(raw_key: str) -> str`, `hash_api_key(raw_key: str) -> str`.
4. **Constant-Time Comparison (PRD Section 10):**
   - Provide `constant_time_compare(val1: str, val2: str) -> bool` using `hmac.compare_digest` to prevent timing attacks.
5. **Secure Random Generators:**
   - Auto-generated 24-character alphanumeric admin password generator using `secrets.choice`.
   - Auto-generated 32-byte secret key generator for cookie session signing using `secrets.token_hex(32)`.

## Interface & Schema
```python
def hash_password(password: str) -> str:
    ...

def verify_password(plain_password: str, hashed_password: str) -> bool:
    ...

def generate_admin_password(length: int = 24) -> str:
    ...

def generate_session_secret() -> str:
    ...

def generate_api_key() -> str:
    """Generates 'dec_' followed by 32 cryptographically secure alphanumeric characters."""
    ...

def extract_key_prefix(raw_key: str) -> str:
    """Extracts first 10 characters (e.g., 'dec_123456')."""
    ...

def hash_api_key(raw_key: str) -> str:
    """Computes SHA-256 hex digest of the raw key."""
    ...

def constant_time_compare(val1: str, val2: str) -> bool:
    ...
```

## Acceptance Criteria
- [ ] API keys generated strictly begin with `dec_` and have 36 total characters (`dec_` + 32 chars).
- [ ] Prefix is exactly 10 characters (`raw_key[:10]`).
- [ ] SHA-256 output is 64 hex characters.
- [ ] Plaintext API keys are never stored; only hash and prefix are retained.
- [ ] Bcrypt password hashing correctly validates matching and rejects non-matching credentials.
