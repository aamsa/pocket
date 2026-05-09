# Product

## Register

product

## Users

A household of two — the owner and his wife. Indonesian, IDR-only. Primary surface is a phone held in one hand on a couch or in bed; secondary surface is a desktop browser at home. There are no other users, no acquisition funnel, no anonymous traffic. Auth is invite-only and bootstrapped via CLI.

The job they're trying to do: answer two recurring questions without friction — *"what's in BCA right now?"* and *"how much did we spend on groceries this month?"* — and log income, expenses, and transfers as they happen, with a few taps. Sharing specific wallets between accounts (view or manage) is the second-largest workflow.

## Product Purpose

Pocket is a private, self-hosted personal finance tracker for one household. It exists because the off-the-shelf options either ask too much (acquisition flows, ads, marketing copy, recurring subscriptions) or assume too little (single-user, no permission model for "this account is shared, that one isn't"). Success looks like: both users open the app reflexively to log a transaction, never get confused about whose pocket is whose, and trust the period-filtered reports enough to let go of spreadsheets.

## Brand Personality

Warm, calm, intimate. A money tool that doesn't perform anxiety, urgency, or hype. The interface should feel like a tidy notebook on a wooden desk in afternoon light — present, considered, slightly hand-made. Voice is plain and direct (no marketing tics, no exclamation points, no "Welcome back!"). Currency is rendered in full (`Rp 1.250.000`), never abbreviated to `1.25M`, because the number is the point.

## Anti-references

- **Generic fintech SaaS** (Mint, Personal Capital, most banking dashboards). The hero-metric template, identical icon-and-heading card grids, blue/teal palette, gradient accents. This is the AI-slop default; push against it on every page.
- **Crypto and trading dashboards.** Dark mode + neon accents, Bloomberg-terminal density, animated glow, "ticker" aesthetics. Pocket is domestic, not financialised.
- **Bank-app maximalism.** Marketing carousels, promo banners, upsells, notification dots competing for attention. Pocket is a private tool — there is nothing to sell to its users.
- **Notion / Linear gray-on-white minimalism.** Cool neutrals, square corners, monospace data tables, no warmth. Pocket is *warm*; this would be the wrong over-correction toward "clean."

## Design Principles

1. **Money is private; reveal is deliberate.** Balance figures render as `Rp ••••` until the user taps an eye to reveal. Income/expense aggregates and transaction-row amounts are intentionally exempt — only standing balances need the curtain. This is the central UX primitive; preserve it.
2. **Cohesion over novelty.** The cream-to-mocha brown palette is the personality. Hold the line — sage `#5C8A4E` and terracotta `#9C3D2E` are the only off-palette accents, used only for income/expense. Resist introducing new colors, new card shapes, or new motion vocabularies "just for this one screen."
3. **Two-person scale, not SaaS scale.** No marketing surfaces. No admin UI for end users (superuser uses CLI commands). Empty states should welcome, not upsell. There is no growth funnel to optimise.
4. **Mobile-first, desktop-layered.** Every page is designed at iPhone width first; desktop is the bottom-tabs-become-sidebar enhancement. Touch targets are 44×44 minimum; copy is sized for arm's-length reading.
5. **Quiet motion.** Animation exists for spatial consistency (sheet rises from where the FAB is), state indication (button press scale), and preventing jarring HTMX swaps — never decoration. The motion conventions in CLAUDE.md are load-bearing; new motion should extend the existing easing tokens (`--ease-snap`, `--ease-glide`), not introduce one-off curves.

## Accessibility & Inclusion

WCAG AA target. Body text contrast 4.5:1, large text and UI elements 3:1. Full keyboard navigation with `focus-visible` rings (mouse/touch presses don't leave stuck rings). `prefers-reduced-motion` is respected — transforms on `:active` and movement-based entrances degrade to opacity-only fades; comprehension cues stay intact. Touch targets 44×44 minimum on the bottom tabs, FAB, and form controls. Currency amounts use `font-variant-numeric: tabular-nums` so the eye can compare digits across rows without re-aligning.
