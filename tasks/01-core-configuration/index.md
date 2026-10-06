# TASK-01: Core Configuration & Cryptographic Utilities

## Overview
This task encompasses setting up the runtime configuration management and cryptographic primitives for `decide`. It defines how environment variables are parsed, validated, and defaulted, and establishes constant-time cryptographic operations for passwords and API tokens.

## Module Architecture & Subtasks

| Subtask ID | Title | Target File | Description |
| :--- | :--- | :--- | :--- |
| **SUBTASK-1.1** | [Environment & Settings Management](file:///home/abhishek/decide/tasks/01-core-configuration/01-environment-and-settings.md) | `decide/config.py` | Pydantic Settings implementation for all PRD §8 variables, path resolutions, and request limit constants. |
| **SUBTASK-1.2** | [Cryptographic Primitives](file:///home/abhishek/decide/tasks/01-core-configuration/02-cryptographic-primitives.md) | `decide/crypto.py` | Bcrypt hashing, SHA-256 digest computation, constant-time comparisons, token generation (`dec_<32_chars>`). |

## Key Dependencies
- `pydantic-settings`
- `bcrypt`
- Python standard library (`secrets`, `hashlib`, `hmac`, `pathlib`)

## Status
**Completed** (All 32 unit tests passing)

## Acceptance Criteria
- [x] All environment variables defined in PRD Section 8 are supported with documented default values.
- [x] Random credentials (24-char admin password, 32-byte secret key, 32-char token) use cryptographically secure RNG (`secrets`).
- [x] Raw API keys strictly follow the `dec_<32_random_alphanumeric_characters>` pattern.
- [x] Constant-time comparison is enforced for hash verification.

