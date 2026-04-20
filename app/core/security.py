"""Minimal security utilities reserved for future auth work."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

SECRET_HASH_SCHEME = "pbkdf2_sha256"
SECRET_HASH_ITERATIONS = 600_000


def _urlsafe_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def hash_secret(secret: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        SECRET_HASH_ITERATIONS,
    )
    return (
        f"{SECRET_HASH_SCHEME}${SECRET_HASH_ITERATIONS}"
        f"${_urlsafe_b64encode(salt)}${_urlsafe_b64encode(digest)}"
    )


def verify_secret(secret: str, encoded_secret: str) -> bool:
    try:
        scheme, iteration_text, salt_text, digest_text = encoded_secret.split("$", 3)
        if scheme != SECRET_HASH_SCHEME:
            return False
        iterations = int(iteration_text)
        salt = _urlsafe_b64decode(salt_text)
        expected_digest = _urlsafe_b64decode(digest_text)
    except (ValueError, TypeError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)
