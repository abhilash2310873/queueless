# Viva questions

1. Why Flask? The app is server-rendered HTML plus a few JSON status calls, which Flask handles without a separate frontend build.
2. Why SQLite? It is a file database so the project runs on Windows and macOS without installing a server. The models use normal types so MySQL or PostgreSQL can replace the URL.
3. Why SQLAlchemy? Tables, foreign keys, and the conditional stock UPDATE are written once and run on more than one database.
4. Why not store passwords directly? `generate_password_hash` stores a salted hash. Login uses `check_password_hash`.
5. How does college email validation work? `STUDENT_EMAIL_DOMAIN` must match the host. Subdomains count only when `ALLOW_STUDENT_EMAIL_SUBDOMAINS` is true.
6. How does authorization work? `roles_required` checks the signed-in role and returns 403. Hiding a link is not the check.
7. How does the cart work? One row per student. A second stall is rejected until the cart is cleared, so one order maps to one queue.
8. How is stock updated? `deduct_stock` runs `UPDATE ... WHERE stock_quantity >= qty` and checks the row count.
9. How do you prevent overselling? If the UPDATE changes zero rows, the order is rejected and earlier lines are restored.
10. What if two users want the last item? SQLite locks the write. The second UPDATE no longer matches. See `docs/concurrency.md`.
11. How is the queue calculated? Position is one plus the number of earlier active orders at that stall.
12. How is waiting time calculated? Sum of prep minutes ahead, divided by `active_counters`, rounded up.
13. Why use QR? The stall confirms the person holding the ticket without reading out an order id that is easy to guess.
14. How is the QR secured? `URLSafeTimedSerializer` signs the order id and a nonce. The image does not contain the name or payment. A bad signature is rejected. After collection the status is COLLECTED, so the same token cannot be used again.
15. How does cash payment work? The order is CASH_PENDING, the queue number exists, and the stall sets CASH_PAID before collection.
16. How does online payment work? The mock page sets SUCCESS or FAILED. The queue number is assigned only after SUCCESS. Failure restores stock.
17. Why a payment abstraction? The order code asks for a status. A Razorpay provider can replace the mock without storing card data.
18. How does the slot recommendation work? It scores open slots by how full they are plus the current queue. It explains the reason. It is not claimed as high-accuracy AI.
19. What is the demand label trained on? Seeded historical orders, grouped by hour. The screen shows LOW, MEDIUM, or HIGH.
20. How are SQL injection attacks prevented? Queries go through SQLAlchemy parameters, not string-built SQL.
21. What if food becomes unavailable after it is in the cart? Checkout checks stock and availability again and will not place the order.
22. How do notifications work? A row is inserted for the student when the order, payment, or status changes. The list is per user.
23. How are reviews restricted? Only a COLLECTED order, and only one review per order.
24. How does the owner dashboard differ from the admin dashboard? The owner sees one stall. The admin sees platform counts and the activity log. Owners get 403 on admin URLs.
25. What are the limitations? One stall per cart, mock payments, SQLite for class demos, and demand labels from synthetic history until real orders accumulate.
26. Why is the cart limited to one stall? Queue math is per kitchen. Mixing stalls would mix two queues in one ticket.
27. When is a slot full? `current_orders` is increased with `WHERE current_orders < max_orders`. A zero row count means the slot is full.
28. Who can cancel? Only the student who owns the order, and only while it is PENDING.
29. What statuses are allowed? PENDING to ACCEPTED, PREPARING, READY, COLLECTED. PENDING can also become REJECTED or CANCELLED. Other jumps are rejected.
30. When is the queue number assigned for online payment? After the mock payment returns SUCCESS, not when the payment page opens.
31. What does the QR contain? A signed token with the order id and a nonce. Not the student name, not the amount.
32. Why hash the email verification code? The database should not hold the raw code. Five wrong tries lock that account.
33. Why is `MAIL_SUPPRESS_SEND` true? Local development prints the code in the terminal instead of needing an email server.
34. How does an owner stay inside their stall? `stalls.owner_id` must equal the logged-in user. Another id returns 403 for the stall and for its food.
35. Can a student open `/admin/users` by typing it? No. The view returns 403.
36. What is stored for a payment? Id, order id, amount, method, status, time, gateway reference.
37. What happens at stock zero? `is_available` is set false in the same UPDATE, and the label becomes SOLD OUT.
38. What is `restore_stock`? It adds quantity back after a cancel or a failed payment. It does not mark the item available by itself.
39. How are favorites stored? One row per user, target type (`food` or `stall`), and target id.
40. How does reorder work? The old lines are added with the same cart checks, so a sold-out item is skipped with an error.
41. What does the delay message mean? Preparation has lasted more than 1.5 times the item prep times. It does not name a cause.
42. Why Chart.js? The dashboards need simple bar counts in the browser. The numbers come from SQL, not from the chart library.
43. Why pagination on browse? The menu query uses 12 items per page so a large catalog is not loaded at once.
44. What is the activity log? Login, logout, order creation, payment, and status changes. Only an admin page lists them.
45. How is the development admin created? `flask --app run.py create-admin`. It refuses to run when `CONFIG_NAME` is production.
46. What is the demo password? `Campus@123` for the documented local accounts. It is not a production secret.
47. Why Pillow with qrcode? Pillow draws the PNG without a system QR library.
48. What is a nonce on the QR? A random value stored on the order. The signature must contain the same nonce, so a token for another order does not scan.
49. How would you move to PostgreSQL? Change `DATABASE_URL`. The conditional UPDATE and foreign keys stay the same.
50. What is future work? A real payment gateway, WebSockets, a phone app, and training the demand label on real orders instead of the seed.

