"""Application settings loaded from the environment.

Copy .env.example to .env and edit it. Nothing in this file is a production secret.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

INSTANCE_DIR = BASE_DIR / "instance"


def _env_flag(name: str, default: str = "False") -> bool:
    """Read a yes/no environment variable. Accepts 1, true, and yes."""
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes"}


def _sqlite_uri(filename: str) -> str:
    # Absolute path so the database file does not depend on the folder you start Flask from.
    path = (INSTANCE_DIR / filename).resolve()
    return "sqlite:///" + path.as_posix()


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-change-me"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or _sqlite_uri("queueless.db")

    # College accounts must use this domain. Change it in .env, not in code.
    STUDENT_EMAIL_DOMAIN = os.environ.get("STUDENT_EMAIL_DOMAIN", "@college.edu")
    ALLOW_STUDENT_EMAIL_SUBDOMAINS = _env_flag("ALLOW_STUDENT_EMAIL_SUBDOMAINS", "False")

    # Dev default: do not send real mail. Verification links are printed later.
    MAIL_SUPPRESS_SEND = _env_flag("MAIL_SUPPRESS_SEND", "True")
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "8025"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_USE_TLS = _env_flag("MAIL_USE_TLS", "False")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@queueless.local")

    PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "mock")
    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

    WTF_CSRF_ENABLED = True
    VERIFICATION_CODE_MINUTES = 30
    VERIFICATION_MAX_ATTEMPTS = 5


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    # One shared in-memory database for the whole test, not a new one per connection.
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # StaticPool keeps every query on the same in-memory database during a test.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(BaseConfig):
    DEBUG = False


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
