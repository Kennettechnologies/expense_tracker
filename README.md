# Expense Tracker (Minimal Flask Implementation)

This is a minimal, runnable Expense Tracker implementing core features from `guide.txt` using Django:

- User registration and login (session-based using Django auth)
- Profile with currency and timezone
- Add/Edit/Delete transactions (amount, category, date, time, description, payment method)
- Receipt upload (images)
- Categories and simple account balances
- CSV import/export for transactions
- Dashboard summary cards

This is a starting implementation — many advanced features from the guide can be added iteratively.

## Quick start (Windows PowerShell)

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r "requirements.txt"
```

3. Run the app:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

4. Open `http://127.0.0.1:8000` in your browser.

## Notes
- Email verification and password-reset are not configured (can be added using Django email backend).
- Database: SQLite file `db.sqlite3` in project root.
- Uploaded files are saved to `media/` (see `expense_tracker/settings.py`).

If you'd like, I can add social login (django-allauth), email sending, Docker support, or improve the UI with more analytics.