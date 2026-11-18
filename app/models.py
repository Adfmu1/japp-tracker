import uuid

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

db = SQLAlchemy()

password_hasher = PasswordHasher()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = password_hasher.hash(password)

    def check_password(self, password: str) -> bool:
        try:
            password_hasher.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False
        return True
