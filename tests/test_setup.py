import pytest
from flask import abort
from sqlalchemy import text

from app.extensions import db
from config import CONFIGS


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"QueueLess" in response.data
    assert b"Order Smart. Skip the Queue." in response.data


def test_unknown_api_is_404(client):
    response = client.get("/api/v1/this-page-does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not found"


def test_forbidden_page(app, client):
    @app.route("/_phase1_forbidden")
    def _phase1_forbidden():
        abort(403)

    response = client.get("/_phase1_forbidden")
    assert response.status_code == 403
    assert b"not allowed" in response.data.lower()


def test_database_connection(app):
    with app.app_context():
        value = db.session.execute(text("SELECT 1")).scalar()
    assert value == 1
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_student_email_domain_is_configurable():
    assert CONFIGS["development"].STUDENT_EMAIL_DOMAIN.startswith("@")
    assert CONFIGS["testing"].MAIL_SUPPRESS_SEND is True


def test_production_rejects_default_secret():
    from app import create_app

    original = CONFIGS["production"].SECRET_KEY
    CONFIGS["production"].SECRET_KEY = "dev-change-me"
    try:
        with pytest.raises(RuntimeError):
            create_app("production")
    finally:
        CONFIGS["production"].SECRET_KEY = original
