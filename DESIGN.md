# DESIGN.md — Anansi Atlas

> This file tells AI agents how to generate UI that matches the Anansi Atlas visual system.
> Keep it updated whenever the design language changes.

---

## Identity

**Product:** Anansi Atlas — "The Web of Opportunity"
**Audience:** Nonprofit executive directors, development leads, grant managers
**Personality:** Authoritative, warm, precision-focused. Not corporate-cold; not playful-casual. Think strategic advisor who also has great taste.
**Visual metaphor:** Spider web — interconnected nodes, radiating paths, organic geometry over rigid grids.

---

## Color Palette

### Core tokens

| Token | Hex | Role |
|---|---|---|
| `--night` | `#07101d` | Deepest background (hero headers, overlays) |
| `--navy` | `#0d1b3d` | Primary dark surface, section numbers, nav |
| `--deep` | `#0d1628` | Header gradient end |
| `--ink` | `#0e1e35` | Body text, labels |
| `--muted` | `#5e6d85` | Secondary text, hints, optional labels |
| `--line` | `#dce5eb` | Borders, dividers |
| `--page` | `#f7f3eb` | Warm cream — default page background |
| `--white` | `#ffffff` | Card surfaces |
| `--gold` | `#d4a017` | Primary CTA, accent, brand mark gradient start |
| `--gold-lt` | `#e5ad3f` | Hover state gold, eyebrow text on dark |
| `--gold-soft` | `#fff6dd` | Gold tint backgrounds |
| `--gold-dark` | `#8a5b00` | Gold text on light backgrounds |
| `--rose` | `#c46a3d` | Secondary accent, required field markers, alert |
| `--rose-soft` | `#fdf0e8` | Rose tint backgrounds |
| `--blue` | `#1a3460` | Brand navy (links, info states) |
| `--blue-soft` | `#eaeef7` | Blue tint backgrounds |

### Usage rules
- **Never** use pure black (`#000`) or pure white on colored backgrounds — always use token values
- Page background is always `--page` (warm cream), never white
- Cards sit on `--white` against `--page` to create layering depth
- Dark sections use `--night` → `--deep` gradient at `160deg`
- Gold is the **only** CTA color — never use blue or green buttons
- Required field asterisks and validation errors use `--rose`

---

## Typography

**Font stack:** `Inter, ui-sans-serif, system-ui, -apple-system, sans-serif`

### Scale

| Usage | Size | Weight | Notes |
|---|---|---|---|
| Hero headline | `clamp(2.2rem, 5vw, 3.8rem)` | 950 | Letter-spacing `-0.04em`, line-height `0.95` |
| Section title | `clamp(1.4rem, 3vw, 2rem)` | 900 | Letter-spacing `-0.03em` |
| Card heading | `1.1rem` | 800 | |
| Label / eyebrow | `0.68–0.78rem` | 900 | Letter-spacing `0.1–0.16em`, ALL CAPS |
| Body | `0.94–1rem` | 400 | Line-height `1.55` |
| Caption / hint | `0.78–0.82rem` | 400–600 | Color `--muted` |
| Button | `0.9–1rem` | 900 | |

### Rules
- Headlines on dark: `#ffffff`
- Headlines on light: `--ink`
- Eyebrow labels on dark: `--gold-lt`
- Eyebrow labels on light: `--muted` (uppercase, tracked)
- Never justify text; left-align everything
- No underlines on nav links — use color and weight to signal interactivity

---

## Spacing & Layout

- Max content width: `1200px` (dashboard), `760px` (forms/intake)
- Base unit: `4px` — use multiples: `8, 12, 16, 20, 24, 28, 32, 40, 48, 64`
- Section padding: `48–64px` vertical on landing, `28–32px` on app pages
- Cards: `24–28px` internal padding
- Grid: CSS Grid preferred over flexbox for 2+ column layouts

---

## Border Radius

| Token | Value | Used for |
|---|---|---|
| `--radius` | `14px` | Inputs, small cards, chips |
| `--radius-lg` | `22px` | Section cards, modals |
| `--radius-pill` | `999px` | Buttons, tags, badges |

---

## Shadows

