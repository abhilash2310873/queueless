"""Accounts and college-email verification."""

from datetime import datetime, timedelta, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow() -> datetime:
    # Naive UTC. SQLite and MySQL both store this without a timezone column.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role:
    STUDENT = "student"
    OWNER = "owner"
    ADMIN = "admin"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.STUDENT, index=True)
    # Roll number. Empty for staff accounts created later by an admin.
    student_id = db.Column(db.String(40), unique=True, nullable=True)
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    # Set after 5 wrong verification codes. A new code cannot clear this.
    verification_locked = db.Column(db.Boolean, nullable=False, default=False)
    is_suspended = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def set_password(self, password: str) -> None:
        # Werkzeug stores a salted hash. The original password is never saved.
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self) -> bool:
        # Flask-Login will not keep a session for a suspended or unverified account.
        return bool(self.email_verified) and not bool(self.is_suspended)


class EmailVerification(db.Model):
    """One pending verification per user. The code and link are stored as hashes."""

    __tablename__ = "email_verifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User", backref=db.backref("verification", uselist=False))

    def expired(self, now: datetime | None = None) -> bool:
        return (now or utcnow()) >= self.expires_at

    @staticmethod
    def expiry(minutes: int) -> datetime:
        return utcnow() + timedelta(minutes=minutes)
