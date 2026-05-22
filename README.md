# Pocket

> Mindful money for two — a private, mobile-first finance web app.

A self-hosted finance tracker for a household of two. Log **income and expense** in seconds, tag each entry with a category and an optional payment **source** (BCA / Cash / GoPay / Card), and open a **rich dashboard** that answers *"what's our net worth trend?"*, *"are we on pace with the food budget?"*, and *"how much went out on GoPay this month?"* — for yourself or the whole household.

Built with Django 5 + HTMX + Alpine.js + Tailwind v4 + ApexCharts. Single-developer scale, IDR-only, designed first for the phone.

> **May 2026 revamp.** Pocket used to model a *tree of pockets* with transfers between them, pocket sharing, and credit-card cycles. That was painful to keep in sync with real accounts, so it was replaced with the simple income/expense ledger described here. The pocket tree, transfers, sharing, and installments are gone.

---

## Features

- **Invite-only auth.** No public registration. The superuser bootstraps accounts via a CLI command. New users are forced to change their temporary password on first login.
- **Income & expense ledger.** Two first-class kinds, each with a category (Salary, Food, Transport, … defaults ship; add your own) and an optional **source** tag. No accounts-with-balances, no transfers — just money in and money out.
- **Net worth from one figure.** Set your starting balance once; the app runs it forward (`start + income − expense`) and snapshots it daily into a **net-worth trend line**. Correct the figure anytime.
- **Household view.** Each person owns their ledger; a household toggle on the dashboard and reports sums both partners and breaks figures down per person.
- **Rich, filterable dashboard.** Net-worth hero chart, period income/expense/net, income-vs-expense bars, spending-by-category donut (tap to expand), spending-by-source, budget pace bars, goal progress, and a latest-activity list — all filterable by period, category, source, and person.
- **Budgets with pace.** Set a monthly limit per category; a bar shows spent-vs-limit with a marker for how much of the month has elapsed, flagging *on track / spending fast / over*.
- **Savings goals.** Set a target (and optional date); track contributions and see the monthly amount needed to reach it.
- **Recurring entries.** Define salary / rent / subscriptions on a weekly or monthly cadence; a nightly job auto-creates them (marked with an **Auto** chip).
- **Mobile-first UI.** Bottom tab bar + center FAB on mobile, sidebar on desktop. IDR formatting (`Rp 1.250.000`) everywhere. Warm cream/brown brand palette from `docs/colors.png`.
- **Net worth hidden by default.** The dashboard balance figure and trend chart render as `Rp ••••` until you tap the eye; the choice persists per device in `localStorage`. Flow figures, transaction rows, and breakdown panels are intentionally always visible.

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
│   ├── accounts/                    auth, UserProfile (display name + starting balance), mgmt commands, middleware
│   ├── transactions/                Category, Source, Transaction; forms/views/urls; default-data seeding
│   ├── ledger/                      Household, Budget, Goal, RecurringRule, DailyBalanceSnapshot; services; jobs
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
python manage.py migrate                    # seeds default categories + starter sources
python manage.py createuser admin --superuser --display-name "Admin" --password "TestPass456!"
python manage.py createuser wife  --display-name "Wife" --password "WifePass456!"
python manage.py seed_household admin wife   # Household + memberships + claims the seeded sources

# 4. Run the server (LAN access for your phone)
python manage.py runserver 0.0.0.0:8000
```

Open `http://localhost:8000/` (or `http://<your-LAN-IP>:8000/` from your phone). Sign in — you'll set a real password on first login, then set your **starting balance** in Settings so the net-worth figure is meaningful.

### Watching CSS while you develop

```powershell
.\.venv\Scripts\tailwindcss.exe -i static/css/input.css -o static/css/output.css --watch
```

### Scheduled jobs (run manually in dev)

```powershell
python manage.py run_recurring        # materialise any due recurring rules into transactions
python manage.py snapshot_balances    # write today's per-user balance snapshot (feeds the net-worth chart)
```

Both accept `--date YYYY-MM-DD` for backfill and are idempotent. In production they run nightly via systemd timers (see `DEPLOY.md`).

