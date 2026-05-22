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

## May 2026 revamp — income/expense ledger (READ THIS FIRST)

The original model (a tree of **pockets** with **transfers** between them, **PocketShare** inheritance, and credit-card statement/due cycles with **installment** plans) was removed. It was too heavy — the transfer pass-through was painful to keep in sync with real accounts. Passes 1–10 below still describe the *motion/visual* system accurately, but their **domain-model** details (pockets, transfers, sharing, cards, cicilan) are obsolete.

**What the app is now:** a flat **income/expense ledger**.

- **Models** — `Category` + `Source` + `Transaction` in `apps/transactions`; `Household`, `HouseholdMember`, `Budget`, `Goal`, `RecurringRule`, `DailyBalanceSnapshot` in the new `apps/ledger`. `Transaction` has `owner`, `category`, nullable `source`, `kind`, `amount`, `occurred_on`, `notes`, nullable `recurring_rule`. No pocket FK, no installment fields, no Transfer model.
- **Net worth** — `UserProfile.starting_balance` + `starting_balance_as_of`; `apps/ledger/services.py::current_balance` runs it forward; `DailyBalanceSnapshot` (written nightly by `snapshot_balances`) feeds the trend chart.
- **Source** — an optional, household-shared, flat payment-method tag. Not a balance, not a tree, never a transfer.
- **Household** — replaces PocketShare. One `HouseholdMember` per user; `household_user_ids` / `scope_owner_ids` scope combined views. Seeded by the `seed_household` command.
- **Budgets** — monthly per-category limits with a pace signal (`budget_status`). **Goals** — target + mutable `current_amount` (`goal_status`). **Recurring** — `RecurringRule` materialised by `run_recurring` (`materialize_recurring`), stamping `Transaction.recurring_rule` (renders an **Auto** chip).
- **Dashboard** is the headline: filterable (period / category / source / person) net-worth hero, income-vs-expense, category & source donuts, budget pace, goal progress, latest activity. Reports page reuses the same builders.
- **Scheduling** — two nightly `pocket-*` systemd timers (`run_recurring` then `snapshot_balances`); see DEPLOY.md. No n8n.
- **Data** — migration history for `transactions`/`ledger` was reset; `accounts` got an additive `0002`. Dev is a fresh start. **Prod is migrated** via `manage.py import_legacy <dumpdata.json>` (export on old code → rebuild DB → import): pockets→sources, transfers dropped, owner=created_by, password hashes preserved. See DEPLOY.md "May 2026 ledger revamp (data migration)".
- **Load-bearing** — the `balance.html` eye-toggle + `.chart-mask` curtain now wrap the **net-worth** figure/chart (key `pocket-balance-vis:dashboard:networth`); `current_balance` must filter `occurred_on >= starting_balance_as_of`; the net-worth trend is empty until `snapshot_balances` has run at least once.

The sections below are the original build history, kept for the motion/visual rationale.

## What got built (chronological)

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
| 3 | Total Balance showing `Rp 454.750.000` (12 future salaries inflating it) instead of realised `Rp 4.750.000` | `balance_for(as_of=None)` defaults to all-time as of Pass 6. Past-only filtering came back in Pass 8 for installment plans, but applied at the view layer (Dashboard latest list, Transactions index) rather than baked into `balance_for`. The card-level cycle math (`card_cycle.outstanding`) clips at today via `balance_for(card, as_of=today)` so future installments don't inflate "owed now". |
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

### Pass 7 — Reports + Pocket detail revamp

Two surfaces redesigned:

1. **Reports** (`apps/reports/`):
   - Added `last_7`, `last_14`, `last_30` to `PERIOD_CHOICES` alongside the existing options. Default period changed to `last_7` so `/reports/` opens with the most recent week.
   - Added a **Category** filter to the form. Applies to Income vs Expense and Top transactions; the Spending-by-category donut suppresses itself when a single category is selected (its breakdown would be redundant).
   - Refactored `pocket_balances_over_time` to emit a **single combined area series** instead of one per pocket (capped at 6). Default series name `"Overall"`; pick a specific pocket to narrow it (renamed to `<name>` or `<name> (downstream)` when sub-pockets are included). Boundary-crossing transfer math means intra-scope transfers cancel cleanly. Panel renamed "Balance over time".

