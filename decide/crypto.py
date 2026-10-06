"""Cryptographic primitives for password hashing, token generation, and constant-time verification."""

import hashlib
import hmac
import secrets
import string
import bcrypt

# Characters used for raw API keys and generated credentials
ALPHANUMERIC_CHARS: str = string.ascii_letters + string.digits
API_KEY_PREFIX: str = "dec_"
API_KEY_RANDOM_LENGTH: int = 32
KEY_PREFIX_LENGTH: int = 10


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with standard salt rounds."""
    if not isinstance(password, str):
        raise TypeError("Password must be a string.")
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash."""
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def generate_admin_password(length: int = 24) -> str:
    """Generates a cryptographically secure random alphanumeric password."""
    if length < 8:
        raise ValueError("Password length must be at least 8 characters.")
    return "".join(secrets.choice(ALPHANUMERIC_CHARS) for _ in range(length))


def generate_session_secret() -> str:
    """Generates a cryptographically secure 32-byte (64-character hex) secret for session signing."""
    return secrets.token_hex(32)


def generate_api_key() -> str:
    """
    Generates a cryptographically secure API key formatted as:
    dec_<32_random_alphanumeric_characters>
    Total string length is 36 characters.
    """
    random_part = "".join(secrets.choice(ALPHANUMERIC_CHARS) for _ in range(API_KEY_RANDOM_LENGTH))
    return f"{API_KEY_PREFIX}{random_part}"


def extract_key_prefix(raw_key: str) -> str:
    """
    Extracts the first 10 characters of the raw API key for display/auditing (e.g. 'dec_a1b2c3').
    Raises ValueError if key is shorter than 10 characters.
    """
    if not isinstance(raw_key, str) or len(raw_key) < KEY_PREFIX_LENGTH:
        raise ValueError(f"API key must be at least {KEY_PREFIX_LENGTH} characters to extract prefix.")
    return raw_key[:KEY_PREFIX_LENGTH]


def hash_api_key(raw_key: str) -> str:
    """Computes a SHA-256 hex digest of the raw API key for secure indexed storage and lookup."""
    if not isinstance(raw_key, str) or not raw_key:
        raise ValueError("API key must be a non-empty string.")
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def constant_time_compare(val1: str, val2: str) -> bool:
    """Performs constant-time comparison of two strings to prevent timing attacks."""
    if not isinstance(val1, str) or not isinstance(val2, str):
        return False
    return hmac.compare_digest(val1, val2)
