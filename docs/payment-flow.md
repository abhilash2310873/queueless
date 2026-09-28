# Payments

Online checkout creates a payment row with status PENDING and does not assign a queue number until the mock gateway reports success. Failure cancels the order and returns stock.

Cash checkout creates the order immediately with status CASH_PENDING, assigns a queue number, and shows PAYMENT PENDING until the stall clicks Mark cash paid (CASH_PAID).

The database stores the payment id, order id, amount, method, status, time, and a mock gateway reference. Card numbers, CVV, and UPI PINs are never accepted.

`PAYMENT_PROVIDER=mock` is the local default. `app/payments/routes.py` is the mock screen. A Razorpay class can replace it later without changing the order service.
