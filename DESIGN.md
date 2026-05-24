---
name: Pocket
description: Mindful money for two — a private, mobile-first finance web app.
colors:
  buttercream:    "#FFEDD8"
  linen:          "#F3D5B5"
  sand:           "#E7BC91"
  caramel:        "#D4A276"
  hazelnut:       "#BC8A5F"
  tobacco:        "#A47148"
  coffee:         "#8B5E34"
  cocoa:          "#6F4518"
  espresso:       "#603808"
  walnut:         "#583101"
  mossbank:       "#5C8A4E"
  terracotta:     "#9C3D2E"
  surface:        "#FFEDD8"
  card-surface:   "#FFFFFF"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "normal"
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
    fontFeature: "'ss01', 'cv11'"
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "0.06em"
  numeric:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "normal"
    fontVariation: "tabular-nums"
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  2xl: "32px"
components:
  btn-primary:
    backgroundColor: "{colors.cocoa}"
    textColor: "{colors.buttercream}"
    rounded: "{rounded.xl}"
    padding: "12px 20px"
  btn-primary-hover:
    backgroundColor: "{colors.espresso}"
    textColor: "{colors.buttercream}"
    rounded: "{rounded.xl}"
    padding: "12px 20px"
  btn-secondary:
    backgroundColor: "{colors.linen}"
    textColor: "{colors.espresso}"
    rounded: "{rounded.xl}"
    padding: "12px 20px"
  btn-secondary-hover:
    backgroundColor: "{colors.sand}"
    textColor: "{colors.espresso}"
    rounded: "{rounded.xl}"
    padding: "12px 20px"
  btn-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.cocoa}"
    rounded: "{rounded.xl}"
    padding: "8px 16px"
  btn-ghost-hover:
    backgroundColor: "{colors.linen}"
    textColor: "{colors.cocoa}"
    rounded: "{rounded.xl}"
    padding: "8px 16px"
  input:
    backgroundColor: "{colors.buttercream}"
    textColor: "{colors.walnut}"
    rounded: "{rounded.md}"
    padding: "12px 16px"
  card:
    backgroundColor: "{colors.card-surface}"
    textColor: "{colors.walnut}"
    rounded: "{rounded.lg}"
    padding: "16px"
  chip:
    backgroundColor: "{colors.linen}"
    textColor: "{colors.espresso}"
    rounded: "{rounded.xl}"
    padding: "4px 10px"
---

# Design System: Pocket

## 1. Overview

**Creative North Star: "The Household Ledger"**

Pocket is a domestic record-keeping tool for two people, not a SaaS finance product. The system reads as a tidy notebook on a wooden desk in afternoon light: warm, present, considered. Every detail leans toward intimacy and patience — the curtain over balances by default, the unabbreviated `Rp 1.250.000`, the cream-to-mocha ramp pulled directly from a domestic palette study. The two-person scale matters: there are no marketing surfaces, no upsells, no growth metrics to optimise against. The interface earns trust by behaving consistently and saying only what needs saying.

This system is forcefully anti-SaaS-fintech. It explicitly rejects the hero-metric template, the icon-and-heading card grid, the blue/teal banking palette, gradient accents, and animated glow. It also rejects the cool-grey Notion/Linear minimalism that "clean" fintech often defaults to — the warmth of the brown ramp is the point, not a stylistic risk to hedge against. Crypto and Bloomberg-terminal density are not even adjacent to the brief.

**Key Characteristics:**
- One palette, held everywhere — cream-to-mocha browns, with sage and terracotta as the only off-palette accents (income / expense respectively).
- Standing balances are private by default; reveal is a deliberate per-balance gesture that persists in `localStorage`.
- Mobile-first geometry: bottom-tab nav and a center FAB on mobile, sidebar replaces tabs on desktop.
- Numbers are tabular and unabbreviated. `Rp 1.250.000`, not `1.25M`.
- Motion is quiet — `--ease-snap` for UI, `--ease-glide` for on-screen movement, `cubic-bezier(0.32, 0.72, 0, 1)` only for the FAB sheet. No bounce, no elastic.
- Surfaces are flat by default. Two purposeful elevations only: the resting card lift and the floating-object pop.

## 2. Colors: The Ledger Palette

A single warm-brown ramp anchors everything; sage and terracotta carry semantic income/expense duty and never appear elsewhere. Neutrals are tinted toward the brand hue — there is no pure grey and no pure black anywhere in the system.

### Primary
- **Cocoa** (`#6F4518`): Primary action surface. The colour of every `btn-primary`, the brand mark, the active sidebar text, the FAB. The most-pressed surface.
- **Espresso** (`#603808`): Pressed/hover state of primary; deep ledger-ink text on cream backgrounds when extra emphasis is needed.

