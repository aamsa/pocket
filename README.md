# Pocket

> Mindful money for two — a private, mobile-first finance web app.

A self-hosted finance tracker for a household of two. Log **income and expense** in seconds, tag each entry with a category, and open a **rich dashboard** that answers *"where did the money go this month?"*, *"are we on pace with the food budget?"*, and *"how are we tracking toward our goals?"* — for yourself or the whole household.

Built with Django 5 + HTMX + Alpine.js + Tailwind v4 + ApexCharts. Single-developer scale, IDR-only, designed first for the phone.

> **May 2026 revamp.** Pocket used to model a *tree of pockets* with transfers between them, pocket sharing, and credit-card cycles. That was painful to keep in sync with real accounts, so it was replaced with the simple income/expense ledger described here. The pocket tree, transfers, sharing, and installments are gone — as are net-worth tracking and payment sources, removed in a later May 2026 change.

---

## Features

- **Invite-only auth.** No public registration. Superusers create accounts (from the web or the CLI); new users are forced to change their temporary password on first login.
- **Income & expense ledger.** Two first-class kinds, each with a category (Salary, Food, Transport, … defaults ship; add your own). No accounts-with-balances, no transfers — just money in and money out.
- **Household view.** Each person owns their ledger; a household toggle on the dashboard and reports sums both partners and breaks figures down per person.
- **Manage My Family.** Every member sees the family roster; the **head of household** can add members (by username), remove them, and rename the family.
- **User administration (superuser).** A web page to list every account, create users, and reset any user's password — no shell required.
- **Rich, filterable dashboard.** Period income/expense/net summary, income-vs-expense bars, spending-by-category donut (tap to expand), budget pace bars, goal progress, and a latest-activity list — all filterable by period, category, and person. The summary reflects the active filter, so picking a category shows that category's spend.
- **Budgets with pace.** Set a monthly limit per category; a bar shows spent-vs-limit with a marker for how much of the month has elapsed, flagging *on track / spending fast / over*.
- **Savings goals.** Set a target (and optional date); track contributions and see the monthly amount needed to reach it.
- **Recurring entries.** Define salary / rent / subscriptions on a weekly or monthly cadence; a nightly job auto-creates them (marked with an **Auto** chip).
- **Mobile-first UI.** Bottom tab bar + center FAB on mobile, sidebar on desktop. IDR formatting (`Rp 1.250.000`) everywhere. Warm cream/brown brand palette from `docs/colors.png`.

## Stack

| Layer | Choice |
|---|---|
| Web framework | Django 5 |
| Templates | Server-rendered Django + HTMX 2 partials |
| Client interactivity | Alpine.js 3 (CDN) |
| Styling | Tailwind CSS v4 (CSS-based config, standalone CLI — no Node) |
| Charts | ApexCharts via CDN |
| Icons | Lucide via CDN |
| Database | SQLite (dev) · Postgres (prod) |
| Auth | Django stock `auth_user` + a tiny `UserProfile` |
| Python | 3.14 |

## Project layout

```
pocket/
├── config/                          Django project package
│   └── settings/{base,dev,prod}.py  split settings; manage.py defaults to dev
├── apps/
│   ├── accounts/                    auth, UserProfile (display name), mgmt commands, middleware
│   ├── transactions/                Category, Transaction; forms/views/urls; default-data seeding
│   ├── ledger/                      Household, Budget, Goal, RecurringRule; services; jobs
│   ├── reports/                     period filter + ApexCharts data builders
│   └── core/                        dashboard, money template tags, context processor
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

# 3. Migrations + users + household
python manage.py migrate                    # seeds default categories
python manage.py createuser admin --superuser --display-name "Admin" --password "TestPass456!"
python manage.py createuser wife  --display-name "Wife" --password "WifePass456!"
python manage.py seed_household admin wife   # Household + memberships

# 4. Run the server (LAN access for your phone)
python manage.py runserver 0.0.0.0:8000
```

Open `http://localhost:8000/` (or `http://<your-LAN-IP>:8000/` from your phone). Sign in — you'll set a real password on first login.

### Watching CSS while you develop

```powershell
.\.venv\Scripts\tailwindcss.exe -i static/css/input.css -o static/css/output.css --watch
```

### Scheduled jobs (run manually in dev)

```powershell
python manage.py run_recurring        # materialise any due recurring rules into transactions
```

