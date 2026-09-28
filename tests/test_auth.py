import pytest

from app.auth.services import college_email_allowed
from app.extensions import db
from app.models import Role, User

PASSWORD = "Campus@123"


@pytest.fixture
def codes(monkeypatch):
    """Capture the verification code instead of printing it."""
    sent = {}

    def fake_deliver(user, code, token):
        sent["email"] = user.email
        sent["code"] = code
        sent["token"] = token

    monkeypatch.setattr("app.auth.services.deliver_verification", fake_deliver)
    return sent


def _register(client, email="student@college.edu", student_id="CS001", password=PASSWORD):
    return client.post(
        "/auth/register",
        data={
            "name": "Asha",
            "email": email,
            "student_id": student_id,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def _login(client, email, password=PASSWORD):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def _make_user(email, role, student_id=None, verified=True, suspended=False):
    user = User(
        name="Test User",
        email=email,
        role=role,
        student_id=student_id,
        email_verified=verified,
        is_suspended=suspended,
    )
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def test_college_email_rules():
    assert college_email_allowed("student@college.edu", "@college.edu", False)
    assert not college_email_allowed("student@gmail.com", "@college.edu", False)
    assert not college_email_allowed("student@yahoo.com", "@college.edu", False)
    assert college_email_allowed("student@student.college.edu", "@student.college.edu", False)
    assert not college_email_allowed("x@cs.college.edu", "@college.edu", False)
    assert college_email_allowed("x@cs.college.edu", "@college.edu", True)
    assert not college_email_allowed("x@notcollege.edu", "@college.edu", True)


def test_register_rejects_public_email(client):
    response = _register(client, email="student@gmail.com")
    assert response.status_code == 200
    assert b"college email" in response.data.lower()
    assert User.query.filter_by(email="student@gmail.com").first() is None


def test_register_verify_login_and_logout(client, codes):
    response = _register(client)
    assert b"Account created" in response.data
    user = User.query.filter_by(email="student@college.edu").one()
    assert user.role == Role.STUDENT
    assert user.email_verified is False
    assert user.password_hash != PASSWORD
    assert PASSWORD not in user.password_hash
    assert user.check_password(PASSWORD)
    assert user.verification.code_hash != codes["code"]

    blocked = _login(client, "student@college.edu")
    assert b"Verify your college email" in blocked.data

    verified = client.post(
        "/auth/verify",
        data={"email": "student@college.edu", "code": codes["code"]},
        follow_redirects=True,
    )
    assert b"Email verified" in verified.data
    assert User.query.filter_by(email="student@college.edu").one().email_verified is True

    home = _login(client, "student@college.edu")
    assert b"Asha" in home.data
    assert b"student@college.edu" in home.data

    logged_out = client.post("/auth/logout", follow_redirects=True)
    assert b"signed out" in logged_out.data.lower()
    account = client.get("/auth/account")
    assert account.status_code == 302
    assert "/auth/login" in account.headers["Location"]


def test_verify_link(client, codes):
    _register(client, email="link@college.edu", student_id="CS002")
    response = client.get(f"/auth/verify/{codes['token']}", follow_redirects=True)
    assert b"Email verified" in response.data
    assert User.query.filter_by(email="link@college.edu").one().email_verified is True


def test_five_wrong_codes_lock_verification(client, codes):
    _register(client, email="lock@college.edu", student_id="CS003")
    wrong = "000000" if codes["code"] != "000000" else "111111"
    for _ in range(5):
        client.post("/auth/verify", data={"email": "lock@college.edu", "code": wrong})
    user = User.query.filter_by(email="lock@college.edu").one()
    assert user.verification_locked is True
    again = client.post(
        "/auth/verify",
        data={"email": "lock@college.edu", "code": codes["code"]},
        follow_redirects=True,
    )
    assert b"locked" in again.data.lower()
    assert user.email_verified is False


def test_student_and_owner_cannot_open_admin_users(client):
    _make_user("student@college.edu", Role.STUDENT, student_id="CS010")
    _make_user("owner@example.local", Role.OWNER)
    _make_user("admin@example.local", Role.ADMIN)

    guest = client.get("/admin/users")
    assert guest.status_code == 302
    assert "/auth/login" in guest.headers["Location"]

    _login(client, "student@college.edu")
    assert client.get("/admin/users").status_code == 403
    client.post("/auth/logout")

    _login(client, "owner@example.local")
    assert client.get("/admin/users").status_code == 403
    client.post("/auth/logout")

    _login(client, "admin@example.local")
    page = client.get("/admin/users")
    assert page.status_code == 200
    assert b"student@college.edu" in page.data
    assert b"owner@example.local" in page.data


def test_account_page_shows_only_the_logged_in_student(client):
    _make_user("one@college.edu", Role.STUDENT, student_id="CS021")
    _make_user("two@college.edu", Role.STUDENT, student_id="CS022")
    _login(client, "one@college.edu")
    page = client.get("/auth/account")
    assert page.status_code == 200
    assert b"one@college.edu" in page.data
    assert b"two@college.edu" not in page.data
