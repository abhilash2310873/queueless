# Testing

From the project folder, with the virtual environment active:

```bat
python -m pytest
```

The same command works on macOS and Linux.

The tests cover app startup, college-email registration, login, role checks, food courts and stalls, menu availability, the atomic stock update including two threads taking the last item, and a cash order that moves from checkout through QR collection. Payment success and failure are covered by the order service used in that flow.

The React app is built with `npm run build` inside `frontend/`. That checks that the interface compiles. The browser still needs Flask running on port 5000.