```css
--shadow-sm: 0 1px 3px rgba(13,27,61,.06), 0 4px 12px rgba(13,27,61,.06);
--shadow:    0 1px 3px rgba(13,27,61,.06), 0 16px 40px rgba(13,27,61,.08);
--shadow-lg: 0 4px 6px rgba(13,27,61,.06), 0 24px 60px rgba(13,27,61,.12);
```

- Cards use `--shadow` by default
- Elevated/hover states use `--shadow-lg`
- Never use `box-shadow: none` to remove focus rings — replace with gold ring instead

---

## Components

### Buttons

```css
/* Primary (gold CTA) */
background: var(--gold);
color: var(--navy);
border-radius: 999px;
font-weight: 900;
padding: 13px 28px;
box-shadow: 0 8px 24px rgba(212,160,23,.28);

/* Hover */
transform: translateY(-1px);
box-shadow: 0 14px 32px rgba(212,160,23,.36);

/* Ghost */
background: transparent;
border: 1.5px solid rgba(255,255,255,.25);
color: #fff;
border-radius: 999px;
```

**Rules:** Never rounded-rectangle buttons — always pill (`999px`). Gold is the only filled CTA color.

### Cards / Panels

```css
background: var(--white);
border: 1px solid var(--line);
border-radius: var(--radius-lg);
box-shadow: var(--shadow);
padding: 28px;
```

No accordion/`<details>` elements — all sections are always visible.

### Form inputs

```css
border: 1.5px solid #cdd6df;
border-radius: var(--radius);
padding: 10px 13px;
background: #fafaf8;
font-size: 0.92rem;

/* Focus */
border-color: var(--gold);
box-shadow: 0 0 0 3px rgba(212,160,23,.18);
background: #fff;
```

### Section headers (numbered)

```html
<div class="section-label">
  <span class="section-num">1</span>   <!-- navy circle, white number -->
  <span class="section-name">LABEL</span>   <!-- muted, uppercase, tracked -->
  <span class="section-note">All fields required</span>   <!-- rose, right-aligned -->
</div>
```

### Brand mark

```html
<!-- Small (32×32px) -->
<span class="brand-mark"></span>
<!-- Gold→rose gradient, border-radius: 10px, inner circle ring via ::after -->
background: linear-gradient(135deg, #e5ad3f, #c96d3c);
```

### Eyebrow / section label pattern (dark background)

```html
<p class="eyebrow">ORGANIZATION SETUP</p>
<!-- font-size: .68rem; font-weight: 900; letter-spacing: .16em; color: var(--gold-lt) -->
```

---

## Dark Header Pattern

Used on hero sections and page headers:

```css
background: linear-gradient(160deg, #07101d 0%, #0d1628 60%, #12213a 100%);
color: #fff;
```

Eyebrow: `--gold-lt`, subtitle: `#c5d1e8`, headline: `#fff`

---

## Sidebar / App Shell

- Sidebar width: `220px`, background `--night`, text `rgba(255,255,255,.75)`
- Active nav item: gold left-border (`3px solid var(--gold)`), background `rgba(212,160,23,.08)`, text `#fff`
- Section dividers in sidebar: `rgba(255,255,255,.06)`
- Getting Started checklist renders at sidebar bottom until all steps complete

---

## Data Visualization

- Chart accent color: `--gold` primary, `--rose` secondary, `--blue` tertiary
- Spider/radar charts use gold stroke with `rgba(212,160,23,.15)` fill
- Score badges: gold on `--gold-soft` background, navy text
- Progress bars: gold fill on `rgba(255,255,255,.06)` track on dark, or `--line` track on light

---

## Anti-patterns (never do)

- No `<details>` / `<summary>` accordions — everything is always visible
- No pure black or pure white backgrounds
- No teal, green, or purple — only the palette tokens above
- No multi-line comment blocks in generated code
- No rounded-rectangle buttons — pills only
- No centered body text in long-form content
- No generic loading spinners — use skeleton states where needed

---

## Voice & Copy

- Headlines: declarative, present tense ("Your Opportunity Web is ready.")
- CTAs: action-first ("Build my Opportunity Web →", "View your Snapshot")
- Labels: noun phrases, not questions ("Mission Statement", not "What is your mission?")
- Empty states: encouraging, specific ("No funders matched yet — add more program detail to improve alignment.")
- Error messages: plain language, actionable ("City is required." not "This field cannot be blank.")