Accepts `--date YYYY-MM-DD` for backfill and is idempotent. In production it runs nightly via a systemd timer (see `DEPLOY.md`).

### User management

Superusers manage accounts from the web (Settings → **Manage users**: list, create, reset passwords). The CLI commands remain, handy for bootstrapping the very first superuser:

```powershell
python manage.py createuser <username> [--superuser] [--display-name "..."] [--password "..."]
python manage.py setpassword <username>                # forces change-on-next-login
python manage.py setpassword <username> --no-force-change
```

## How the pieces fit

### A transaction is income or expense, tagged with a category

Every row is one of two kinds. A **Category** (Food, Salary, …) classifies it. Each transaction is **owned** by one person.

### Household = combined view, not per-object sharing

A `Household` groups members (`HouseholdMember`, one per user). The dashboard/reports "Who" filter switches between *Me*, a specific member, and *Everyone*; `household_user_ids(user)` and `scope_owner_ids(user, person)` resolve that into the owner ids each query/chart uses.

### Reports are server-built

The reports and dashboard views assemble full ApexCharts options dicts in Python (`apps/reports/services.py`) and ship them through `json_script` blocks. `static/js/app.js` parses the JSON, applies an IDR axis formatter, and instantiates the chart — re-running on `htmx:afterSwap` so filter changes re-render in place without leaking instances.

## Verification

A quick smoke test with `admin` + `wife` in one household:

1. **Login** at `/accounts/login/`; first login redirects to change-password.
2. **Add entries** via the FAB / sidebar: an expense and an income. Confirm they appear in the latest-activity list and the period Income/Expense/Net summary updates.
3. **Filters** — change period / category / person on the dashboard and transactions list; panels swap via HTMX without a full reload. Pick a category and confirm the summary card shows that category's total and the donut renders it.
4. **Budgets** (`/ledger/budgets/`) — set a limit for the expense's category; the pace bar reflects spend vs limit with a today marker. Add more expense and watch it flip to *over*.
5. **Goals** (`/ledger/goals/`) — create a goal, contribute, see progress + projection.
6. **Recurring** (`/ledger/recurring/`) — create a monthly rule with next-run today, run `python manage.py run_recurring`, confirm a new transaction with the **Auto** chip and an advanced next-run.
7. **Household** — log in as `wife`, add entries; switch the dashboard "Who" to *Everyone* and confirm the combined total + per-person breakdown.

## What's not in scope yet

- **AI insights** (monthly summary / "ask your money" chat) — the planned next step.
- **CSV import / export.**
- **Multi-currency.** Out of scope by design.
- **Automated tests.** Verification is manual + shell/test-client smoke checks; no `pytest` yet.

## Production

Pocket is deployed to <https://pocket.ionyx.org>. Operations runbook: [`DEPLOY.md`](DEPLOY.md). Project handoff: [`HANDOFF.md`](HANDOFF.md).

## Operating notes

- `db.sqlite3`, `staticfiles/`, `static/css/output.css`, and `.env` are gitignored. `output.css` rebuilds in seconds — don't commit it.
- The dev settings allow any host (`ALLOWED_HOSTS = ["*"]`) so you can hit the server from a phone on the LAN. Prod settings tighten this back down.
- The `pytailwindcss` package downloads a platform-specific Tailwind v4 binary on first run; no Node toolchain needed.
- Tailwind v4 uses a CSS-based config (`@theme { ... }`), not `tailwind.config.js`. Dynamic class names (e.g., `bg-{{ category.color_token }}`) are safelisted via `@source inline(...)` in `static/css/input.css`.

## Project layout cheatsheet

| You want to... | Look in |
|---|---|
| Add a brand color | `static/css/input.css` (the `@theme` block) |
| Add a category icon | `apps/transactions/models.py` (`CATEGORY_ICON_CHOICES`) |
| Change budget / goal / recurring logic | `apps/ledger/services.py` |
| Add or change a chart | `apps/reports/services.py` + the dashboard / reports panel templates |
| Change the IDR formatter | `apps/core/templatetags/money.py` and `static/js/app.js` |
| Tweak the mobile shell | `templates/partials/{app_bar,bottom_tabs,fab,sidebar}.html` |
| Change the income/expense/net summary card | `templates/partials/period_summary.html` |
