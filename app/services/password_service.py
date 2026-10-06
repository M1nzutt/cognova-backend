import secrets
from threading import BoundedSemaphore

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


class PasswordService:
    """Hash with Argon2id and verify without leaking account existence."""

    def __init__(self) -> None:
        self._slots = BoundedSemaphore(2)
        self._hasher = PasswordHasher()
        self._dummy_hash = self.hash(secrets.token_urlsafe(32))

    def hash(self, password: str) -> str:
        with self._slots:
            return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str | None) -> bool:
        try:
            with self._slots:
                valid = self._hasher.verify(password_hash or self._dummy_hash, password)
        except (VerificationError, InvalidHashError):
            return False
        return valid and password_hash is not None

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)
