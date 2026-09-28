# Phase 4 — Food categories, items, and availability

## What was implemented

Admins create database-backed food categories. Stall owners add, edit, and delete menu items on their own stall (name, price, prep time, stock, veg flag, photo) and mark each item available or unavailable. Another owner who opens that food URL gets 403. Admins can list every food item.

## Files created and modified

- `app/models/food.py`, `app/models/__init__.py`
- `app/admin/forms.py`, `app/admin/services.py`, `app/admin/routes.py`
- `app/owner/forms.py`, `app/owner/services.py`, `app/owner/routes.py`
- `app/templates/admin/categories.html`, `category_form.html`, `food.html`, `_nav.html`
- `app/templates/owner/menu.html`, `food_form.html`, `_nav.html`, `stall.html`
- `app/templates/base.html`, `app/static/css/style.css`, `README.md`
- `tests/test_food.py`
- `migrations/versions/801474d61459_add_food_categories_and_items.py`

## Database changes

Tables `food_categories` and `food_items`. Food names are unique per stall. `is_available` is a manual flag. `stock_quantity` is stored now; the atomic checkout deduction is Phase 5.

## How to run and test it

Windows: `.venv\Scripts\activate`. macOS/Linux: `source .venv/bin/activate`. Then:

```bat
flask --app run.py db upgrade
flask --app run.py create-admin
flask --app run.py run --debug
```

1. Log in as `admin@example.local` / `Campus@123`. Open http://127.0.0.1:5000/admin/categories and add “Fast Food”. You should see it in the table.
2. If you do not already have a stall and owner from Phase 3, create a court, approve it, add a stall, and create `owner@example.local` / `Campus@123` for that stall.
3. Log in as that owner. Open Menu, add Chicken Burger, ₹120, 8 minutes, stock 15, leave Vegetarian unchecked, keep Available checked. You should see AVAILABLE.
4. Click Mark unavailable. The badge should become CURRENTLY UNAVAILABLE. Edit the item, set stock to 0, save. The badge should become SOLD OUT.
5. While still the owner, open http://127.0.0.1:5000/admin/food. You should see “not allowed”. Log in as the admin and open that URL — you should see Chicken Burger.
6. Run `python -m pytest`. You should see 20 passed.

## Expected result

Categories are not hard-coded. Owners manage only their own menu. Unavailable and sold-out labels come from `is_available` and `stock_quantity`.

## Known limitations

Students cannot browse the catalog yet (Phase 6). Checkout does not deduct stock yet (Phase 5). Rating stays 0 until reviews exist.
