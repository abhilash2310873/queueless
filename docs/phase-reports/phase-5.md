# Phase 5 — Stock management

## What was implemented

`deduct_stock` subtracts stock with one conditional `UPDATE`. If the row count is zero, the order is rejected and the message says how many are left. Reaching zero sets `is_available` to false in that same statement. Saving a menu item with stock 0 also clears availability. `restore_stock` adds units back without marking the item available again.

## Files created and modified

- `app/utils/stock.py`
- `app/owner/services.py`, `app/models/food.py`
- `tests/test_stock.py`
- `docs/concurrency.md`, `README.md`

## Database changes

No new tables. `food_items.stock_quantity` and `food_items.is_available` are updated by the conditional statement. Run `flask --app run.py db upgrade` only if Phase 4 tables are missing.

## How to run and test it

Windows: `.venv\Scripts\activate`. macOS/Linux: `source .venv/bin/activate`. Then `flask --app run.py run --debug`.

1. Log in as a stall owner who already has a menu item. Open Menu and edit that item. Set stock to 0 and leave Available checked. Save.
2. The menu badge should say SOLD OUT. Open the item again: Available should be off, because stock 0 clears it.
3. Set stock to 5, check Available, and save. The badge should say AVAILABLE.
4. Click Mark unavailable. The badge should say CURRENTLY UNAVAILABLE while stock stays 5.
5. Run `python -m pytest`. You should see 25 passed. The new tests include two threads asking for the last unit: one succeeds, the other is rejected, and stock ends at 0.

## Expected result

Stock never goes negative. Two overlapping deductions cannot both take the last unit. The SQL is explained in `docs/concurrency.md`.

## Known limitations

The cart and checkout do not call `deduct_stock` yet. That connection is made when orders are created. Students still cannot browse the menu.
