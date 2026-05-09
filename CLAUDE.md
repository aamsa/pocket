# Pocket — project guide for Claude Code

A private, mobile-first personal finance web app for two people (the owner and his wife). Tracks earnings, spending, and transfers across hierarchical "pockets" with sharing and period-filtered reports.

## Always

- **Keep docs in sync with code.** README.md and this file describe what's actually shipped. Update them in the same change as the code.
- **Never use Django's built-in admin UI.** All admin actions are either custom pages or management commands.
- **Currency is IDR only.** Amounts are integers (no decimals). Display via the `rupiah` template filter, format input via the `x-rupiah` Alpine directive.
- **Mobile-first.** Designs start at iPhone width; desktop is the layered enhancement (sidebar instead of bottom tabs).
- **Brand palette only.** Cream-to-mocha browns from `docs/colors.png`, mapped to `--color-brand-{50..900}` in `static/css/input.css`. Income uses `#5C8A4E` (sage), expense uses `#9C3D2E` (terracotta) — those are the only two off-palette accents allowed.

## Stack

- Django 5 (Python 3.14), HTMX 2 + Alpine 3 + ApexCharts via CDN
- Tailwind CSS v4 — the **CSS-based config** (`@theme` block in `static/css/input.css`); there is no `tailwind.config.js`.
- SQLite for dev (`db.sqlite3`, gitignored). Postgres planned for prod (`config/settings/prod.py` placeholder).
- `pytailwindcss` provides the standalone Tailwind binary; no Node required.

## Where things live

```
config/settings/{base,dev,prod}.py     dev defaults to settings.dev via manage.py
apps/accounts/                         auth, UserProfile, force-password-change, mgmt commands
apps/pockets/                          Pocket tree, PocketShare, permissions
apps/transactions/                     Category, Transaction, Transfer (yes — Transfer model lives here)
apps/reports/                          period filter + ApexCharts data builders
apps/core/                             dashboard, money template tags (rupiah, balance_key), context processors
templates/                             project-level (base.html + partials/, page templates)
templates/partials/balance.html        amount + per-balance eye toggle (used everywhere a pocket balance is shown)
static/css/input.css                   Tailwind v4 source — all design tokens defined here
static/js/app.js                       HTMX/Alpine glue: chart hydration, x-rupiah directive
docs/colors.png                        brand palette source
```

Transfer URLs are mounted at `/transfers/` from `apps/transactions/transfer_urls.py` even though the views live in `apps/transactions/views.py` — keeps URLs natural while sharing the model app.

## Common commands

```powershell
# venv (one-time)
py -m venv .venv

# every session
.\.venv\Scripts\Activate.ps1

# build CSS once
.\.venv\Scripts\tailwindcss.exe -i static/css/input.css -o static/css/output.css --minify

# build CSS in watch mode (separate terminal)
.\.venv\Scripts\tailwindcss.exe -i static/css/input.css -o static/css/output.css --watch

# run server (LAN access)
python manage.py runserver 0.0.0.0:8000

# migrations
python manage.py makemigrations <app>
python manage.py migrate

# user management (no web UI for this — superuser only)
python manage.py createuser <username> [--superuser] [--display-name "..."]
python manage.py setpassword <username>
```

`output.css` is gitignored — rebuild after changing templates that introduce new utility classes, or run watch mode while developing.

## Conventions

- **UUID primary keys** on every domain model (Pocket, PocketShare, Category, Transaction, Transfer).
- **Permission decorator** `@require_pocket_permission('view'|'manage')` from `apps.pockets.permissions` for every pocket/transaction view that takes a `pocket_id` URL kwarg.
- **`visible_pocket_ids(user)`** is the canonical way to scope queries across owned + shared pockets. Don't roll your own.
- **Default categories** are seeded by a `post_migrate` signal in `apps.transactions.signals` with `is_default=True`. Don't let users edit defaults — gate edits on `is_default=False AND created_by==user`.
- **One Main pocket per user**, enforced by a partial unique index. The post-User-creation signal in `apps.pockets.signals` bootstraps it.
- **Forms get a `user=` kwarg** so they can scope querysets and stamp `created_by`. Don't read `request.user` inside a form.
- **HTMX swap pattern**: views check `request.headers.get("HX-Request")` and return the inner partial vs the full page from the same view function.
- **ApexCharts**: build the full options dict server-side (in `apps/reports/services.py`), pass through `json_script`, hydrate in `static/js/app.js` on `htmx:afterSwap` so charts re-render cleanly through swaps. Add `_format: "rupiah"` to apply the IDR axis/tooltip formatter.
- **Dynamic Tailwind classes** like `bg-{{ pocket.color_token }}` need to appear in the `@source inline(...)` safelist in `input.css` since the scanner can't see them.
- **Balance figures** — strictly *balance* totals — should be rendered through `templates/partials/balance.html`, never as a bare `{{ amount|rupiah }}`. The partial provides the per-balance eye toggle and `localStorage` persistence under the `pocket-balance-vis:` namespace.
  - **Default is HIDDEN.** The wrapper renders with `balance-hidden` statically; Alpine removes it only when localStorage records `'1'` for the key. So the user always sees `Rp ••••` first and reveals deliberately.
  - Build the key with `{% balance_key "pocket" pocket.id "downstream" as bkey %}` (from `apps.core.templatetags.money`) — Django's stock `add` filter can't concat `str + UUID`, so don't try `"pocket:"|add:p.id`.
  - Re-using the same key on multiple pages (e.g. `pocket:<uuid>:downstream` on both pockets-index and pocket-detail) is intentional — the user expects revealing a pocket on one page to also reveal it on the other.
  - **Scope is balances only.** Use the partial for: the Dashboard *Total Balance* card, every pocket-row balance on the Pockets list, the two balance cards on the Pocket detail page. **Do NOT use it for** the Dashboard income/expense aggregates, transaction-row amounts, transfer rows, transactions filter list, reports charts/lists, transaction form input. The user explicitly excluded these — don't add eyes there without asking first.
  - Alpine state is **inlined in the partial**, not registered via `Alpine.data()`. This was deliberate after a stale-cache incident on iOS Safari left the click handler dead. Keep it inline.

## Test users (dev DB)

If `db.sqlite3` is present from prior dev work:
- `admin` / `TestPass456!` (superuser, display name "Admin" or "Aamsa" depending on whether the profile-save smoke ran)
- `wife` / `WifePass456!` (member; has BCA pocket shared with manage)

If you reset the DB, recreate them:
```powershell
python manage.py migrate
python manage.py createuser admin --superuser --display-name "Admin"
python manage.py createuser wife --display-name "Wife"
```

## Deferred (not yet shipped)

- **Production deployment.** `config/settings/prod.py` is a placeholder (Postgres connection only). No Gunicorn/Nginx/systemd config yet.
- **Recurring transactions** (e.g., monthly salary auto-post).
- **Soft-delete restore UI** for archived pockets (the model supports it; no view yet).
- **CSV import/export.**
- **Multi-currency** (explicitly out of scope for this MVP).
