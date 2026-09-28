# Stock and concurrent orders

QueueLess changes stock with one SQL statement. It does not read the number in Python, decide, and then write. That read-then-write pattern can sell the same last item twice when two requests overlap.

## The statement

```sql
UPDATE food_items
   SET stock_quantity = stock_quantity - :qty,
       is_available = CASE
           WHEN stock_quantity - :qty <= 0 THEN 0
           ELSE is_available
       END
 WHERE id = :id
   AND is_available = 1
   AND stock_quantity >= :qty
```

The database checks `stock_quantity >= :qty` while it applies the update. If two students both ask for the last unit:

1. The first update matches the row and sets stock to 0 and `is_available` to false.
2. The second update matches zero rows, because stock is no longer high enough.
3. The app sees a row count of 0 and rejects that order. The message uses the stock left after the failed attempt, for example "Only 1 item remaining."

This lives in `app/utils/stock.py` as `deduct_stock`. Checkout will call it when orders exist. Putting the check only in the cart page would not be enough, because two browsers can pass that page before either one writes.

## What this does not do

Adding stock back (`restore_stock`) is also one `UPDATE`, but it does not turn the item available again. The stall owner does that after they know the food is ready to sell. SQLite serialises writers with a lock. The same SQL still works on MySQL and PostgreSQL, where the conditional update is the real protection under many app servers.