### Secondary
- **Linen** (`#F3D5B5`): Soft secondary surface — `btn-secondary` background, hover wash on rows, chip background, scrim under the FAB sheet's safe-area.
- **Sand** (`#E7BC91`): Active hover state of secondary buttons; quiet structural divides that need slightly more presence than `linen`.

### Tertiary
- **Mossbank** (`#5C8A4E`): Income only. Sage green carries the *added* signal — incoming transactions, success messages, the up-arrow icon. Never used decoratively.
- **Terracotta** (`#9C3D2E`): Expense only. Carries the *removed* signal — outgoing transactions, error messages, validation. Never used decoratively.

### Neutral
- **Buttercream** (`#FFEDD8`): App-wide page surface. Replaces white. Body backdrop, input fill, FAB ring.
- **Walnut** (`#583101`): Default text colour. Replaces black; same visual role, warmer tone.
- **Linen / Sand / Caramel / Hazelnut / Tobacco / Coffee** form the in-between ramp for borders, dividers, hover washes, hierarchy in muted text. `Coffee` (brand-600) is the **lightest text colour permitted on cream for body prose** — it clears 5.6:1 against `buttercream`. `Tobacco` (brand-500) sits at ~4.0:1 and is reserved for large/heavy text or UI components only. `Hazelnut` and above carry decorative/structural duty (chevron icons, illustration hairlines) and never carry running text.

### Named Rules

**The Off-Palette Two Rule.** Sage `#5C8A4E` and terracotta `#9C3D2E` are the *only* colours outside the brown ramp that appear in the product. They are reserved exclusively for the income/expense semantics. Don't borrow them for accents, branding flourishes, or "active state" visual effects. The system's coherence depends on this rule being unbroken.

**The No-Pure-Black, No-Pure-White Rule.** Body text is `walnut`, never `#000`. Page surface is `buttercream`, never `#fff`. Card surfaces use literal white only because the contrast against `buttercream` is what defines a card — and the card border immediately tints it back toward warm. Anywhere a value reads as "neutral grey," it should be tinted toward the brand hue.

## 3. Typography

**Display Font:** Inter (with `ui-sans-serif`, `system-ui`, sans-serif fallbacks)
**Body Font:** Inter (same family — single-stack)
**Numeric Treatment:** Inter with `font-variant-numeric: tabular-nums`

**Character:** Inter is the chosen single voice — calm, modern, warm enough at 600 weight to sit on the cream surface without feeling clinical. Stylistic sets `ss01` and `cv11` are enabled globally to soften the `1` and the `a` toward a more humanist feel. The system does not use a serif or a mono; the warmth comes from the palette, not the type.

### Hierarchy
- **Display** (600 / `1.875rem` / 1.15 / `-0.02em`): Page-title H1 on top-level routes (Dashboard, Pockets, Reports). Negative tracking pulls the form together at scale.
- **Headline** (600 / `1.5rem` / 1.2 / `-0.015em`): Mobile-width page H1. Slightly tighter than Display because phone screens compress hierarchy.
- **Title** (600 / `1rem` / 1.4): Card titles, section labels above lists.
- **Body** (400 / `0.875rem` / 1.5): All running text, transaction descriptions, form labels-as-prose. Capped at ~70ch in long-form.
- **Label** (500 / `0.75rem` / 1.3 / `+0.06em` / uppercase): Micro-labels — "INCOME", "DOWNSTREAM", section dividers. Sparingly applied; over-use erodes the warm voice.
- **Numeric** (600 / tabular-nums): Every currency figure, balance, transaction amount. Tabular nums are non-negotiable — vertical alignment of digits across rows is what makes the ledger legible.

### Named Rules

**The Tabular Currency Rule.** Every IDR figure renders through the `rupiah` template filter and inherits `font-variant-numeric: tabular-nums` (the `.num` utility). Bare amounts without `.num` are forbidden — digits must align vertically across rows so the eye can scan a column without re-anchoring.

**The Single-Voice Rule.** Inter is the only typeface in the product. No serif H1 for "editorial flair," no mono for "data feel." The warmth budget is spent on colour and motion, not type.

## 4. Elevation

Pocket is **flat by default** with two purposeful lifts. Most surfaces — list rows, form sections, dropdown items, the active period filter — sit at zero elevation and are separated by tinted borders (`linen` or `sand`) or background washes. Shadow signals "I am a floating object," not "I am important."