### User management

There's no web UI for creating users — that's deliberate. Use the management commands:

```powershell
python manage.py createuser <username> [--superuser] [--display-name "..."] [--password "..."]
python manage.py setpassword <username>                # forces change-on-next-login
python manage.py setpassword <username> --no-force-change
```

## How the pieces fit

### A transaction is income or expense, tagged with a category and (optionally) a source

Every row is one of two kinds. A **Category** (Food, Salary, …) classifies it; a **Source** (BCA, Cash, GoPay, Card) optionally records where the money sat or came from — purely a label for slicing, never a balance you reconcile and never a transfer. Each transaction is **owned** by one person.

### Net worth runs forward from a single starting figure

Set `starting_balance` (+ the date it's "as of") in Settings. `apps/ledger/services.py::current_balance` computes `starting + Σincome − Σexpense` from that date forward. The `snapshot_balances` command records each user's balance daily into `DailyBalanceSnapshot`, and the dashboard/reports net-worth chart reads those snapshots — so the trend reflects history even as you correct the starting figure.

### Household = combined view, not per-object sharing

A `Household` groups members (`HouseholdMember`, one per user). The dashboard/reports "Who" filter switches between *Me*, a specific member, and *Everyone*; `household_user_ids(user)` and `scope_owner_ids(user, person)` resolve that into the owner ids each query/chart uses.

### Reports are server-built

The reports and dashboard views assemble full ApexCharts options dicts in Python (`apps/reports/services.py`) and ship them through `json_script` blocks. `static/js/app.js` parses the JSON, applies an IDR axis formatter, and instantiates the chart — re-running on `htmx:afterSwap` so filter changes re-render in place without leaking instances.

## Verification

A quick smoke test with `admin` + `wife` in one household:

1. **Login** at `/accounts/login/`; first login redirects to change-password.
2. **Settings** (`/accounts/settings/profile/`) — set a starting balance (e.g. `10.000.000`) and as-of date. The dashboard Net worth figure (tap the eye) reflects it.
3. **Add entries** via the FAB / sidebar: an expense with a source and an income. Confirm the dashboard balance = `start + income − expense` and the transaction shows its source.
4. **Filters** — change period / category / source / person on the dashboard and transactions list; panels swap via HTMX without a full reload.
5. **Budgets** (`/ledger/budgets/`) — set a limit for the expense's category; the pace bar reflects spend vs limit with a today marker. Add more expense and watch it flip to *over*.
6. **Goals** (`/ledger/goals/`) — create a goal, contribute, see progress + projection.
7. **Recurring** (`/ledger/recurring/`) — create a monthly rule with next-run today, run `python manage.py run_recurring`, confirm a new transaction with the **Auto** chip and an advanced next-run.
8. **Snapshots** — run `python manage.py snapshot_balances`; the net-worth chart renders once a snapshot exists.
9. **Household** — log in as `wife`, add entries; switch the dashboard "Who" to *Everyone* and confirm the combined total + per-person breakdown.

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
- Tailwind v4 uses a CSS-based config (`@theme { ... }`), not `tailwind.config.js`. Dynamic class names (e.g., `bg-{{ source.color_token }}`) are safelisted via `@source inline(...)` in `static/css/input.css`.

## Project layout cheatsheet

| You want to... | Look in |
|---|---|
| Add a brand color | `static/css/input.css` (the `@theme` block) |
| Add a category or source icon | `apps/transactions/models.py` (`CATEGORY_ICON_CHOICES`, `SOURCE_ICON_CHOICES`) |
| Change balance / snapshot / budget / goal / recurring logic | `apps/ledger/services.py` |
| Add or change a chart | `apps/reports/services.py` + the dashboard / reports panel templates |
| Change the IDR formatter | `apps/core/templatetags/money.py` and `static/js/app.js` |
| Tweak the mobile shell | `templates/partials/{app_bar,bottom_tabs,fab,sidebar}.html` |
| Change the net-worth eye toggle | `templates/partials/balance.html` (key namespace `pocket-balance-vis:`) |
