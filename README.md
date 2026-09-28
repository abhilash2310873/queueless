# QueueLess

**Order Smart. Skip the Queue.**

QueueLess is a campus food-court ordering and queue system. Students browse stalls, place an order, receive a queue number, and collect food with a signed QR ticket. Stall staff run their own queue. A super admin manages the platform.

This repository is built in phases. The current phase is the application foundation: configuration, the Flask app factory, the database connection, and the base page layout. Ordering, accounts, and queues are added in later phases.

## Problem

Campus food courts build long physical queues, students cannot see what is still available, and stalls have no shared view of who is next.

## Stack

- Python 3.12+
- Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Flask-Mail
- SQLite for development (the models are written so MySQL or PostgreSQL can replace it later)
- Bootstrap 5 and a small custom stylesheet

## Setup

Requires Python 3.12 or newer. Packages are pinned in `requirements.txt` and install from pre-built wheels, so Windows does not need a C compiler.

### Windows

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
flask --app run.py db init
flask --app run.py db upgrade
flask --app run.py run --debug
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
flask --app run.py db init
flask --app run.py db upgrade
flask --app run.py run --debug
```

Open http://127.0.0.1:5000/

`flask db init` is only needed the first time, and only if the `migrations/` folder is not already in the project.

## Environment

Copy `.env.example` to `.env`. The `.env` file is gitignored.

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Signs sessions and, later, QR tokens. Use a long random string outside local development. |
| `DATABASE_URL` | Leave empty to use `instance/queueless.db`. |
| `STUDENT_EMAIL_DOMAIN` | College domain students must register with, for example `@college.edu`. |
| `ALLOW_STUDENT_EMAIL_SUBDOMAINS` | `False` means the email domain must match exactly. `True` also allows subdomains such as `cs.college.edu`. |
| `MAIL_SUPPRESS_SEND` | `True` in development. Mail is not sent to a real server. Later phases print the verification link in the terminal. That is intentional, not a bug. |
| `PAYMENT_PROVIDER` | `mock` until a real gateway is configured. |

Do not put card numbers, UPI PINs, or real payment secrets in the project.

## Tests

With the virtual environment activated:

```bat
python -m pytest
```

The same command works on macOS and Linux.

## What is not here yet

Accounts, food courts, menus, cart, checkout, queues, payments, and QR pickup are later phases. See `docs/phase-reports/` after each phase.
