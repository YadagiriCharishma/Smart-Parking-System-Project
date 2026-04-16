# Smart Parking System (Prototype)

Python Flask + SQLite prototype with user roles, bookings, QR, email, scheduler.

## Quickstart

1. Python 3.11+
2. Create venv and install deps:
```
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```
3. Run dev server:
```
python run.py
```

Set environment variables for email if needed: `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`.