### Shadow Vocabulary
- **`--shadow-card`** (`0 1px 2px 0 rgb(88 49 1 / 0.04), 0 1px 3px 0 rgb(88 49 1 / 0.08)`): The resting elevation of every `card`. Tinted toward `walnut`, never neutral grey. Whisper-level — makes the card feel like a slip of paper on the desk, not a UI panel hovering above it.
- **`--shadow-pop`** (`0 8px 24px -6px rgb(88 49 1 / 0.18)`): Reserved for genuinely floating objects: the FAB, the rising bottom sheet, the login-page brand mark. Used precisely twice in the product and shouldn't grow.

### Named Rules

**The Two-Shadow Rule.** Only `--shadow-card` and `--shadow-pop` exist. New shadows are forbidden. If you reach for a third elevation, the answer is almost always a tinted background or border, not another shadow token. Drop-downs, modals, popovers, and dialogs use `--shadow-card`.

**The Tinted-Shadow Rule.** Every shadow uses `rgb(88 49 1 / α)` (i.e. tinted toward `walnut`). Pure-black shadows are forbidden — they read cold and break the warm cohesion the palette establishes.

## 5. Components

Components are deliberately rounded — `rounded-full` for pressables, `rounded-2xl` for surfaces — and sit on the cream page with whisper-shadow, never sharp edges or hard outlines.

### Buttons
- **Shape:** Pill / fully rounded (`9999px`). Buttons are oblong because the action is the signal, not the shape.
- **Primary:** `cocoa` background, `buttercream` text, `12px 20px` padding, `--shadow-card` resting. Hover deepens to `espresso`. Press scales to `0.98` over 160ms with `--ease-snap`. `focus-visible:ring-2 ring-cocoa-300/50` only — focus rings never persist after a click.
- **Secondary:** `linen` background, `espresso` text, identical padding and shape. Hover deepens to `sand`. Same press behaviour.
- **Ghost:** Transparent background, `cocoa` text, `8px 16px` padding (smaller). Hover wash is `linen` at 80% alpha. Same press scale.
- **Press feedback is mandatory.** All three variants scale to `0.98` on `:active`. The FAB scales to `0.95` because it's the single most pressed control on mobile.

### Chips
- **Style:** `linen` background, `espresso` text, `4px 10px` padding, fully rounded. No border, no shadow.
- **State:** Static — chips in this product are descriptors ("Manage", "Default", "Main"), not filters. If a filter chip is ever introduced, the selected state should be `cocoa`/`buttercream`, never an outline.

### Cards / Containers
- **Corner Style:** `rounded-2xl` (16px). Generous, never sharp.
- **Background:** White (`#FFFFFF`) — the *only* place in the product where literal white appears. The contrast against `buttercream` is what makes a card read as a card.
- **Shadow Strategy:** `--shadow-card` resting; never `--shadow-pop`. (See Elevation.)
- **Border:** `1px solid linen` — the warm tint pulls the white surface back toward the palette so it doesn't read clinical.
- **Internal Padding:** `16–24px` typical. Empty states get more; dense lists less.
- **No nested cards.** Ever.

### Inputs / Fields
- **Style:** `buttercream` fill (matches page surface), `1px solid sand` border, `rounded-xl` (12px). Padding `12px 16px`.
- **Focus:** Border shifts to `tobacco`, ring `2px cocoa/40%` adds outside the border. `focus:` (not `focus-visible:`) — form fields legitimately need a ring on click so the user knows where typing will go.
- **Error:** Border shifts to `terracotta` at 20% alpha, background washes to `terracotta/10`. Error message in `terracotta` directly under the field.
- **Disabled:** Opacity 0.6, no visual border change otherwise.

### Navigation
- **Sidebar (desktop):** `200px` fixed, sticky below the app bar. Active item: `sand/70%` background, `walnut` text. Inactive: `cocoa` text, no background, hover wash `linen/70%`. No transition on the active-state colour flip — nav is a hot path; instant feedback is correct.
- **Bottom tabs (mobile):** `md:hidden`, fixed bottom, `buttercream/95` with backdrop-blur, top border `linen`. Five-column grid. Active item: `walnut` text. Inactive: `tobacco` text. Press feedback is `scale(.96)` over 100ms. No colour transition (frequent action).
- **App bar:** Sticky top, `buttercream/85` with backdrop-blur, `linen` bottom border. 56px on mobile, 64px desktop.

### Balance Eye Toggle (signature component) — REMOVED May 2026

> Removed with the net-worth feature — no standing balances remain to hide. `templates/partials/balance.html`, the `.chart-mask` curtain, and the `pocket-balance-vis:` localStorage namespace are gone. Kept below as historical design rationale.

