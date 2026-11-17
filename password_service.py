"""Shared password handling, including existing accounts with legacy passwords."""
import hmac
import re

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

password_hash = PasswordHash.recommended()


def verify_password(password, stored):
    if not isinstance(stored, str):
        return False
    if stored.startswith(('$argon2', '$2')):
        try:
            return password_hash.verify(password, stored)
        except (ValueError, UnknownHashError):
            return False
    return hmac.compare_digest(password.encode('utf-8'), stored.encode('utf-8'))


def valid_new_password(password):
    return (8 <= len(password) <= 128
            and all(re.search(pattern, password) for pattern in
                    (r'[A-Z]', r'[a-z]', r'[0-9]', r'[^A-Za-z0-9]')))
