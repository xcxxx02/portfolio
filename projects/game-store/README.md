# Game Store

A Flask and SQLite digital game store assignment with customer accounts, product browsing, bundles, carts, wishlists, checkout, game keys, reviews and an admin inventory dashboard.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FLASK_SECRET_KEY = "replace-with-a-random-secret"
python app.py
```

Open `http://127.0.0.1:5000`.

The Stripe flow is a local demonstration adapter; it does not process real payments. The SQLite database is created and seeded locally on first run.
