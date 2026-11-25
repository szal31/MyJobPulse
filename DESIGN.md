# MyJobPulse Design Direction

Reading this as: public-policy analytical dashboard for Malaysian economic planners, parliamentarians, and datathon judges, in an editorial civic-ledger style, dial ENERGY 1 / RHYTHM 2 / MOTION 1.

## Dials
- **Dial:** ENERGY 1 / RHYTHM 2 / MOTION 1
- **ENERGY 1 (Calm):** Public-service and statistical-bulletin authority; let official DOSM and Hansard evidence speak without visual hype.
- **RHYTHM 2 (Consistent with deliberate breaks):** Predictable header + KPI strip at the top of each view, followed by varied analytical compositions (paired charts, fan charts, Malaysia choropleth map, scatter plots, priority-ordered state cards, and tabular scoreboards).
- **MOTION 1 (Hover and focus states only):** 150ms ease-out hover/focus transitions on interactive controls and cards; zero entrance animations, zero loops, disabled under `prefers-reduced-motion: reduce`.

## Color System (R-01, R-25, R-29)
- **Neutrals (ground, surface, ink):** `#F8FAFC` page canvas, `#FFFFFF` card/plot surface, `#EEF2F8` secondary rail/table header, `#E2E8F0` hairline grid/borders, `#0F172A` primary ink (17.9:1 on white), `#475569` secondary ink (7.6:1 on white).
- **Core brand hue:** `#1E40AF` deep navy for DOSM actual series, primary emphasis, and interactive links (8.7:1 on white); `#93C5FD` soft sky tint strictly as historical comparison bars alongside navy.
- **Single deliberate accent:** `#B45309` amber text/badges (5.0:1 on white) and `#D97706` amber chart strokes (3.2:1 non-text AA) reserved for forecasts, wage-penalty cost callouts, and key warnings.
- **Functional traffic-light states (semantic only, never decorative):** `#B91C1C` High risk (5.9:1 on `#FEF2F2`), `#B45309` Watch (4.8:1 on `#FFFBEB`), `#15803D` Normal (4.8:1 on `#F0FDF4`). Always paired with text labels and distinct scatter marker shapes (`diamond`, `triangle-up`, `circle`).

## Typography (R-06)
- **Primary sans (`Fira Sans` with offline system-sans fallback):** Clean humanist proportions tuned for dense labels, policy prose (`68ch` max measure), and 100% offline rendering without CDN font requests.
- **Tabular numerals (`Fira Code` with offline system-mono fallback):** Used strictly for numeric KPI values, state rates, and aligned accuracy tables (`font-variant-numeric: tabular-nums`) so digits align vertically across rows and cards; never used for headings or decorative terminal styling.

## Identity Motif & Component Decisions (R-08, R-11, R-12, R-14, R-31)
- **Identity motif:** Clean hairline-divided civic report sections, full 1px semantic borders with gentle surface tints (never one-sided left stripes), and pill status badges that pair color, tint, and text.
- **Border radius:** `10px-12px` for cards/sections, `999px` reserved strictly for compact status pills and section-jump links.
- **Shadow:** Single hairline elevation (`0 1px 2px rgba(15, 23, 42, 0.04)`) on KPI cards to separate them lightly from the `#F8FAFC` canvas; tables and callouts sit flat.
- **Icons:** Used only where a domain glyph clarifies page purpose on Home navigation (`show_chart`, `map`, `tune`, `account_balance`, `checklist`, `description`); no repeated default forward arrows.
- **Light mode fixed (R-21):** Analytical policy briefs and printable A4 PDFs are read in bright meeting rooms and printed on white paper; light mode guarantees parity between the live app and `Dashboard.pdf`.
