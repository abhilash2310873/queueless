# QueueLess

**Order Smart. Skip the Queue.**

QueueLess is a campus food-court ordering and queue system. Students browse stalls, place an order, receive a queue number, and collect food with a signed QR ticket. Stall staff run their own queue. A super admin manages the platform.

This repository is built in phases. Accounts, food courts, stalls, owner logins, categories, and menus are in place. Cart, queues, and payments come in later phases.

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
| `MAIL_SUPPRESS_SEND` | `True` in development. Verification mail is not sent. The code and link are printed in the Flask terminal. That is intentional, not a bug. |
| `PAYMENT_PROVIDER` | `mock` until a real gateway is configured. |

Do not put card numbers, UPI PINs, or real payment secrets in the project.

## Tests

With the virtual environment activated:

```bat
python -m pytest
```

The same command works on macOS and Linux.

## Accounts

Students register at http://127.0.0.1:5000/auth/register with an email on `STUDENT_EMAIL_DOMAIN`. `student@gmail.com` is rejected when the domain is `@college.edu`.

Set `ALLOW_STUDENT_EMAIL_SUBDOMAINS=False` to require an exact domain match. Set it to `True` to also allow subdomains, such as `x@cs.college.edu` when the domain is `@college.edu`.

With `MAIL_SUPPRESS_SEND=True`, open the terminal running Flask after registration. It prints a 6-digit code and a link. Five wrong codes lock verification for that account. The code and link are stored only as hashes.

After `flask --app run.py db upgrade`, create the local super admin:

```bat
flask --app run.py create-admin
```

Development only: `admin@example.local` / `Campus@123`. The command refuses to run when the app is in production. Do not use this password outside your own machine.

A student or stall owner who opens http://127.0.0.1:5000/admin/users receives 403. Hiding the link is not the protection; the view checks the role.

## Food courts and stalls

Sign in as the super admin and open Food courts. A new court and stall stay closed until you click Approve, which sets the status to OPEN. Reject sets CLOSED.

Create an owner from the Stalls page and pick the stall they run. That account can open My stall and edit only that stall. Opening another stall's address returns 403 because `stalls.owner_id` must match the logged-in user. Staff email is not limited to the college domain.

On Users, Suspend blocks the next login. Activate allows it again. An admin cannot suspend their own account.

## Menus

Admins create food categories at http://127.0.0.1:5000/admin/categories. Names such as Breakfast or Fast Food are rows in the database, not a hard-coded list.

A stall owner opens Menu, adds a food item (name, price, preparation time, stock, vegetarian flag, photo), and can mark it available or unavailable. Unavailable food shows CURRENTLY UNAVAILABLE. Stock of 0 shows SOLD OUT. Another owner who opens that food's URL receives 403. Student browsing of the catalog is a later phase; until then the owner menu and the admin All food page are the places to inspect items.

## What is not here yet

Cart, checkout, queues, payments, and QR pickup are later phases. Stock is reduced with one conditional `UPDATE` in `app/utils/stock.py` so two orders cannot take the last item. See `docs/concurrency.md`. Checkout will call that function in a later phase. See `docs/phase-reports/` after each phase.
