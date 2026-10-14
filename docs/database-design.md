# Database design

Users have orders, notifications, favorites, and reviews. A user with the owner role is linked from `stalls.owner_id`. That column is unique, so one login runs one stall.

A food court has many stalls. A stall has many food items and pickup slots. Each food item belongs to one category. Categories are shared rows, not a hard-coded list.

An order belongs to one user, one stall, one food court, and one pickup slot. It has many order items, one payment, one queue record, and at most one review. Order items copy the name and price at purchase time so a later price change does not rewrite history.

Payments store amount, method, and status only. Login attempts store a failure count and a lock time per email. Password reset stores a hash of the token on the user, not the token itself.

Stock changes are not a separate table. `food_items.stock_quantity` is updated with one conditional `UPDATE`, described in `docs/concurrency.md`.