2. **Pocket detail** (`/pockets/<id>/`): new card panel between Sub-pockets and Recent activity holds two charts — a downstream balance area chart with the eye-curtain (per-pocket localStorage key `pocket-balance-vis:detail:<uuid>:balance`) and a category-spending donut. Quick filter chips `7d / 14d / 30d` (default 30) HTMX-swap only the panel. Scope is `descendant_ids_with_self()` to mirror the Downstream total card. Empty states explain "no activity in the last N days".

### Pass 8 — Credit-card support + installment plans

Two related features that ship together because the cycle math is the same primitive:

1. **Credit-card pockets** (`Pocket.kind`):
   - New fields on `Pocket`: `kind` (`"cash"` | `"credit"`, default cash), `statement_day` (1–28), `due_day` (1–28). CheckConstraints enforce credit-only fields, Main is always cash, and day ranges. Migration `pockets.0003_credit_cards`.
   - New `apps.pockets.services.card_cycle(card)` returns a `CardCycle(outstanding, committed, cycle_spend, pending_bill, due_on, days_until_due)` snapshot. `outstanding` is **clipped at today** (`balance_for(card, as_of=today)`) so future-dated rows don't inflate "owed now". `committed` is the sum of future-dated expenses (relevant once installments exist).
   - **Pockets list** keeps cash pockets in the existing tree and renders credit cards in a separate flat **Cards** section (`templates/pockets/_card_row.html`). Each card row shows owed (terracotta), `Cycle Rp X · Committed Rp Y · Bill Rp Z due in Wd`, and a Pay button (deep-links to `/transfers/new/?to=<card>&amount=<bill>`) when there's a closed bill.
   - **Pocket detail page** for a credit card switches to a 4-figure layout (Outstanding / This cycle / Bill due / Committed; mobile collapses to 2×2), hides Sub-pockets, and adds a primary Pay-bill button. An "Active installment plans" panel lists each plan with `M of N paid · Rp X /mo · next due <date>` plus the total.
   - **Dashboard** headline splits into **Cash / Owed / Net** (each with its own eye-curtain key) when the user has at least one card; otherwise it stays single-figure Total balance.
   - **Repayment** reuses the existing Transfer flow; `transfer_new` view now reads `?to=` and `?amount=` GET params for pre-fill (mirrors the existing `?from=`).

2. **Installment plans (cicilan)**:
   - New nullable Transaction fields: `installment_group` (UUID), `installment_index` (1..N), `installment_total` (N). CheckConstraint `txn_installment_consistent` enforces that all three are NULL or all set with `installment_total` between 2 and 36. Migration `transactions.0004_installments`.
   - When entering a credit-card expense, the New expense form reveals an optional **Installments** select (Single / 3 / 6 / 12 / 24 months). Saving with months > 1 materialises N expense Transactions on the card sharing one `installment_group` UUID, monthly amounts (last child eats the remainder so children sum exactly to the entered total), with `occurred_on` = purchase day shifted forward k−1 months and clamped to month-end via `apps.pockets.services._clamp_day_to_month`. Editing an existing installment child treats it as a regular Transaction (no installment selector).
   - **Past-only-by-default filter restored** for surfaces that read as "what has happened" (Dashboard latest list, Dashboard monthly aggregates, Transactions index). The Transactions filter form's `show_planned` checkbox opts back into seeing future-dated rows, which render with italics + a "Planned" chip + a "Cicilan k/N" chip via `templates/transactions/_list.html`. Reports surfaces are unaffected (period-bounded already).

### Pass 9 — Polish bug-fixes from real-device usage

