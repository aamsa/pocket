# Pocket — project guide for Claude Code

A private, mobile-first personal finance web app for two people (the owner and his wife). A simple **income/expense ledger** with categories and an optional payment **source** tag, a rich filterable dashboard (net-worth trend, cash flow, spending breakdowns, budget pace, goals), monthly budgets, savings goals, and auto-recurring entries. No accounts-with-balances, no transfers, no pocket tree — that earlier model was removed in the May 2026 revamp because the transfer pass-through was painful to keep in sync.

## Always

- **Keep docs in sync with code.** README.md and this file describe what's actually shipped. Update them in the same change as the code.
- **Never use Django's built-in admin UI.** All admin actions are either custom pages or management commands.
- **Currency is IDR only.** Amounts are integers (no decimals). Display via the `rupiah` template filter, format input via the `x-rupiah` Alpine directive (or the inline amount-formatting `x-data` used on the transaction form).
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
- SQLite for dev (`db.sqlite3`, gitignored). Postgres for prod (`config/settings/prod.py`).
- `pytailwindcss` provides the standalone Tailwind binary; no Node required.

## Where things live

```
config/settings/{base,dev,prod}.py     dev defaults to settings.dev via manage.py
apps/accounts/                         auth, UserProfile (display name + starting balance), force-password-change, mgmt commands
apps/transactions/                     Category, Source, Transaction; their forms/views/urls; default-data seeding signal
apps/ledger/                           Household, HouseholdMember, Budget, Goal, RecurringRule, DailyBalanceSnapshot;
                                         services.py (balance, snapshot, recurring, budget, goal); management commands
apps/reports/                          period filter + ApexCharts data builders (income/expense, category, source, net worth)
apps/core/                             dashboard, money template tags (rupiah, balance_key, index), context processor
templates/                             project-level (base.html + partials/, page templates)
templates/partials/balance.html        amount + per-balance eye toggle (used for standing balance figures)
templates/dashboard/_panels.html       the rich dashboard panels (HTMX swap target)
templates/ledger/{budgets,goals,recurring}/   ledger page templates
static/css/input.css                   Tailwind v4 source — all design tokens defined here
static/js/app.js                       HTMX/Alpine glue: chart hydration, x-rupiah directive
docs/colors.png                        brand palette source
```

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

# user + household management (no web UI — superuser only)
python manage.py createuser <username> [--superuser] [--display-name "..."] [--password "..."]
python manage.py setpassword <username>
python manage.py seed_household <username> [<username> ...] [--name "Household"]

