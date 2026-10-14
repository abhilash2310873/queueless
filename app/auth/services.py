"""Registration, college-email rules, and verification.

Routes stay thin. The checks a student must explain in a viva live here.
"""

import hashlib
import secrets

from flask import current_app, g, url_for
from flask_mail import Message
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, mail
from app.models import EmailVerification, Role, User
from app.models.user import utcnow
from datetime import timedelta


class AuthError(Exception):
    """A registration or verification problem we can show to the user."""


def college_email_allowed(email: str, domain: str, allow_subdomains: bool) -> bool:
    """Return True when email belongs to the configured college domain.

    domain is stored like ``@college.edu``. With allow_subdomains False, the
    host must match exactly. With True, ``cs.college.edu`` is also accepted.
    """
    email = (email or "").strip().lower()
    if email.count("@") != 1:
        return False
    local, host = email.split("@")
    if not local or not host or any(ch.isspace() for ch in email):
        return False
    required = (domain or "").strip().lower()
    if required.startswith("@"):
        required = required[1:]
    if not required or "." not in required:
        return False
    if allow_subdomains:
        return host == required or host.endswith("." + required)
    return host == required


def register_student(name: str, email: str, password: str, student_id: str) -> User:
    """Create an unverified student and send a verification code."""
    email = email.strip().lower()
    student_id = student_id.strip()
    # Any real email address can register. The message still has to be verified.
    if email.count("@") != 1 or "." not in email.split("@", 1)[1]:
        raise AuthError("Enter a valid email address.")
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    if User.query.filter_by(email=email).first():
        raise AuthError("An account with that email already exists.")
    if User.query.filter_by(student_id=student_id).first():
        raise AuthError("That roll number is already registered.")

    user = User(name=name.strip(), email=email, role=Role.STUDENT, student_id=student_id)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.flush()
        _issue_verification(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise AuthError("An account with that email already exists.") from None
    return user


def resend_verification(email: str) -> None:
    user = User.query.filter_by(email=email.strip().lower(), role=Role.STUDENT).first()
    if user is None:
        raise AuthError("No student account is waiting for that email.")
    if user.email_verified:
        raise AuthError("That email is already verified. You can log in.")
    if user.verification_locked:
        raise AuthError("Verification is locked after too many wrong codes.")
    _issue_verification(user)
    db.session.commit()


def verify_with_code(email: str, code: str) -> User:
    user = User.query.filter_by(email=email.strip().lower()).first()
    if user is None or user.email_verified:
        raise AuthError("That code does not match a pending verification.")
    record = user.verification
    if user.verification_locked or record is None:
        raise AuthError("Verification is locked after too many wrong codes.")
    if record.expired():
        raise AuthError("That code has expired. Request a new one.")
    if not check_password_hash(record.code_hash, code.strip()):
        record.attempts += 1
        # The raw code is never stored. After 5 misses the account stays locked.
        if record.attempts >= current_app.config["VERIFICATION_MAX_ATTEMPTS"]:
            user.verification_locked = True
            db.session.commit()
            raise AuthError("Verification is locked after too many wrong codes.")
        db.session.commit()
        raise AuthError("That code is incorrect.")
    _mark_verified(user)
    return user


def verify_with_token(token: str) -> User:
    token_hash = _hash_token(token)
    record = EmailVerification.query.filter_by(token_hash=token_hash).first()
    if record is None:
        raise AuthError("This verification link is not valid.")
    user = record.user
    if user.verification_locked:
        raise AuthError("Verification is locked after too many wrong codes.")
    if record.expired():
        raise AuthError("This verification link has expired. Request a new one.")
    _mark_verified(user)
    return user


def deliver_verification(user: User, code: str, token: str) -> None:
    """Email the code. In development the message is printed instead of sent."""
    link = url_for("auth.verify_link", token=token, _external=True)
    body = (
        f"Hello {user.name},\n\n"
        f"Your QueueLess verification code is {code}.\n"
        f"Or open this link:\n{link}\n\n"
        "The code expires in "
        f"{current_app.config['VERIFICATION_CODE_MINUTES']} minutes."
    )
    if current_app.config.get("MAIL_SUPPRESS_SEND", True):
        # No mail server. The API shows this code on screen so a deployed demo still works.
        g.dev_verification_code = code
        print("\n----- QueueLess verification (mail suppressed) -----")
        print(f"To: {user.email}")
        print(f"Code: {code}")
        print(f"Link: {link}")
        print("----------------------------------------------------\n")
        return
    message = Message("Verify your QueueLess account", recipients=[user.email], body=body)
    mail.send(message)


def _issue_verification(user: User) -> None:
    if user.verification_locked:
        raise AuthError("Verification is locked after too many wrong codes.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    token = secrets.token_urlsafe(32)
    record = user.verification
    if record is None:
        record = EmailVerification(user_id=user.id)
        db.session.add(record)
    record.code_hash = generate_password_hash(code)
    record.token_hash = _hash_token(token)
    record.attempts = 0
    record.expires_at = EmailVerification.expiry(current_app.config["VERIFICATION_CODE_MINUTES"])
    db.session.flush()
    deliver_verification(user, code, token)


def _mark_verified(user: User) -> None:
    user.email_verified = True
    if user.verification is not None:
        db.session.delete(user.verification)
    db.session.commit()


def _hash_token(token: str) -> str:
    # The link token is long and random, so a SHA-256 hash is enough to store it.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def login_is_locked(email: str) -> bool:
    from app.models import LoginAttempt

    row = LoginAttempt.query.filter_by(email=(email or "").strip().lower()).first()
    return bool(row and row.locked_until and row.locked_until > utcnow())


def record_login_failure(email: str) -> None:
    from app.models import LoginAttempt
    from app.models.user import utcnow as now

    email = (email or "").strip().lower()
    row = LoginAttempt.query.filter_by(email=email).first()
    if row is None:
        row = LoginAttempt(email=email, failures=0)
        db.session.add(row)
    row.failures += 1
    if row.failures >= current_app.config["LOGIN_MAX_ATTEMPTS"]:
        row.locked_until = now() + timedelta(minutes=10)
    db.session.commit()


def clear_login_failures(email: str) -> None:
    from app.models import LoginAttempt

    row = LoginAttempt.query.filter_by(email=(email or "").strip().lower()).first()
    if row:
        db.session.delete(row)
        db.session.commit()


def request_password_reset(email: str) -> None:
    user = User.query.filter_by(email=(email or "").strip().lower()).first()
    if user is None:
        return
    token = secrets.token_urlsafe(32)
    user.reset_token_hash = _hash_token(token)
    user.reset_expires = utcnow() + timedelta(minutes=30)
    db.session.commit()
    if current_app.config.get("MAIL_SUPPRESS_SEND", True):
        g.dev_reset_token = token
        print("\n----- QueueLess password reset (mail suppressed) -----")
        print(f"To: {user.email}")
        print(f"Token: {token}")
        print("-------------------------------------------------------\n")
        return
    message = Message("Reset your QueueLess password", recipients=[user.email], body=f"Your reset token is {token}.")
    mail.send(message)


def reset_password(token: str, password: str) -> None:
    if len(password or "") < 8:
        raise AuthError("Password must be at least 8 characters.")
    user = User.query.filter_by(reset_token_hash=_hash_token(token or "")).first()
    if user is None or user.reset_expires is None or user.reset_expires < utcnow():
        raise AuthError("This reset token is not valid.")
    user.set_password(password)
    user.reset_token_hash = None
    user.reset_expires = None
    db.session.commit()
