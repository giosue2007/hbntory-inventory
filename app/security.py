#!/usr/bin/env python3
"""
Password hashing with PBKDF2-SHA256 (Python standard library).
Only the hash is stored, never the plain-text password.
"""
import hashlib
import hmac
import secrets

ITERATIONS = 600_000


def hash_password(password):
    """
    Return 'pbkdf2_sha256$iterations$salt$hash' for the password.
    """
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 salt.encode(), ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password, stored):
    """
    Return True if the password matches the stored hash.
    """
    try:
        _, iterations, salt, expected = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 salt.encode(), int(iterations))
    return hmac.compare_digest(digest.hex(), expected)