# scheduled jobs (run nightly in prod; manual in dev)
python manage.py run_recurring [--date YYYY-MM-DD]        # materialise due recurring rules
python manage.py snapshot_balances [--date YYYY-MM-DD]    # write daily net-worth snapshot
```

`output.css` is gitignored — rebuild after changing templates that introduce new utility classes, or run watch mode while developing.

## Conventions

- **UUID primary keys** on every domain model (Category, Source, Transaction, Household, HouseholdMember, Budget, Goal, RecurringRule, DailyBalanceSnapshot).
- **Ownership, not permissions.** Each `Transaction` has an `owner` (the person whose money it is). Scope a single user's data with `Transaction.objects.for_user(user)`; scope the whole household with `.for_household(user)`. There is no permission decorator and no per-object sharing — household membership is the only sharing mechanism.
- **Household scoping.** `apps.ledger.services.household_user_ids(user)` is the canonical way to get the set of user ids in a combined view (returns `[user.id]` if the user isn't in a household). `household_members(user)` returns the User objects. `apps.reports.services.scope_owner_ids(user, person)` resolves a `person` filter value (`"me"` | `"household"` | a specific user id) into owner ids for charts. A user belongs to exactly one `Household` via the `HouseholdMember` OneToOne; seed it with `seed_household`.
- **Sources are an optional flat tag.** A `Source` (BCA / Cash / GoPay / Card …) is *not* an account with a balance and there are no transfers. `Transaction.source` is a nullable FK (`SET_NULL`). Sources are **household-scoped** (`Source.objects.for_household(household)`) so both partners pick from one list. Seeded with `household=None` by the `post_migrate` signal, then claimed by `seed_household`.
- **Net worth = one starting figure + flows.** Each `UserProfile` carries `starting_balance` + `starting_balance_as_of`. `apps.ledger.services.current_balance(user, as_of=None)` = `starting_balance + Σincome − Σexpense` over transactions with `occurred_on >= starting_balance_as_of` (and `<= as_of`). `household_balance(user)` sums members. The trend line is fed by **daily snapshots** (`DailyBalanceSnapshot`, one row per user per day) written by the `snapshot_balances` command — never recomputed live from transactions in the chart builder.
- **Default categories + starter sources** are seeded by a `post_migrate` signal in `apps.transactions.signals` (idempotent). Don't let users edit default categories — gate edits on `is_default=False AND created_by==user`.
- **Forms get a `user=` kwarg** so they can scope querysets and stamp `owner`/`created_by`/`household`. Don't read `request.user` inside a form. Unique constraints that span fields set in `save()` (Budget `(user, category, month)`; Source `(household, name)`) are validated in the form's `clean()` so a duplicate shows a friendly error instead of a 500.
- **HTMX swap pattern**: views check `request.headers.get("HX-Request")` and return the inner partial vs the full page from the same view function. Dashboard → `dashboard/_panels.html`; transactions → `transactions/_list.html`; reports → `reports/_panels.html`. Filter forms `hx-get` the same view with `hx-push-url="true"`.
- **Budgets + pace.** A `Budget` is a monthly per-category limit (`month` normalised to day-1). `apps.ledger.services.budget_status(user, month)` returns rows with `spent`, `limit`, `remaining`, `pct`, `time_pct`, and a `signal` of `over` (spent > limit) / `fast` (spending faster than the share of the month elapsed) / `on_track`. The dashboard + budgets page render a bar coloured by signal with a tick marker at `time_pct`.
- **Goals.** A `Goal` has `target_amount` + a single mutable `current_amount` (funding is intentionally decoupled from the ledger — there are no accounts to move money between). `goal_status(goal)` returns `pct`, `remaining`, `days_left`, and `needed_per_month`. Contributions adjust `current_amount` via the `goal_contribute` POST.
- **Recurring entries.** A `RecurringRule` (kind, amount, category, source, `cadence` weekly|monthly, `anchor_day`, `next_run`, `active`) is materialised into `Transaction`s by `apps.ledger.services.materialize_recurring()` (the `run_recurring` command). It loops to catch missed runs and advances `next_run` (weekly → +7d; monthly → next month clamped to `anchor_day` via `_clamp_day_to_month`). Generated transactions carry a `recurring_rule` FK and render an **Auto** chip in the list.
- **ApexCharts**: build the full options dict server-side (in `apps/reports/services.py`), pass through `json_script`, hydrate in `static/js/app.js` on `htmx:afterSwap` so charts re-render cleanly through swaps. Add `_format: "rupiah"` to apply the IDR axis/tooltip formatter.
- **Dynamic Tailwind classes** like `bg-{{ source.color_token }}` need to appear in the `@source inline(...)` safelist in `input.css` since the scanner can't see them (the current safelist covers `bg-brand-{200..700}`).
- **Currency amounts never truncate.** Render every figure through `rupiah` + the `.num` utility; never put `truncate` on an amount (the brand shows full `Rp 1.250.000`, never `1.25jt`). In a flex row pairing a label with an amount, the **amount** is `num shrink-0` and the **label** is `min-w-0 truncate` — so the label ellipsizes and the full figure always shows. Multi-figure summaries (e.g. the dashboard Income/Expense/Net) stack to label→value rows on mobile (`grid-cols-1 sm:grid-cols-3`) rather than sitting in fixed narrow columns that clip.
- **Balance figures** — strictly *balance / net-worth* totals — render through `templates/partials/balance.html`, never as a bare `{{ amount|rupiah }}`. The partial provides the per-balance eye toggle and `localStorage` persistence under the `pocket-balance-vis:` namespace (kept for continuity across the revamp).
  - **Default is HIDDEN.** The wrapper renders with `balance-hidden` statically; Alpine removes it only when localStorage records `'1'` for the key. The user always sees `Rp ••••` first and reveals deliberately.
  - Build composite keys with `{% balance_key ... as bkey %}` (from `apps.core.templatetags.money`) — Django's stock `add` filter can't concat `str + UUID`.
  - **Scope is standing balances only.** Use the partial for the Dashboard **Net worth** figure (key `dashboard:networth`). The net-worth **chart** uses the `.chart-mask` curtain (overlay so ApexCharts can still measure width), sharing the same key `pocket-balance-vis:dashboard:networth` so revealing one reveals the other on next load. **Do NOT** add the curtain to the income/expense/net aggregate cards, transaction-row amounts, the budget/goal/source/top-transaction panels, or form inputs — the user explicitly excluded these; don't add eyes there without asking.
  - Alpine state is **inlined in the partial**, not registered via `Alpine.data()`. Deliberate after a stale-cache incident on iOS Safari left the click handler dead. Keep it inline.

## Motion conventions

UI motion follows Emil Kowalski's design-engineering rules. The `emil-design-eng` skill captures the full ruleset; the project-specific bits are:

- **Easing tokens.** `--ease-snap` (`cubic-bezier(0.23, 1, 0.32, 1)`) is the UI default; `--ease-glide` (`cubic-bezier(0.77, 0, 0.175, 1)`) is for on-screen movement; the FAB sheet uses the iOS-drawer curve `cubic-bezier(0.32, 0.72, 0, 1)`. Both `--ease-*` tokens are exposed as Tailwind utilities (`ease-snap`, `ease-glide`). Don't introduce one-off curves — extend the token set instead.
- **Never use `ease-in` for UI.** It delays the moment the user is watching most. The `.htmx-settling` class is the canonical example of the trap.
- **List entrance** uses the `.anim-row` class (opacity-only `fade-in`) on transaction/budget/goal/recurring rows — degrades cleanly under reduced motion and re-runs pleasantly on HTMX swaps.
- **Buttons declare exact properties.** `.btn-primary/.btn-secondary/.btn-ghost/.input` use explicit `transition: transform … , background-color … , …` — never the bare `transition` shorthand (which animates `all`).
- **`focus-visible:` over `focus:` for buttons.** `.input` keeps `focus:` because form fields legitimately need a focus ring on click.
- **Press feedback is mandatory on tappable rows and nav.** `active:scale-[.96..99]` for hot-path nav (sidebar/bottom-tabs); buttons already have `active:scale-[.98]`. No colour transition on hot-path nav.
- **Origin-aware popovers.** Anchored popovers (account dropdown) need `origin-top-right` so the scale animation comes out of the trigger. Modals stay centered.
- **`prefers-reduced-motion` block at end of `input.css`** disables transforms on `:active` and degrades movement-based entrances to opacity-only fades. Reduce, don't remove.
- **ApexCharts: initial render animates, swaps don't.** The `_ANIMATIONS` constant in `apps/reports/services.py` sets `dynamicAnimation.enabled: false` so filter swaps stay crisp. Reuse it for any new chart.

## Test users (dev DB)

If you reset the DB, recreate them with the documented flow:
```powershell
del db.sqlite3
python manage.py migrate                      # seeds default categories + starter sources
python manage.py createuser admin --superuser --display-name "Admin" --password "TestPass456!"
python manage.py createuser wife --display-name "Wife" --password "WifePass456!"
python manage.py seed_household admin wife     # Household + memberships + claims the seeded sources
```
Both users start with `force_password_change=True`, so the first browser login redirects to change-password (set a real one or clear the flag in the shell for testing).

## Deferred (not yet shipped)

- **AI insights** (monthly summary card / natural-language "ask your money" chat) — the standout next step; intentionally skipped in v1.
- **CSV import / export.**
- **Multi-currency** (explicitly out of scope).
- **Automated tests.** Verification is manual + shell/test-client smoke checks; no `pytest` yet.
- **Removed in the revamp:** the pocket tree, transfers, pocket sharing (PocketShare), credit-card statement/due cycles, and installment plans (cicilan). Recurring covers true repetition; a decoupled "pay once over N months" feature could return later if missed.

## Production

The app is live at <https://pocket.ionyx.org> on a DigitalOcean droplet. The production settings module is `config.settings.prod` driven by `/etc/pocket.env` on the droplet. Full operational runbook lives in [`DEPLOY.md`](DEPLOY.md); the broader project handoff is in [`HANDOFF.md`](HANDOFF.md). Key operational rules:

- **Don't disturb co-tenant services** on the droplet (`ionyx`, `n8n`, `sablonmechanics-v2`, plus other ionyx subdomain vhosts). Pocket is isolated to its own user (`pocket`), port (`127.0.0.1:8002`), database (`pocket`), env file (`/etc/pocket.env`), systemd unit (`pocket.service`), and Nginx vhost (`pocket.ionyx.org`).
- **Cloudflare SSL mode is Full** (not Full Strict). The origin uses snakeoil; Full Strict would refuse the handshake.
- **Two nightly jobs** (`run_recurring` then `snapshot_balances`) run as `pocket`-owned systemd timers — recurring first so the day's auto-entries are counted in the snapshot. See DEPLOY.md. No n8n involvement.