- **`occurred_on` not pre-filling on edit forms**: Django's `DateInput` widget defaults to the locale format (id-id → `"09-05-2026"`), but `<input type="date">` only accepts ISO `YYYY-MM-DD` and silently leaves the field empty otherwise. Pinned `format="%Y-%m-%d"` on `TransactionForm` and `TransferForm`'s `occurred_on` widgets.
- **Cash / Owed / Net dashboard card overflowing on mobile**: `grid-cols-3` always-on forced 9-digit IDR amounts plus eye-toggle buttons into ~110px each. Switched to `grid-cols-1 sm:grid-cols-3` — on mobile each row is `[label]·····[amount]` baseline-aligned; at `sm:` and up it returns to the stacked 3-up. Mobile font dropped from text-xl to text-lg.
- **Add expense form Alpine error mentioning `Math.floor`**: The `pocketKind` getter embedded `\"` inside a double-quoted `x-data` attribute. HTML doesn't recognise `\"` as escape — the parser treated `"` as the attribute terminator and the rest of the JS became malformed HTML. Moved the data factory into a `<script>` tag before the form and used Alpine's `init()` lifecycle to attach a change listener on the pocket select.
- **Pocket not pre-filling on edit transaction**: Stale `x-model="pocketId"` on the pocket widget from an earlier Alpine state shape; `pocketId` no longer existed in the data object after the `txnForm()` refactor, so Alpine bound the select to undefined on mount and wiped the server-rendered `selected`. Removed the stale `x-model`.
- **More page navigation**: added an **All transactions** link above Categories on the Settings/More page.

### Pass 10 — System-wide polish sweep

A flagship-bar polish pass aligning every surface back to DESIGN.md after several feature passes accumulated small drifts. No new patterns introduced — only existing tokens re-applied where they belonged.

- **Reduced-motion completeness** (`static/css/input.css`): replaced the enumerated `:active` reset (four button classes + `.balance button`) with a universal `*:active { transform: none; }` inside the `@media (prefers-reduced-motion: reduce)` block. Every `active:scale-*` in the app now drops its transform for reduced-motion users — pocket rows, card rows, sub-pocket rows, settings nav rows, bottom tabs, sidebar, FAB, chart-curtain eye — without enumerating each. The slide-up→fade-in entrance degradation is unchanged.
- **Credit card row drift** (`templates/pockets/_card_row.html`): the outer `<div>` wrapping the link + Pay button had no hover state (the link itself only carried `active:scale-[.99]`). Added `hover:bg-brand-50/60 transition-[background-color] duration-150 ease-snap` to the wrapper so cards get the same warm linen wash as cash pockets. Also wrapped each rupiah figure in the `Cycle … · Committed … · Bill …` subtitle in `<span class="num">` so digits column-align per the Tabular Currency Rule.
- **Press feedback gaps**: sub-pocket rows on `templates/pockets/detail.html:159` and the four settings nav rows on `templates/settings/profile.html` only had hover washes — no `active:scale-*`. Brought both in line with the standard nav-row pattern (`active:scale-[.99] transition-[transform,background-color] duration-150 ease-snap`).
- **Section-label color discipline**: four `<h2>`/`<h3>` labels coloured `text-income` / `text-expense` were sitting at borderline-AA contrast on cream and consumed semantic-color budget the Off-Palette Two Rule reserves for transaction signals. Neutralised to `text-brand-700`. The amounts and chart series in those panels still carry the sage/terracotta — that's where the semantic budget belongs. Touched: `categories/index.html:21,42`, `reports/_panels.html:88,109`.
- **Shares-inbox Accept button** (`templates/shares/inbox.html:30`): `btn-secondary text-income` stacked semantic colour over the secondary's own `text-brand-800`, fighting both. Accept *is* the primary action on a pending-invite row, so promoted to `btn-primary`. Decline ghost (`btn-ghost text-expense hover:bg-expense/10`) stays — matches the destructive-ghost pattern from the Archive button on `pockets/detail.html:107`.
- **Dashboard empty-state chip-as-prose** (`templates/dashboard.html:119`): `Tap <span class="chip">+</span> to add the first one` misused `.chip` (which is a static descriptor, not inline ornament). Replaced with a small `w-5 h-5 rounded-full bg-brand-700 text-brand-50` pill containing the plus icon — visually rhymes with the actual FAB the user is being asked to tap, without claiming chip semantics.

