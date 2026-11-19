import uuid
from datetime import datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    job_applications: Mapped[list["JobApplication"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = password_hasher.hash(password)

    def check_password(self, password: str) -> bool:
        try:
            password_hasher.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False
        return True


class JobApplication(db.Model):
    __tablename__ = "job_applications"
    __table_args__ = (
        CheckConstraint(
            "salary_min >= 0",
            name="ck_job_applications_salary_min_nonnegative",
        ),
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_max >= salary_min",
            name="ck_job_applications_salary_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    company: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stage: Mapped[str] = mapped_column(String(120), nullable=False)

    user: Mapped["User"] = relationship(back_populates="job_applications")
