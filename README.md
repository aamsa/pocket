# Pocket

> Mindful money for two — a private, mobile-first finance web app.

A self-hosted finance tracker for a household of two: track earnings and spending across multiple "wallets," share specific wallets between accounts (view-only or manage), and answer questions like *"how much did we spend on groceries this month?"* or *"what's in BCA right now?"* with clean period-filtered reports.

Built with Django 5 + HTMX + Alpine.js + Tailwind v4 + ApexCharts. Single-developer scale, IDR-only, designed first for the phone.

---

## Features (MVP)

- **Invite-only auth.** No public registration. The superuser bootstraps accounts via a CLI command. New users are forced to change their temporary password on first login.
- **Hierarchical pockets.** Each user gets a "Main" pocket on signup. Sub-pockets nest underneath (e.g. `Main → BCA → Emergency Fund`). Balances roll up to the parent ("downstream total").
- **Income, expense, and transfer.** All three are first-class. Categories ship with sensible defaults (Salary, Food, Transport, …) and users can add their own.
- **Pocket sharing.** Invite another user to a pocket with `view` or `manage` permission. Sharing a parent implicitly shares descendants. Recipients accept or decline from an inbox.
- **Period-filtered reports.** Week / This month / Last 3 months / This year / Custom range. Filter by pocket (with optional include-subtree). Four panels: income vs expense, spending by category donut, pocket balances area chart, top transactions.
- **Scheduled income / expense.** Pick a frequency (daily / weekly / monthly / yearly), an "every N" interval, a start date, and either an end date or an occurrence count. Editing the rule re-plans the future; past actuals are never disturbed. Past entries can be paused without deleting.
- **Projection dashboard.** Forward-looking view at `/projections/`: balance trajectory per pocket, projected monthly income vs expense, and the active schedules driving the forecast. Horizon picker (3 / 6 / 12 months).
- **Mobile-first UI.** Bottom tab bar + center FAB on mobile, sidebar on desktop. IDR formatting (`Rp 1.250.000`) everywhere. Warm cream/brown brand palette taken from `docs/colors.png`.
- **Per-balance hide/reveal, hidden by default.** Every *balance* figure (the Dashboard's Total Balance card, every pocket row balance on the Pockets list, both balance cards on Pocket detail) renders as `Rp ••••` until you tap its eye icon to reveal. Choice persists in `localStorage` per device, per balance — navigating between pages or reloading keeps revealed balances revealed. Income and expense aggregates, transaction rows, and report charts are intentionally untouched.

## Stack

| Layer | Choice |
|---|---|
| Web framework | Django 5 |
| Templates | Server-rendered Django + HTMX 2 partials |
| Client interactivity | Alpine.js 3 (CDN) |
| Styling | Tailwind CSS v4 (CSS-based config, standalone CLI — no Node) |
| Charts | ApexCharts via CDN |
| Icons | Lucide via CDN |
| Database | SQLite (dev) · Postgres (prod, deferred) |
| Auth | Django stock `auth_user` + a tiny `UserProfile` |
| Python | 3.14 |

## Project layout

```
pocket/
├── config/                          Django project package
│   └── settings/{base,dev,prod}.py  split settings; manage.py defaults to dev
├── apps/
│   ├── accounts/                    auth, UserProfile, mgmt commands, middleware
│   ├── pockets/                     Pocket tree, PocketShare, permissions, balance services
│   ├── transactions/                Category, Transaction, Transfer, RecurringRule + materialiser
│   ├── reports/                     period filter + ApexCharts data builders (the past)
│   ├── projections/                 forward-looking dashboard (the future)
│   └── core/                        dashboard, money template tags, context processors
├── templates/                       project-level templates (base + partials + pages)
├── static/
│   ├── css/input.css                Tailwind v4 source (design tokens live here)
│   └── js/app.js                    HTMX/Alpine glue (chart hydration, x-rupiah)
└── docs/colors.png                  brand palette source
```

## Dev setup (Windows / PowerShell)

```powershell
# 1. Virtualenv & deps (first time only)
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Build the Tailwind output once
.\.venv\Scripts\tailwindcss.exe -i static/css/input.css -o static/css/output.css --minify

# 3. Migrations + first user
python manage.py migrate
python manage.py createuser admin --superuser --display-name "Admin"
python manage.py createuser wife  --display-name "Wife"

# 4. Run the server (LAN access for your phone)
python manage.py runserver 0.0.0.0:8000
```

Open `http://localhost:8000/` (or `http://<your-LAN-IP>:8000/` from your phone). Sign in — you'll be asked to set a real password on first login.

For LAN access from another device the first time, Windows will prompt for a firewall rule; allow it for **Private** networks only.

### Watching CSS while you develop

```powershell
.\.venv\Scripts\tailwindcss.exe -i static/css/input.css -o static/css/output.css --watch
```

### User management

There's no web UI for creating users — that's deliberate. Use the management commands:

```powershell
python manage.py createuser <username> [--superuser] [--display-name "..."]
python manage.py setpassword <username>                # forces change-on-next-login
python manage.py setpassword <username> --no-force-change
```

Both prompt for the password by default; pass `--password "..."` for non-interactive use (don't put real secrets on the command line on a shared machine).

## How the pieces fit

### Pockets are wallets, plus categories on every transaction

A **Pocket** is a place money lives — your BCA account, cash, GoPay, whatever. Pockets nest: `Main → BCA → Emergency Fund`. Balances roll up the tree.

A **Category** is a tag on each income or expense row (Food, Salary, Transport). Independent of which pocket the money's in.

A **Transfer** moves balance between two pockets without affecting income/expense reports — it's a separate row type, not a pair of fake transactions.

### Sharing inherits down the tree

When you share a parent pocket with someone (with `view` or `manage`), they automatically get the same access to every descendant. Permission checks walk up the ancestor chain looking for an accepted share — see `apps/pockets/permissions.py`. The recipient sees shared pockets in a separate "Shared with you" section on their pockets page; the dashboard and ledger transparently include them.

### Reports are server-built

The reports view assembles full ApexCharts options dicts in Python (`apps/reports/services.py::*`) and ships them through `json_script` blocks. `static/js/app.js` parses the JSON, applies an IDR axis formatter, and instantiates the chart. The same handler runs on `htmx:afterSwap`, so changing the period filter re-renders the charts in place without leaking the previous instances.

## Verification

A quick smoke test, with two users (`admin` and `wife`) and the BCA pocket shared with `wife` at `manage`:

1. **Login** at `/accounts/login/`. First-time login redirects to `/accounts/change-password/`.
2. **Pockets** at `/pockets/` — you should see Main (auto-bootstrapped). Create "BCA" under Main.
3. **Add transactions** via the FAB (mobile) or sidebar (desktop):
   - Income Rp 5.000.000 (Salary) → BCA
   - Expense Rp 250.000 (Food) → BCA
   - Transfer Rp 1.000.000 from BCA → Main
4. **Verify balances**: BCA = Rp 3.750.000, Main subtree total = Rp 4.750.000.
5. **Share** BCA with `wife` (manage), accept from wife's `/pockets/inbox/`.
6. **Reports** at `/reports/` — all four panels render with IDR-formatted axes.
7. **Permissions**: visit a non-shared pocket as `wife` → 403. Visit `/does-not-exist/` → 404.

## What's not in the MVP

These are explicitly deferred:

- **Production deployment** to the existing DigitalOcean droplet. `config/settings/prod.py` has the Postgres skeleton; Gunicorn/Nginx/systemd are a follow-up plan.
- **Restore-from-archive UI** for pockets (model supports it; no view yet).
- **CSV import/export.**
- **Multi-currency.** Out of scope by design.

## Operating notes

- `db.sqlite3`, `staticfiles/`, `static/css/output.css`, and `.env` are gitignored. `output.css` rebuilds in seconds — don't commit it.
- The dev settings allow any host (`ALLOWED_HOSTS = ["*"]`) so you can hit the server from a phone on the LAN. Prod settings tighten this back down.
- The `pytailwindcss` package downloads a platform-specific Tailwind v4 binary on first run; no Node toolchain needed.
- Tailwind v4 uses a CSS-based config (`@theme { ... }`), not `tailwind.config.js`. Brand colors and other tokens live in `static/css/input.css`. Dynamic class names (e.g., `bg-{{ color_token }}`) are safelisted via `@source inline(...)` in the same file.

## Project layout cheatsheet

| You want to... | Look in |
|---|---|
| Add a brand color | `static/css/input.css` (the `@theme` block) |
| Add a new pocket icon | `apps/pockets/models.py` (`POCKET_ICON_CHOICES`) |
| Change permission rules | `apps/pockets/permissions.py` |
| Add a new chart | `apps/reports/services.py` + `templates/reports/_panels.html` |
| Change the IDR formatter | `apps/core/templatetags/money.py` and `static/js/app.js` |
| Tweak the mobile shell | `templates/partials/{app_bar,bottom_tabs,fab,sidebar}.html` |
| Add an eye toggle to another balance | `templates/partials/balance.html` (include with `key=` and optional `text_class=`) — keys live under `localStorage` namespace `pocket-balance-vis:` |
