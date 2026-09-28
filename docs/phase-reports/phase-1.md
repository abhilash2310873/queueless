# Phase 1 — Project setup

## What was implemented

Flask application factory, environment-based configuration, SQLAlchemy and Flask-Migrate wired to SQLite, Flask-Login / Flask-Mail / CSRF extensions, and the shared page layout (navigation, light and dark mode, flash area, 403 / 404 / 500 pages). No food, account, or order features yet.

## Files created and modified

- `config.py`, `run.py`, `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, `README.md`, `LICENSE`
- `app/__init__.py`, `app/extensions.py`, `app/models/__init__.py`, `app/main/`
- `app/templates/`, `app/static/css/style.css`, `app/static/js/main.js`
- `tests/conftest.py`, `tests/test_setup.py`
- `migrations/` (empty schema; no tables yet)

## Database changes

SQLite file: `instance/queueless.db` (gitignored). Alembic is initialized. There are no tables until later phases add models.

## How to run and test it

Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
flask --app run.py db upgrade
flask --app run.py run --debug
```

macOS / Linux: use `python3 -m venv .venv`, `source .venv/bin/activate`, and `cp .env.example .env`. The Flask commands are the same.

1. Open http://127.0.0.1:5000/ — you should see “Order Smart. Skip the Queue.” and three feature cards.
2. Click the moon icon — the page should switch to dark mode and stay dark after refresh.
3. Open http://127.0.0.1:5000/missing — you should see “Page not found”, not a Python traceback.
4. In another terminal, with the virtual environment active, run `python -m pytest` — you should see 6 passed.

## Expected result

The site starts, uses SQLite, and shows the QueueLess layout. Tests cover the home page, 404, 403, the database connection, college-domain config, and refusal to run production with the default secret.

## Known limitations

No registration, login, food courts, or orders. `load_user` returns no user until Phase 2. `MAIL_SUPPRESS_SEND` defaults to true; real email is not sent. Bootstrap and fonts load from a CDN, so the first view needs a network connection.
