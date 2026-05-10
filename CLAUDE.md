# Pocket — project guide for Claude Code

A private, mobile-first personal finance web app for two people (the owner and his wife). Tracks earnings, spending, and transfers across hierarchical "pockets" with sharing and period-filtered reports.

## Always

- **Keep docs in sync with code.** README.md and this file describe what's actually shipped. Update them in the same change as the code.
- **Never use Django's built-in admin UI.** All admin actions are either custom pages or management commands.
- **Currency is IDR only.** Amounts are integers (no decimals). Display via the `rupiah` template filter, format input via the `x-rupiah` Alpine directive.
- **Mobile-first.** Designs start at iPhone width; desktop is the layered enhancement (sidebar instead of bottom tabs).
- **Brand palette only.** Cream-to-mocha browns from `docs/colors.png`, mapped to `--color-brand-{50..900}` in `static/css/input.css`. Income uses `#5C8A4E` (sage), expense uses `#9C3D2E` (terracotta) — those are the only two off-palette accents allowed.

## Installed skills

The project's recommended skills are pinned in `skills-lock.json` (committed). The skill content itself is gitignored — install per-machine with `npx skills add <repo>` (it reads the lock for hash verification).

- **`emil-design-eng`** (Emil Kowalski's design-engineering skill). Use proactively when reviewing or polishing UI — animation timing, transition curves, transform-origin choices, the small details that make the brown/cream palette feel right.
  - Install: `npx skills add emilkowalski/skill`
  - Lives at `.agents/skills/emil-design-eng/SKILL.md`; a junction at `.claude/skills/emil-design-eng/` makes Claude Code's discovery pick it up.
  - On Windows, the `.claude/skills/` junction needs to be recreated after a fresh install:
    `New-Item -ItemType Junction -Path .claude\skills\emil-design-eng -Target .agents\skills\emil-design-eng`

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
apps/transactions/                     Category, Transaction, Transfer
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
  - **Scope is standing balances only.** Use the partial for: the Dashboard *Total Balance* card, every pocket-row balance on the Pockets list, the two balance cards on the Pocket detail page. The **Reports → Pocket balances chart** also has a curtain — it uses the `.chart-mask` wrapper (see `templates/reports/_panels.html`), not the partial. The partial wraps a number; the chart curtain wraps a chart with an overlay so ApexCharts can still measure its width. Both share the localStorage namespace `pocket-balance-vis:` (chart key: `pocket-balance-vis:reports:pocket-balances`). **Do NOT add either curtain to** the Dashboard income/expense aggregates, transaction-row amounts, transfer rows, transactions filter list, the Income vs Expense / Spending by category / Top transactions panels on Reports, transaction form input. The user explicitly excluded these — don't add eyes there without asking first.
  - Alpine state is **inlined in the partial**, not registered via `Alpine.data()`. This was deliberate after a stale-cache incident on iOS Safari left the click handler dead. Keep it inline.

## Motion conventions

UI motion follows Emil Kowalski's design-engineering rules. The `emil-design-eng` skill captures the full ruleset; the project-specific bits are:

- **Easing tokens.** `--ease-snap` (`cubic-bezier(0.23, 1, 0.32, 1)`) is the UI default; `--ease-glide` (`cubic-bezier(0.77, 0, 0.175, 1)`) is for on-screen movement; the FAB sheet uses the iOS-drawer curve `cubic-bezier(0.32, 0.72, 0, 1)`. Both `--ease-*` tokens are exposed as Tailwind utilities (`ease-snap`, `ease-glide`). Don't introduce one-off curves — extend the token set instead.
- **Never use `ease-in` for UI.** It delays the moment the user is watching most. The `.htmx-settling` class is the canonical example of the trap.
- **Buttons declare exact properties.** `.btn-primary/.btn-secondary/.btn-ghost/.input` use explicit `transition: transform … , background-color … , …` — never the bare `transition` shorthand (which animates `all` via Tailwind's class).
- **`focus-visible:` over `focus:` for buttons.** Mouse/touch press shouldn't leave a ring; keyboard focus should. `.input` keeps `focus:` because form fields legitimately need a focus ring on click.
- **Press feedback is mandatory on tappable rows and nav.** `active:scale-[.96..99]` for hot-path nav (sidebar/bottom-tabs); buttons already have `active:scale-[.98]`. No colour transition on hot-path nav (frequent action — Emil's frequency rule).
- **Origin-aware popovers.** Anchored popovers (account dropdown) need `origin-top-right` (or matching origin) so the scale animation comes out of the trigger. Modals stay centered — they're not anchored.
- **`prefers-reduced-motion` block at end of `input.css`** disables transforms on `:active` and degrades movement-based entrances to opacity-only fades. Reduce, don't remove — keep opacity/colour cues.
- **ApexCharts: initial render animates, swaps don't.** The `_ANIMATIONS` constant in `apps/reports/services.py` sets `dynamicAnimation.enabled: false` so period-filter swaps stay crisp. Reuse it for any new chart.

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

- **Soft-delete restore UI** for archived pockets (the model supports it; no view yet).
- **CSV import/export.**
- **Multi-currency** (explicitly out of scope for this MVP).
- **Automated tests.** The README's verification flow is manual; no `pytest` yet.

## Production

The app is live at <https://pocket.ionyx.org> on a DigitalOcean droplet. The production settings module is `config.settings.prod` driven by `/etc/pocket.env` on the droplet. Full operational runbook lives in [`DEPLOY.md`](DEPLOY.md); the broader project handoff (what shipped, what's load-bearing, what's deferred) is in [`HANDOFF.md`](HANDOFF.md). Key operational rules:

- **Don't disturb co-tenant services** on the droplet (`ionyx`, `n8n`, `sablonmechanics-v2`, plus other ionyx subdomain vhosts). Pocket is isolated to its own user (`pocket`), port (`127.0.0.1:8002`), database (`pocket`), env file (`/etc/pocket.env`), systemd unit (`pocket.service`), and Nginx vhost (`pocket.ionyx.org`).
- **Cloudflare SSL mode is Full** (not Full Strict). The origin uses snakeoil; Full Strict would refuse the handshake.
