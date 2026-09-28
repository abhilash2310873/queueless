# Phases 6–26 — Ordering, queue, payments, and the rest of the demo

## What was implemented

Students can search and filter food, keep a one-stall cart, pick a pickup slot, and check out with cash or a mock online payment. Stock is deducted with the conditional update from Phase 5. Each order gets a queue number and a wait time from prep minutes divided by counters. The order page polls status. The QR is a signed token; a bad signature or a second scan is rejected. Owners accept, prepare, mark cash paid, and collect. Reviews, favorites, history, reorder, notifications, owner and admin dashboards, demand labels, delay text, and a login attempt limit are included.

## Files created and modified

- `app/models/order.py`, `payment.py`, `notification.py`, `food.py` (`active_counters`)
- `app/student/`, `app/orders/`, `app/payments/`, `app/queue/`, `app/notifications/`, `app/analytics/`
- `app/utils/stock.py` is called from checkout
- Templates under `student/`, `orders/`, `payments/`, `owner/orders.html`, `admin/dashboard.html`
- `scripts/seed_data.py`
- `docs/queue-algorithm.md`, `concurrency.md`, `payment-flow.md`, `ml-model.md`, `api-documentation.md`, `demo-script.md`, `viva-questions.md`
- `tests/test_flow.py`
- `migrations/versions/651b1161ab7c_add_orders_cart_slots_payments.py`

## Database changes

Carts, pickup slots, orders, order items, payments, queue records, reviews, favorites, notifications, complaints, activity logs, prediction records. Run `flask --app run.py db upgrade`.

## How to run and test it

Windows: `.venv\Scripts\activate`. macOS/Linux: `source .venv/bin/activate`.

```bat
python -m pip install -r requirements.txt
flask --app run.py db upgrade
flask --app run.py create-admin
python scripts/seed_data.py
flask --app run.py run --debug
```

1. Log in as `student@college.edu` / `Campus@123` after the seed. Open Browse and add Chicken Burger.
2. Open Checkout. Choose the 12:00–12:15 slot and Pay at cash counter. You should see a queue number, a wait, and PAYMENT PENDING.
3. Log in as `owner@example.local` / `Campus@123`. Open Orders. Mark cash paid, Accept, Preparing, Ready.
4. Paste the pickup token from the student order page. The order becomes COLLECTED. Paste it again and you should see “already collected”.
5. As the student, open the order and save a 1–5 review. Open `/admin/dashboard` and you should see “not allowed”.
6. `python -m pytest` should show 26 passed.

## Expected result

A student can order, watch the queue, and collect with a signed QR. An owner cannot collect another stall’s ticket. Admin charts are counts.

## Known limitations

Online payment is a mock page. Demand labels use seeded history, not a live campus model. The login limit counts failed attempts in this process only; it resets when Flask restarts.
