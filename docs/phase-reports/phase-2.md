# Phase 2 — Authentication

## What was implemented

Student registration with a configurable college-email rule, hashed passwords, email verification by code or link, login, logout, and role checks. Students and stall owners who open `/admin/users` get 403. A development-only `create-admin` command adds the super admin.

## Files created and modified

- `app/models/user.py`, `app/models/__init__.py`
- `app/auth/`, `app/admin/routes.py`, `app/utils/decorators.py`
- `app/templates/auth/`, `app/templates/admin/users.html`, `app/templates/base.html`
- `app/__init__.py`, `app/extensions.py`, `config.py`, `app/static/css/style.css`
- `tests/test_auth.py`, `README.md`
- `migrations/versions/310706276098_add_users_and_email_verification.py`

## Database changes

Tables `users` and `email_verifications`. Passwords and verification codes are hashed. The link token is stored as a SHA-256 hash. Run `flask --app run.py db upgrade` if the tables are not there yet.

## How to run and test it

Windows: `.venv\Scripts\activate` then the Flask commands below. macOS/Linux: `source .venv/bin/activate`. Same Flask commands.

```bat
flask --app run.py db upgrade
flask --app run.py create-admin
flask --app run.py run --debug
```

1. Open http://127.0.0.1:5000/auth/register — type `student@gmail.com`. You should see “Use your college email address.”
2. Register as `student@college.edu` with a roll number and a password of at least 8 characters. The terminal running Flask should print a 6-digit code and a link.
3. Open http://127.0.0.1:5000/auth/verify — enter that email and code. Then log in. You should see your name and email on the account page.
4. Log out. The account page should send you back to login.
5. Log in as `admin@example.local` / `Campus@123` and open http://127.0.0.1:5000/admin/users — you should see the student. Log in as the student and open that same URL — you should see “not allowed”.
6. Run `python -m pytest`. You should see 13 passed.

## Expected result

Only college emails register. Unverified students cannot log in. Five wrong codes lock verification. Admin pages are blocked for other roles.

## Known limitations

No password reset, no owner screens, and no suspend button yet. Food courts start in Phase 3. `Campus@123` is a local development password only.