Every standing-balance figure rendered inside the `balance.html` partial: `<span class="balance">` wraps the amount + a small eye icon. The wrapper carries `balance-hidden` statically so server HTML shows `Rp ••••` immediately — no JS-required reveal. Alpine reads `localStorage` on init and removes the class only if the user has previously revealed this exact key. The toggle button has `active:scale-90` press feedback; its hit target is enlarged with `p-2 -m-2` so taps land comfortably without changing the visible icon size.

This component is load-bearing — the Alpine state is inlined in the partial (not registered via `Alpine.data()`) after a stale-cache incident on iOS Safari. Don't refactor it without preserving that.

The Reports → Pocket balances chart shares the same UX primitive but uses a sister component, `.chart-mask`, defined in `static/css/input.css`. Mirrors the partial's idiom: wrapper carries `chart-hidden` statically, Alpine removes it on reveal, an absolutely-positioned `.chart-overlay` covers the chart with a `Rp ••••` placeholder + backdrop blur. The chart itself always renders into the DOM (so ApexCharts can measure container width); the overlay sits on top with `pointer-events: none` when revealed, full opacity when hidden. localStorage key follows the same `pocket-balance-vis:` namespace.

## 6. Do's and Don'ts

### Do:
- **Do** keep the cream-to-mocha brown ramp as the entire palette. New surfaces use existing shades; new accents do not exist.
- ~~**Do** render every standing balance through `templates/partials/balance.html`.~~ *(Removed May 2026 with net worth — no standing balances remain.)*
- **Do** use tabular-nums (the `.num` utility) on every currency figure so digits column-align across rows.
- **Do** use `--ease-snap` for UI transitions (160ms for state, 200ms for popovers) and `--ease-glide` for on-screen movement. Reach for `--animate-sheet-up`'s iOS-drawer curve only for the FAB sheet.
- **Do** use `focus-visible:` rings on buttons and `focus:` rings on form inputs. Mouse press should not leave a stuck ring; keyboard focus must be visible.
- **Do** add `active:scale-[.98]` (or `.96`/`.99` for nav rows) press feedback to every tappable surface. The product runs on phones; press feedback is non-negotiable.
- **Do** treat `--shadow-card` as the resting elevation. `--shadow-pop` exists only for the FAB and the rising bottom sheet.
- **Do** respect `prefers-reduced-motion` — `:active` transforms drop, slide-up entrances degrade to opacity-only fades. Comprehension cues stay; movement goes.
- **Do** render currency unabbreviated — `Rp 1.250.000`, never `1.25M` or `Rp 1.25jt`.

### Don't:
- **Don't** ship the **generic fintech SaaS** template — hero-metric card, identical icon-and-heading card grid, blue/teal banking palette, gradient accents. This is the single most common AI-slop default and the product is forcefully against it.
- **Don't** ship **crypto/neon dashboards** — dark mode + neon accents, animated glow, Bloomberg-terminal density. Pocket is domestic, not financialised.
- **Don't** drift toward **Notion/Linear gray-on-white minimalism** — cool greys, square corners, monospace data tables. The warmth is the point; dropping it is the wrong correction.
- **Don't** use `#000` or `#fff` directly. `walnut` for text; `buttercream` for page; `card-surface` (white) only inside the `card` component where the contrast is the point.
- **Don't** introduce a third semantic colour. Income is sage, expense is terracotta, everything else is brown. There is no purple "Investments" category or blue "Savings" callout — categories are differentiated by name and icon, not by colour outside the income/expense binary.
- **Don't** use `transition: all` or bare `transition` — specify the exact properties and the easing token. Never animate `width`, `height`, `padding`, or `margin`.
- **Don't** use `ease-in` on UI. It delays the moment the user is watching most. The HTMX swap-in is `--ease-snap`, not `ease-in` — that was the canonical violation we fixed in the motion pass.
- **Don't** add **gradient text** (`background-clip: text` over a gradient), **side-stripe borders** (colored `border-left > 1px` as an accent), or **glassmorphism** (decorative blur). Reach for solid colour, full borders, or nothing.
- *(Obsolete May 2026: the **eye toggle** / balance-hide system was removed with net worth. There are no standing balances; every figure renders plainly.)*
- **Don't** introduce **nested cards**. If a card needs internal grouping, use spacing, dividers, or a label.
- **Don't** use **animated icons, animated emoji, or any decorative motion** — motion serves spatial consistency, state indication, or HTMX swap continuity. Decoration is forbidden.
- **Don't** use the Django **admin UI**. All admin actions are CLI commands or custom pages; the admin styling will violate every rule above.
