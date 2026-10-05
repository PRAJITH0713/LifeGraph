"""User model and password hashing helpers."""

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from flask_login import UserMixin


password_hasher = PasswordHasher()


class User(UserMixin):
    def __init__(self, user_id, full_name, email):
        self.id = user_id
        self.full_name = full_name
        self.email = email

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(row["id"], row["full_name"], row["email"])


def verify_password(password_hash, password):
    try:
        return password_hasher.verify(password_hash, password)
    except VerificationError:
        return False
