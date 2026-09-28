from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth.forms import LoginForm, RegisterForm, ResendForm, VerifyCodeForm
from app.auth.services import AuthError, register_student, resend_verification, verify_with_code, verify_with_token
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth.account"))
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            register_student(form.name.data, form.email.data, form.password.data, form.student_id.data)
        except AuthError as exc:
            flash(str(exc), "danger")
        else:
            flash(
                "Account created. Enter the verification code from your college email. "
                "In development that code is printed in the terminal running Flask.",
                "success",
            )
            return redirect(url_for("auth.verify_form"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.account"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        # Same message for a missing email and a wrong password.
        if user is None or not user.check_password(form.password.data):
            flash("Email or password is incorrect.", "danger")
        elif user.is_suspended:
            flash("This account is suspended.", "danger")
        elif not user.email_verified:
            flash("Verify your college email before signing in.", "warning")
        elif _login_blocked(form.email.data):
            flash("Too many login attempts. Wait a few minutes and try again.", "danger")
        else:
            login_user(user)
            _login_attempts.pop(form.email.data.strip().lower(), None)
            from app.models import ActivityLog
            from app.extensions import db

            db.session.add(ActivityLog(actor_id=user.id, action="login", detail=user.email))
            db.session.commit()
            flash("You are signed in.", "success")
            return redirect(_safe_next(request.args.get("next")))
        _note_failed_login(form.email.data)
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    from app.extensions import db
    from app.models import ActivityLog

    if current_user.is_authenticated:
        db.session.add(ActivityLog(actor_id=current_user.id, action="logout", detail=current_user.email))
        db.session.commit()
    logout_user()
    flash("You are signed out.", "success")
    return redirect(url_for("main.index"))


@auth_bp.route("/verify", methods=["GET", "POST"])
def verify_form():
    form = VerifyCodeForm()
    resend_form = ResendForm()
    if form.validate_on_submit():
        try:
            verify_with_code(form.email.data, form.code.data)
        except AuthError as exc:
            flash(str(exc), "danger")
        else:
            flash("Email verified. You can log in now.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/verify.html", form=form, resend_form=resend_form)


@auth_bp.route("/verify/<token>")
def verify_link(token: str):
    try:
        verify_with_token(token)
    except AuthError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("auth.verify_form"))
    flash("Email verified. You can log in now.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/resend", methods=["POST"])
def resend():
    form = ResendForm()
    if form.validate_on_submit():
        try:
            resend_verification(form.email.data)
        except AuthError as exc:
            flash(str(exc), "danger")
        else:
            flash("A new verification code was issued. In development it is printed in the terminal.", "success")
    else:
        flash("Enter the college email used at registration.", "danger")
    return redirect(url_for("auth.verify_form"))


@auth_bp.route("/account")
@login_required
def account():
    # The page reads current_user only, so one student cannot open another's account.
    return render_template("auth/account.html")


def _safe_next(target: str | None) -> str:
    # Only follow a relative path. This blocks redirects to another website.
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("auth.account")


_login_attempts: dict[str, int] = {}


def _note_failed_login(email: str) -> None:
    key = (email or "").strip().lower()
    _login_attempts[key] = _login_attempts.get(key, 0) + 1


def _login_blocked(email: str) -> bool:
    from flask import current_app

    key = (email or "").strip().lower()
    return _login_attempts.get(key, 0) >= current_app.config["LOGIN_MAX_ATTEMPTS"]
