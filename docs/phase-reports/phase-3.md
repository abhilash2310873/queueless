# Phase 3 — Food courts, stalls, and owners

## What was implemented

Admin screens to create food courts and stalls, approve or reject them, create an owner account linked to one stall, and suspend or activate users. An owner can edit only the stall whose `owner_id` is their user id. Another stall id returns 403.

## Files created and modified

- `app/models/food.py`, `app/models/__init__.py`
- `app/admin/forms.py`, `app/admin/services.py`, `app/admin/routes.py`
- `app/owner/`, `app/utils/uploads.py`
- `app/templates/admin/`, `app/templates/owner/stall.html`, `app/templates/base.html`, `app/templates/auth/account.html`
- `app/__init__.py`, `app/static/css/style.css`, `tests/test_places.py`, `README.md`
- `migrations/versions/1de63d48a1e3_add_food_courts_and_stalls.py`

## Database changes

Tables `food_courts` and `stalls`. A stall name is unique inside one court. `stalls.owner_id` is unique, so one owner account runs one stall. New courts and stalls start as CLOSED.

## How to run and test it

Windows: `.venv\Scripts\activate`. macOS/Linux: `source .venv/bin/activate`. Then:

```bat
flask --app run.py db upgrade
flask --app run.py create-admin
flask --app run.py run --debug
```

1. Log in as `admin@example.local` / `Campus@123`. Open http://127.0.0.1:5000/admin/courts and create “Main Campus Food Court”, 08:00 to 20:00. The status should be CLOSED.
2. Click Approve. The status should become OPEN.
3. Open Stalls, create “Burger Hub” in that court, then Create owner: name Burger Admin, email `owner@example.local`, password `Campus@123`, stall Burger Hub.
4. Log out, log in as that owner, open My stall, change the contact, and save. You should see “Stall updated.”
5. While logged in as that owner, open http://127.0.0.1:5000/admin/courts. You should see “not allowed”.
6. Log in as the admin, open Users, click Suspend on the owner, log out, and try the owner login. You should see “suspended”. Activate the owner and the login should work again. `python -m pytest` should show 17 passed.

## Expected result

Admins manage courts, stalls, and owners. Owners cannot open another stall or any admin page. Suspend blocks the next login.

## Known limitations

No menus or stock yet. Deleting a court is not in this phase. Logos are optional png, jpg, or webp files.