What was inventoried and **intentionally not touched**:

- `--ease-glide` token defined in `input.css` but unreferenced in any template. Kept as a documented on-screen-movement token even though no current surface uses it; removing it now would force a re-add the next time we add a draggable or retargeted-transition element.
- Em dashes in template copy. The shared impeccable design law bans them; the user's DESIGN.md and PRODUCT.md voice uses them deliberately. User instructions take precedence.
- `templates/500.html` inline brand hex. The page must render when the static CSS pipeline isn't available, so inline hex is the right call.
- Reports `show_planned` checkbox raw styling. Component-ising as a `.checkbox` token is a separate scope.
- Transaction-row tap-to-edit affordance. Rows are intentionally informational with a small "Edit" link in the corner; making the whole row navigable is a UX decision, not polish.

## What's deferred (still not built)

- **CSV import / export.** Useful for migrating existing spreadsheet data; not blocking.
- **Soft-delete restore UI for pockets.** The model supports archive + unarchive (the `archive`/`unarchive` views exist), but there's no list of archived pockets to restore from. Today, restoring requires the Django shell.
- **Multi-currency.** Out of scope by design — IDR-only is a deliberate constraint.
- **Bulk installment-plan operations.** Today each installment is a regular Transaction, edited or deleted individually. "Cancel the whole plan" and "refinance / change months" are deferred. Probably v2: a button on the card-detail Active-plans panel.
- **Non-zero interest installments.** v1 assumes 0% (Indonesian merchant cicilan default). If the user ever uses a paid-installment plan, the children would still be correct expense rows but the "total = months × monthly" assumption would understate the true cost.
- **Notification system / email digests.** Not on the roadmap.
- **Tests.** No automated tests yet. The verification flow in README.md is manual.

## Load-bearing details (don't refactor without preserving these)

1. **Eye toggle / chart-mask system.** `templates/partials/balance.html` keeps its Alpine state inlined (not registered via `Alpine.data()`) after a stale-cache incident on iOS Safari. The `.chart-mask` sister system in `static/css/input.css` and the `pocket-balance-vis:` localStorage namespace are the same primitive. Documented in CLAUDE.md.

2. **`<input type="date">` requires ISO format.** Both `TransactionForm` and `TransferForm` pin `format="%Y-%m-%d"` on the `occurred_on` widget. Do not remove — `LANGUAGE_CODE = "id-id"` would otherwise default to `dd-mm-yyyy` and silently break the edit-form pre-fill.

3. **`card_cycle.outstanding` clips at today.** `apps.pockets.services.card_cycle()` calls `balance_for(card, as_of=today)` so future-dated installment rows don't inflate "owed now". The `committed` figure is the sum of future-dated expense Transactions. If you ever change `card_cycle()`, preserve this split — it's the only thing keeping installment plans honest.

4. **Past-only-by-default on history surfaces.** Once installment plans exist, future-dated `Transaction` rows live in the DB. The Dashboard latest list, Dashboard monthly aggregates, and the default Transactions list filter `occurred_on__lte=today`. The `show_planned` checkbox on the Transactions filter form opts back into seeing future entries (rendered with italics + a Planned chip + a Cicilan k/N chip). Reports surfaces keep period-bounded semantics — no clip needed.

