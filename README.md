# Pocket

Mindful money for two — a private, mobile-first finance web app.

Track earnings, spending, and transfers across hierarchical "pockets" (wallets / accounts), share pockets with another user (view or manage), and see clean reports with adjustable periods.

Stack: **Django 5 · HTMX 2 · Alpine.js 3 · Tailwind CSS · ApexCharts · SQLite (dev) · Postgres (prod, future).**

## Dev setup (Windows / PowerShell)

```powershell
# 1. Create venv and install deps
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Build CSS (one-shot)
.\.venv\Scripts\pytailwindcss.exe -i static/css/input.css -o static/css/output.css --minify

# 3. Run migrations
python manage.py migrate

# 4. Create the first user (you will be prompted for a password)
python manage.py createuser admin --superuser --display-name "Admin"

# 5. Start the dev server
python manage.py runserver
```

Open <http://localhost:8000/> and sign in. You'll be asked to set a new password on first login.

## Watch CSS while developing

```powershell
.\.venv\Scripts\pytailwindcss.exe -i static/css/input.css -o static/css/output.css --watch
```

## Project layout

```
config/             Django project (settings split base/dev/prod, urls, wsgi)
apps/
  accounts/         Auth, UserProfile, login/logout/change-password, mgmt commands
  pockets/          Pocket tree + sharing (wired in Phase 3 / 6)
  transactions/     Income, Expense, Categories (Phase 4); Transfer (Phase 5)
  reports/          Period-filtered charts (Phase 8)
  core/             Dashboard + shared template tags + context processors
templates/          Project-level templates (base.html, partials/, page templates)
static/css/         Tailwind input + built output
static/js/          HTMX/Alpine glue
docs/colors.png     Brand palette source
```

## Useful commands

```powershell
python manage.py createuser <username> [--superuser] [--display-name "..."]
python manage.py setpassword <username>
python manage.py runserver
```
