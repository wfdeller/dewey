"""Encryption utilities for sensitive data storage."""

import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings


def _get_fernet() -> Fernet:
    """Get Fernet instance using derived key from SECRET_KEY."""
    settings = get_settings()

    # Derive a proper 32-byte key from SECRET_KEY using PBKDF2
    # Using a fixed salt since we need deterministic encryption/decryption
    # The SECRET_KEY itself provides the entropy
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"dewey_tenant_keys_v1",  # Fixed salt for deterministic derivation
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.secret_key.encode()))
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """
    Encrypt a sensitive value for storage.

    Args:
        plaintext: The value to encrypt (e.g., API key)

    Returns:
        Base64-encoded encrypted value
    """
    if not plaintext:
        return ""

    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_value(encrypted: str) -> str:
    """
    Decrypt a stored encrypted value.

    Args:
        encrypted: Base64-encoded encrypted value

    Returns:
        Decrypted plaintext
    """
    if not encrypted:
        return ""

    fernet = _get_fernet()
    encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode())
    decrypted = fernet.decrypt(encrypted_bytes)
    return decrypted.decode()


def mask_api_key(key: str, visible_chars: int = 8) -> str:
    """
    Mask an API key for display, showing only first/last few characters.

    Args:
        key: The API key to mask
        visible_chars: Number of characters to show at start and end

    Returns:
        Masked key like "sk-abc1...xyz9"
    """
    if not key or len(key) <= visible_chars * 2:
        return "***"

    return f"{key[:visible_chars]}...{key[-visible_chars:]}"