5. **Installment integrity.** `Transaction` rows in a plan share an `installment_group` UUID; `installment_index` is 1..N and `installment_total` is N. The CheckConstraint `txn_installment_consistent` enforces all-NULL-or-all-set. Per-installment amounts use integer division with the **last child eating any remainder** so the children sum exactly to the entered total. Editing an existing installment child treats it as a normal Transaction; bulk plan operations (cancel-all, refinance) are deferred.

6. **UUID primary keys + `_state.adding`.** Every domain model has a UUID PK with `default=uuid.uuid4`, which means `instance.pk` is **truthy** even on unsaved new instances. To distinguish new vs edit in form code, use `self.instance._state.adding` (True for new). Don't gate edit-form behavior on `self.instance.pk` — it'll always look like an edit.

7. **Alpine `x-data` is inside an HTML attribute.** Don't put `\"` inside a double-quoted `x-data="..."` block — HTML doesn't honor backslash escapes inside attributes and will truncate at the first unescaped `"`. For complex Alpine state, define a function in a `<script>` tag and reference it as `x-data="myFn()"`.

8. **Motion conventions.** Easing tokens (`--ease-snap`, `--ease-glide`) and the focus-visible/focus split are documented in CLAUDE.md. Don't introduce one-off cubic-beziers; extend the token set.

9. **No Django admin.** The default `django.contrib.admin` is intentionally absent from `INSTALLED_APPS`. All operations are CLI commands or custom pages. Don't add the admin back without thinking through the design implications.

10. **No public registration.** Accounts are seeded via `python manage.py createuser` and gated by the auth middleware. There is no `/register` route — by design.

## Operational notes

- **Backups**: not yet configured. The droplet has DigitalOcean's snapshot facility, but Pocket-specific Postgres dumps aren't running on a schedule. Before relying on this for real money, set up a daily `pg_dump pocket` cron and copy off-droplet (e.g., to Backblaze or to a Tailscale-reachable NAS).
- **Migrations**: every new schema change should ship behind a migration.
- **Static asset cache busting**: `STATIC_VERSION` in `/etc/pocket.env` is a unix timestamp the templates append to `output.css` and `app.js`. Bump it after a CSS / JS deploy and `systemctl restart pocket`.
- **Cloudflare SSL mode**: must stay on **Full** (not Full Strict). Origin uses snakeoil; Full Strict would refuse the connection.
- **Logs**: `journalctl -u pocket` is the gunicorn log (access + error). Nginx access goes to `/var/log/nginx/access.log` (all vhosts mixed; grep for `pocket.ionyx.org`).

## Operational health to watch

- Whether real users hit any overflow / truncation regressions on devices we didn't test (iPhone SE 320px is the floor we tested at; older Android phones may render differently).
- Postgres connection count — `sudo -u postgres psql -c 'SELECT count(*) FROM pg_stat_activity'` periodically, since other services on the droplet share the same Postgres instance.
- Memory pressure — droplet is 1 GB; `free -h` and `journalctl -u pocket | grep -i 'memory\|killed'`. If gunicorn workers OOM, drop `--workers 2` to `--workers 1` in `/etc/systemd/system/pocket.service`.
- Cloudflare Analytics → check for unexpected traffic. Pocket has 2 known users; anything else is a probe and should be quiet.

## What I'd do next

If picking this up, in order of leverage:
1. **Backups.** Daily `pg_dump pocket | xz` to off-droplet storage. Single most important missing piece.
2. **Bulk installment-plan operations.** A "Cancel plan" button on the Active plans panel that deletes future-dated children but keeps the past actuals (a one-line ORM call); plus a "Refinance" affordance that re-materialises remaining months. Small, high-utility surface.
3. **Archive-restore UI for pockets.** Closes the "model supports it but no view" loop; small surface.
4. **CSV import.** Lets the user migrate any pre-existing spreadsheet data.
5. **Tests.** No automated tests yet. First targets for `pytest`: the `balance_for` / `card_cycle` semantics, the installment materialiser's date math (especially month-end clamping for plans starting on the 31st), and the period-filter logic in `apps/reports/services.py`.
