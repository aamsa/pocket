# Handoff — what got built, why, and what to read next

This is the "you're picking the project up after a long break" document. It tells you what shipped, what's deferred, what's load-bearing, and what to read in what order.

## Reading order

1. **PRODUCT.md** — strategic. Who Pocket is for, brand personality, anti-references, the five design principles (especially "Money is private; reveal is deliberate" — that's the central UX primitive).
2. **DESIGN.md** — visual. Cream-to-mocha palette, Inter type system, two-shadow elevation, component spec. The frontmatter is normative; the prose contextualizes.
3. **CLAUDE.md** — operating manual for working in the repo (conventions, motion tokens, balance partial scope).
4. **README.md** — features list + dev setup.
5. **DEPLOY.md** — production runbook for `pocket.ionyx.org`.

## What's live

- **Production URL**: <https://pocket.ionyx.org>
- **Origin**: DigitalOcean droplet at `mydroplet`, port 8002, Postgres 16, Nginx + Cloudflare Full mode + snakeoil cert
- **Seeded accounts**:
  - `aamsa` / `poer123` (superuser, display name "Aamsa")
  - `raypchl` / `raypchl` (member, display name "Ray")
- **Latest deployed commit**: see `git log origin/main -1` after this hand-off lands

## What got built (chronological, four passes)

### Pass 1 — Emil-style motion polish

Audited motion vocabulary across every interactive element and fixed the systemic gaps:

- Easing tokens added to `static/css/input.css`: `--ease-snap` (UI default, `cubic-bezier(0.23, 1, 0.32, 1)`), `--ease-glide` (on-screen movement). Plus the iOS-drawer curve on the FAB sheet.
- `.htmx-settling` switched from `ease-in` (Emil rule violation — delays the moment the user is watching most) to `var(--ease-snap)`.
- Buttons (`.btn-primary/.btn-secondary/.btn-ghost`) and `.input` now declare exact transition properties + duration + curve instead of the bare `transition` shorthand. Added `active:scale-[.98]` to `.btn-ghost` (was missing). Switched button focus rings to `focus-visible:` so mouse / touch press doesn't leave a stuck ring.
- Account dropdown: scale-95 → scale-100 enter from `origin-top-right` (anchored to the avatar trigger), explicit Alpine `x-transition:enter` / `x-transition:leave`.
- Django messages animate slide-down + fade in / slide-up + fade out, per-message dismiss.
- `prefers-reduced-motion` block disables `:active` transforms and degrades movement-based entrances to opacity-only fades.
- ApexCharts: initial render animates, period-swap re-renders don't (`dynamicAnimation.enabled: false`).

### Pass 2 — Impeccable polish

Setup: `PRODUCT.md`, `DESIGN.md`, `DESIGN.json` (Stitch format) written.

Polish:
- Contrast: every prose `text-brand-500` (~4.0:1 on cream, fails WCAG AA body) bumped to `text-brand-600` (~5.6:1). Navigation chevrons `text-brand-400` → `text-brand-500`. Balance eye toggle rest state `text-brand-300` → `text-brand-500`.
- Em dashes removed from copy across six templates (Emil and impeccable both ban them).
- `Welcome back,` greeting on Dashboard removed (PRODUCT.md explicitly bans the "Welcome back" pattern). Replaced with H1 = user's name + subtitle = today's date.
- "Add Income" / "Add Expense" Title Case → sentence case in FAB and sidebar.
- `categories/index.html` got `{% empty %}` clauses for both income and expense sections.
- `templates/pockets/detail.html` "Per-pocket transactions are coming." placeholder copy softened (later replaced entirely in Pass 3).
- Eye curtain extended to the Reports → Pocket balances chart via a `.chart-mask` overlay that mirrors `balance.html`'s idiom (chart always renders into the DOM so ApexCharts can measure it; the overlay covers it when hidden).

### Pass 3 — Per-pocket activity

**Per-pocket activity** on the Pocket detail page replaces the placeholder. Builds `rows` in `apps/pockets/views.py::detail` using the same merge-Transactions-and-Transfers logic as `apps/transactions/views.py::index`. Filter dropdown on the Transactions page also fixed to include shared pockets, not just owned.

> Earlier work in this pass also built **Scheduled income/expense (RecurringRule)** and a **Projection dashboard** at `/projections/`. Both were removed in a later cleanup — see "Pass 6 — Removed scheduled & projection features" below.

### Pass 4 — Bug bash from real-device screenshots

The user reported six concrete issues from screenshots on a real iPhone. All fixed:

| # | Symptom | Fix |
| --- | --- | --- |
| 1 | Page-header `+` button overflowing right edge | All `flex items-end justify-between` headers got `min-w-0 flex-1` on text + `shrink-0` on actions |
| 2 | "Recent activity" rows showing `S…` for category names | Restructured rows: name on line 1, chips/meta on line 2 |
| 3 | Total Balance showing `Rp 454.750.000` (12 future salaries inflating it) instead of realised `Rp 4.750.000` | At the time, `balance_for` was made to default `as_of=date.today()` to clip future-dated rule rows. Now obsolete after Pass 6 removed the scheduled feature; the default is again all-time. |
| 4 | Bottom-tab bar reading as a floating chip | Switched from `bg-brand-50/95 backdrop-blur` to opaque cream + `shadow-[0_-4px_16px_-8px_rgb(88_49_1_/_0.12)]`. Bumped `<main>` bottom padding to `calc(env(safe-area-inset-bottom)+6.5rem)` |
| 5 | Projections monthly chart wider than card | (Mooted — Projections removed in Pass 6.) |
| 6 | "M…" truncated wallet name | Same row restructure as #2 — name gets full line 1, chips drop to line 2 |

Plus pre-emptive fixes from a separate overflow audit: `.depth-row` utility for nested-pocket indent (smaller step on mobile), filter-form reflow on narrow viewports, `<main>` got `overflow-x-clip` as a safety net, breadcrumb wraps with truncated ancestor links, pocket-detail balance grid stacks to 1-col below sm.

### Pass 5 — Production deployment

Brought `pocket.ionyx.org` up on the existing droplet alongside `ionyx`, `n8n`, and `sablonmechanics-v2`. Followed the sablonmechanics-v2 pattern (Linux user `pocket`, code at `/home/pocket/apps/pocket`, env at `/etc/pocket.env`, Gunicorn on `127.0.0.1:8002`, Nginx + snakeoil cert + Cloudflare Full mode, Postgres 16). See **DEPLOY.md** for the runbook.

### Pass 6 — Removed scheduled & projection features

Per user request, the **`RecurringRule`** model + materialiser and the **`/projections/`** dashboard were both removed:

- Deleted `apps/projections/` and `templates/projections/`, plus `templates/recurring/`, `apps/transactions/recurring.py`, and the `RecurringRule` model.
- Hard-deleted every `Transaction` row generated by a rule (past and future), then dropped `Transaction.recurring_rule` and the `RecurringRule` table — see migration `apps/transactions/migrations/0003_remove_recurring.py`.
- Stripped sidebar / settings / transactions-page nav entries, the `show_planned` filter, and the "Planned" chip on `_list.html`.
- Reverted the past-only-by-default filtering on Dashboard aggregates / latest list / Transactions index, and dropped the `as_of=date.today()` default on `balance_for`.
- The `_running_balance_at` helper in `apps/reports/services.py` was kept — Reports' own pocket-balances chart still uses it.

## What's deferred (still not built)

- **CSV import / export.** Useful for migrating existing spreadsheet data; not blocking.
- **Soft-delete restore UI for pockets.** The model supports archive + unarchive (the `archive`/`unarchive` views exist), but there's no list of archived pockets to restore from. Today, restoring requires the Django shell.
- **Multi-currency.** Out of scope by design — IDR-only is a deliberate constraint.
- **Pocket-level transaction filtering visualisation tweaks.** Period filtering on the Pocket detail's Recent activity card. Today the activity card just shows the latest 10 rows; users have to click View all to filter.
- **Notification system / email digests.** Not on the roadmap.

## Load-bearing details (don't refactor without preserving these)

1. **Eye toggle / chart-mask system.** `templates/partials/balance.html` keeps its Alpine state inlined (not registered via `Alpine.data()`) after a stale-cache incident on iOS Safari. The `.chart-mask` sister system in `static/css/input.css` and the `pocket-balance-vis:` localStorage namespace are the same primitive. Documented in CLAUDE.md.

2. **Motion conventions.** Easing tokens (`--ease-snap`, `--ease-glide`) and the focus-visible/focus split are documented in CLAUDE.md. Don't introduce one-off cubic-beziers; extend the token set.

3. **No Django admin.** The default `django.contrib.admin` is intentionally absent from `INSTALLED_APPS`. All operations are CLI commands or custom pages. Don't add the admin back without thinking through the design implications.

4. **No public registration.** Accounts are seeded via `python manage.py createuser` and gated by the auth middleware. There is no `/register` route — by design.

## Operational notes

- **Backups**: not yet configured. The droplet has DigitalOcean's snapshot facility, but Pocket-specific Postgres dumps aren't running on a schedule. Before relying on this for real money, set up a daily `pg_dump pocket` cron and copy off-droplet (e.g., to Backblaze or to a Tailscale-reachable NAS).
- **Migrations**: every new schema change should ship behind a migration.
- **Static asset cache busting**: `STATIC_VERSION` in `/etc/pocket.env` is a unix timestamp the templates append to `output.css` and `app.js`. Bump it after a CSS / JS deploy and `systemctl restart pocket`.
- **Cloudflare SSL mode**: must stay on **Full** (not Full Strict). Origin uses snakeoil; Full Strict would refuse the connection.
- **Logs**: `journalctl -u pocket` is the gunicorn log (access + error). Nginx access goes to `/var/log/nginx/access.log` (all vhosts mixed; grep for `pocket.ionyx.org`).

## Things to watch the first week

- Whether real users hit any overflow / truncation regressions on devices we didn't test (iPhone SE 320px is the floor we tested at; older Android phones may render differently).
- Postgres connection count — `sudo -u postgres psql -c 'SELECT count(*) FROM pg_stat_activity'` periodically, since other services on the droplet share the same Postgres instance.
- Memory pressure — droplet is 1 GB; `free -h` and `journalctl -u pocket | grep -i 'memory\|killed'`. If gunicorn workers OOM, drop `--workers 2` to `--workers 1` in `/etc/systemd/system/pocket.service`.
- Cloudflare Analytics → check for unexpected traffic. Pocket has 2 known users; anything else is a probe and should be quiet.

## What I'd do next

If picking this up, in order of leverage:
1. **Backups.** Daily `pg_dump pocket | xz` to off-droplet storage. Single most important missing piece.
2. **Archive-restore UI for pockets.** Closes the "model supports it but no view" loop; small surface.
3. **CSV import.** Lets the user migrate any pre-existing spreadsheet data.
4. **Per-pocket transaction filtering** on the detail page (period picker on the activity card).
5. **Tests.** No automated tests yet. The verification flow in README.md is manual; first targets for `pytest` would be the `balance_for` semantics and the period-filter logic in `apps/reports/services.py`.
