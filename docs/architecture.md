# Architecture

A student uses the React app (or the Flask HTML pages). Both call the same Python services. Those services use SQLAlchemy to read and write SQLite.

```
Browser (React on port 5173, or Flask templates on port 5000)
        |
        v
Flask routes and /api/v1
        |
        v
Services (auth, cart, orders, stock, queue, payments, predictions)
        |
        v
SQLAlchemy models
        |
        v
SQLite file instance/queueless.db
```

React does not talk to the database. Vite proxies `/api` to Flask so the login cookie stays on one origin. Business rules, such as the one-stall cart, the conditional stock update, and the signed QR token, live in Python so the HTML tests and the React app cannot drift apart.
