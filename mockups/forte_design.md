---
name: Forte
source: https://forte.kz/en/logo (brand book) + bank.forte.kz/en, /en/cards, /en/deposits, business.forte.kz/en/ComForte, premier.forte.kz/en
captured: 2026-10-16 via Playwright (desktop 1440×900, mobile 390×844)
colors:
  primary: "#4A0221"            # Dark Magenta — CTA fill, display type
  primary-deep: "#270111"       # wine ink — chip text, active tab text, card titles on gray
  brand-magenta: "#A31551"      # Forte Magenta — master brand, logo, active nav link
  brand-pink: "#F03785"         # secondary-gradient end
  sky-blue: "#61CFFF"           # Sky Blue — accent surface, slider thumb, active tab underline, footer numbers
  coral: "#FC9385"              # Coral Sunshine — warm accent surface, gradient end
  canvas: "#FFFFFF"
  surface-soft: "#F7F6F6"
  surface-gray: "#EDEDED"       # band + service-card surface
  surface-panel: "#F1F2F3"      # brand-book specimen panel
  hairline: "#D5D5D5"
  hairline-soft: "#EAEBEF"
  ink: "#1D1D1D"
  body-muted: "#6C6C6C"
  slate: "#69758B"
  link: "#185AC5"
  on-primary: "#FFFFFF"
  market-cyan: "#00D0FF"
  market-mustard: "#F0C54F"
  business-navy: "#072146"
  business-medium: "#043263"
  business-light: "#1464A5"
  business-ice: "#EEF5FD"
  premier-green-dark: "#08342A"
  premier-green-medium: "#234E44"
  premier-green-light: "#3A8171"
  premier-gold: "#C9B07E"
  premier-night: "#121A1B"
  premier-nav: "#11151B"
  premier-tile: "#1E2627"
  premier-slate: "#4C5561"
  premier-cta: "#98134B"
  premier-teal: "#1BC1D1"
  finance-grey-dark: "#3C3C3B"
  finance-grey-medium: "#878787"
  finance-grey-light: "#C6C6C6"
  finance-grey-white: "#F6F6F6"
gradients:
  footer: "linear-gradient(210.46deg, #FF6A78 -3.25%, #9B053F 69.11%, #820232 86.64%)"
  forte-primary: "linear-gradient(90deg, #4A0221, #FC9385)"
  forte-secondary: "linear-gradient(90deg, #A31551, #F03785)"
  forte-hero: "linear-gradient(115deg, #4A0221 0%, #B8335F 55%, #FC9385 100%)"
  business-band: "linear-gradient(220.28deg, #1464A5 2.33%, #072146 95.51%)"
typography:
  family: '"Open Sans", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
  premier-family: "Cignika"
  display-lg:  { size: 37px, weight: 700, lineHeight: 1.2,  letterSpacing: -0.1295px }
  display-md:  { size: 32px, weight: 700, lineHeight: 1.5,  letterSpacing: 0 }
  title-lg:    { size: 28px, weight: 600, lineHeight: 1.17, letterSpacing: -0.042px }
  banner-title:{ size: 28px, weight: 500, lineHeight: 1.14, letterSpacing: 0.07px }
  title-md:    { size: 20px, weight: 600, lineHeight: 1.235,letterSpacing: -0.03px }
  value-lg:    { size: 24px, weight: 400, lineHeight: 1.5,  letterSpacing: -0.168px }
  body-md:     { size: 16px, weight: 400, lineHeight: 1.5,  letterSpacing: -0.048px }
  button:      { size: 16px, weight: 400, lineHeight: 1.5,  letterSpacing: 0 }
  tab:         { size: 16px, weight: 500, lineHeight: 1.75, letterSpacing: 0 }
  chip:        { size: 14px, weight: 500, lineHeight: 1.25, letterSpacing: 0 }
  body-sm:     { size: 14px, weight: 400, lineHeight: 1.5,  letterSpacing: 0 }
  caption:     { size: 13px, weight: 400, lineHeight: 1.5,  letterSpacing: -0.0195px }
  eyebrow:     { size: 12px, weight: 600, lineHeight: 1.5,  letterSpacing: 1.8px }
  premier-display: { size: 44px, weight: 700, lineHeight: 1.15, letterSpacing: 0 }
rounded:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  pill: 22px
  full: 50%
  business-card: 20px
  premier-tile: 30px
  premier-card: 40px
spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 40px
  banner-x: 80px
  section: 80px
components:
  button-primary:        { bg: "{colors.primary}", fg: "{colors.on-primary}", type: "{typography.button}", padding: "16px 20px", height: 56px, radius: "{rounded.md}" }
  button-inverse:        { bg: "{colors.canvas}", fg: "{colors.primary}", type: "{typography.button}", weight: 500, padding: "16px 20px", radius: "{rounded.md}" }
  segmented-toggle:      { height: 36px, padding: "8px 12px", radius: "{rounded.lg}", type: "{typography.chip}" }
  segmented-toggle-active:   { bg: "{colors.primary}", fg: "{colors.on-primary}", border: "1px solid transparent" }
  segmented-toggle-inactive: { bg: transparent, fg: "{colors.primary}", border: "1px solid {colors.primary}" }
  filter-chip:           { bg: "{colors.canvas}", fg: "{colors.primary-deep}", border: "1px solid {colors.hairline}", padding: "6px 12px", radius: "{rounded.pill}", type: "{typography.chip}" }
  filter-chip-active:    { bg: "{colors.primary}", fg: "{colors.on-primary}", border: "1px solid {colors.primary}" }
  underline-tab:         { fg: "{colors.slate}", type: "{typography.tab}", underline: "2px {colors.surface-gray}" }
  underline-tab-active:  { fg: "{colors.primary-deep}", underline: "2px {colors.sky-blue}" }
  icon-button-circular:  { size: 40px, bg: "{colors.canvas}", radius: "{rounded.full}" }
  service-card:          { bg: "{colors.surface-gray}", radius: "{rounded.xl}" }
  promo-banner:          { radius: "{rounded.xl}", paddingX: "{spacing.banner-x}", shadow: "rgba(0,0,0,0.1) 0 4px 8px" }
  text-input:            { bg: "{colors.canvas}", border: "1px solid {colors.hairline}", radius: "{rounded.md}", height: 48px, padding: "12px 16px" }
---

## Overview

Forte's web surfaces are a **wine-on-white retail bank with a toy-box voice**. The base atmosphere is white canvas and flat `{colors.surface-gray}` (#EDEDED) bands alternating down the page, near-black body type, and section headlines set heavy (700) in `{colors.primary}` — the very dark magenta, almost aubergine, that also fills every primary button. Nothing is minimal in the Swiss sense: every section is anchored by a glossy **3D illustration** (cards, safes, coins, phones, piggy-tokens) that bursts out of its card's top edge.

The brand voltage comes from three places: (1) the **Forte magenta family** — `{colors.brand-magenta}` (#A31551) for the logo and active nav, `{colors.primary}` (#4A0221) for action and display type; (2) **saturated full-width promo banners** in `{colors.sky-blue}`, `{colors.market-mustard}`, or the navy business gradient that punctuate the scroll every one or two screens; and (3) the **magenta→coral gradient footer**, the one place a gradient covers the full viewport width.

Type is **Open Sans** everywhere (300–800 variable). Unlike editorial systems, Forte *does* use weight for emphasis: section titles 700, card titles 600, body 400. Hierarchy is weight + wine color, not size alone.

The group is a **multi-brand system**: the same layout skeleton re-themes per sub-brand. Bank (Forte) is magenta; **Business** swaps the primary to `{colors.business-navy}`; **Premier** is a separate dark dialect with its own font (Cignika) and green-gold palette. The brand book page (`forte.kz/en/logo`) is the canonical token source for all of them.

**Key Characteristics:**
- Primary CTA is `{colors.primary}` (#4A0221, dark magenta) with white text, 56px tall, `{rounded.md}` (12px) corners. One family of button shape across the whole site.
- Inverse CTA (white fill, wine text) is used on every saturated or dark surface — never a ghost/translucent button.
- Section rhythm alternates **white → `{colors.surface-gray}` band → white → saturated promo banner → gray band → gradient footer**. The page never shows two gray bands in a row.
- Every product section carries a glossy, high-chroma **3D render** (magenta/pink/sky/silver materials). Illustrations overflow the top of their card container.
- Section headlines are centered `{typography.display-lg}` (37px / 700) in `{colors.primary}`, with a gray `{typography.body-md}` lead-in below.
- Border radius is generous and hierarchical: 12px controls → 16px small cards/chips → 24px big cards and banners.
- Interactive selection vocabulary is consistent: **filled wine = selected, wine outline / hairline = available**, across toggles, chips and segmented controls. Sky-blue is the "focus/progress" accent (slider thumbs, active tab underline).

## Colors

### Brand & Accent
- **Primary** (`{colors.primary}` — #4A0221, "Dark Magenta"): Primary button fill, section headline color, numbered step bullets, selected chip fill. This is the action color — *not* the logo magenta.
- **Primary Deep** (`{colors.primary-deep}` — #270111): Wine ink for chip labels, active underline-tab text, card titles on gray.
- **Brand Magenta** (`{colors.brand-magenta}` — #A31551, "Forte Magenta", CMYK 0/87/50/36): The master-brand color. Logo, app-icon tile, active second-tier nav link, magenta lockup surfaces.
- **Brand Pink** (`{colors.brand-pink}` — #F03785): End stop of the secondary gradient; never used flat.
- **Sky Blue** (`{colors.sky-blue}` — #61CFFF, CMYK 56/0/0/0): Second brand color. Full promo-banner surface ("Transfers Without Borders"), slider thumbs, active-tab underline, phone numbers in the footer.
- **Coral** (`{colors.coral}` — #FC9385, "Coral Sunshine", CMYK 0/42/47/1): Warm accent surface (stat tile "500 000+ card users", travel-card art) and gradient end stop.

### Surface
- **Canvas** (`{colors.canvas}` — #FFFFFF): Default page surface, calculator panels, mega-menu.
- **Surface Gray** (`{colors.surface-gray}` — #EDEDED): The workhorse. Full-bleed section bands *and* the fill of service cards, product cards and result panels.
- **Surface Soft** (`{colors.surface-soft}` — #F7F6F6): Very light alternative fill (story placeholders, subtle cards).
- **Surface Panel** (`{colors.surface-panel}` — #F1F2F3): Brand-book typography specimen panel.
- **Hairline** (`{colors.hairline}` — #D5D5D5): Input borders, filter-chip outlines, calculator row dividers.
- **Hairline Soft** (`{colors.hairline-soft}` — #EAEBEF): Brand-book lockup-tile borders and section rules.

### Text
- **Ink** (`{colors.ink}` — #1D1D1D): Default running text and nav items.
- **Body Muted** (`{colors.body-muted}` — #6C6C6C): Card descriptions, section lead-ins, inactive top-tier nav.
- **Slate** (`{colors.slate}` — #69758B): Secondary text with a cool cast — inactive tabs, calculator values, brand-book captions and eyebrows.
- **Link** (`{colors.link}` — #185AC5): Inline links and "More" text links on business tariff cards.
- **On Primary** (`{colors.on-primary}` — #FFFFFF): Text on wine, magenta, sky, mustard, navy and gradient surfaces.

### Promo & Category Surfaces
Used as **full-card fills**, never as small accents:
- **Sky** (`{colors.sky-blue}`) — transfers banner, white headline.
- **Mustard** (`{colors.market-mustard}` — #F0C54F) — ForteMobile banner and Market "Outdoor & Sports" tile.
- **Market Cyan** (`{colors.market-cyan}` — #00D0FF) — Market "Smartphones & gadgets" tile.
- **Magenta gradient** (#CA4B67 → #5D062C top-to-bottom) — Market "Beauty & Health" tile.
- **Navy gradient** (`{gradients.business-band}`) — fraud-awareness banner and Business promo bands; uses `button-inverse`.

### Gradients
| Token | Value | Use |
|---|---|---|
| `{gradients.footer}` | 210°, #FF6A78 → #9B053F → #820232 | Full-bleed footer on every Forte page |
| `{gradients.forte-primary}` | 90°, Dark Magenta → Coral | Brand-book "primary gradient" |
| `{gradients.forte-secondary}` | 90°, Forte Magenta → Pink | Brand-book "secondary gradient" |
| `{gradients.forte-hero}` | 115°, #4A0221 → #B8335F → #FC9385 | Presentation-template hero |
| `{gradients.business-band}` | 220°, Light Blue → Dark Blue | Business promo bands, presentation template |

### Sub-brand Palettes (from the brand book, "03 Sub-brands")
Every sub-brand keeps the Forte logotype and adds a coloured descriptor. Four colour families organise the group.

| Sub-brand | Lead HEX | Palette | Primary gradient | Secondary gradient |
|---|---|---|---|---|
| **Forte** (master) | #A31551 | Forte Magenta #A31551 · Sky Blue #61CFFF · Dark Magenta #4A0221 · Coral Sunshine #FC9385 | Dark Magenta → Coral | Magenta → Pink |
| **Solo** | #A31551 | Dark Magenta · Coral Sunshine · Forte Magenta · Sky Blue | Dark Magenta → Forte Magenta | Dark Magenta → Coral |
| **Premier** | #08342A | Dark Green #08342A · Medium Green #234E44 · Light Green #3A8171 · Forte Gold #C9B07E | Dark Green → Light Green | Medium Green → Forte Gold |
| **Business** | #072146 | Dark Blue #072146 · Medium Blue #043263 · Light Blue #1464A5 · Sky Blue #61CFFF | Dark Blue → Sky Blue | Sky Blue → White |
| **Corporate** | #043263 | Medium Blue · Light Blue · Sky Blue · Dark Blue | Medium Blue → Sky Blue | Dark Blue → Light Blue |
| **Leasing** | #1464A5 | Light Blue · Sky Blue · Medium Blue · Dark Blue | Light Blue → Sky Blue | Sky Blue → White |
| **Finance** | #878787 | Medium Grey #878787 · Light Grey #C6C6C6 · Dark Grey #3C3C3B · White Grey #F6F6F6 | Light Grey → White Grey | Dark Grey → Medium Grey |

Descriptor colours in lockups: Market (navy), Business (sky), Mobile (mustard), Solo (coral, on a Dark Magenta wordmark), Corporate (sky on mid-blue), Leasing (sky on navy), Premier (gold script on dark green), Finance (grey).

## Typography

### Font Family
**Open Sans** (variable, weights 300–800) is the brand typeface "across every product and surface — a humanist sans that stays legible from caption to display." Fallback: `system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`. The brand book publishes a downloadable Open Sans package.

**Premier** runs a separate face, **Cignika** (300/400/600/700), on its own dark site — treat it as a sub-system, like a pricing dialect.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `{typography.display-lg}` | 37px | 700 | 1.2 | -0.1295px | Page h1 and centered section h2 ("Get a Forte Card", "Our Services") in `{colors.primary}` |
| `{typography.display-md}` | 32px | 700 | 1.5 | 0 | Brand-book section headings ("02 Brand architecture") |
| `{typography.title-lg}` | 28px | 600 | 1.17 | -0.042px | Card titles ("Cards for Every Occasion"), product names |
| `{typography.banner-title}` | 28px | 500 | 1.14 | 0.07px | Promo-banner headline (white on sky/mustard/navy, ink on gray) |
| `{typography.title-md}` | 20px | 600 | 1.235 | -0.03px | Footer contact labels, sub-titles, swatch names |
| `{typography.value-lg}` | 24px | 400 | 1.5 | -0.168px | Calculator result values, footer phone numbers (sky blue) |
| `{typography.body-md}` | 16px | 400 | 1.5 | -0.048px | Body copy, nav links, descriptions |
| `{typography.button}` | 16px | 400 | 1.5 | 0 | Large CTA labels (weight 500 on inverse, 600 on "More") |
| `{typography.tab}` | 16px | 500 | 1.75 | 0 | Underline tabs ("12 months"), top-tier nav |
| `{typography.chip}` | 14px | 500 | 1.25 | 0 | Toggles, filter chips, small CTAs inside cards |
| `{typography.body-sm}` | 14px | 400 | 1.5 | 0 | Footer legal, swatch metadata, mega-menu items |
| `{typography.caption}` | 13px | 400 | 1.5 | -0.0195px | Breadcrumbs, input helper text ("min. amount 1,000 ₸") |
| `{typography.eyebrow}` | 12px | 600 | 1.5 | 1.8px | Brand-book section numbers ("01", "02"), uppercase meta |
| `{typography.premier-display}` | 44px | 700 | 1.15 | 0 | Premier h3 in Cignika |

### Principles
Forte uses **weight as emphasis**: 700 for section titles, 600 for card titles, 500 for interactive labels, 400 for reading text, 300 for light accents. Display headlines get slightly negative tracking (≈ -0.0035em). Headlines on white are always `{colors.primary}`, never pure black; body stays `{colors.ink}` with descriptions dropping to `{colors.body-muted}`.

Numbers carry the ₸ (tenge) glyph with a thin space and spaced thousands ("50 000 ₸", "4 825,3 ₸"). Open Sans covers Latin, Cyrillic and Kazakh — the site ships in Kazakh, Russian and English.

## Layout

### Spacing System
- **Base unit:** 4px. Observed steps: 4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48 · 80.
- **Button padding:** 16px × 20px (56px tall) for primary CTAs; 8px × 12px for compact toggles; 6px × 12px for chips.
- **Section padding (vertical):** ~80px (`{spacing.section}`) top and bottom on each band (gray "Get a Forte Card" band: 80px to headline).
- **Banner internal padding:** 80px horizontal inset for headline + CTA (`{spacing.banner-x}`); 48px × 32px padding inside calculator columns.
- **Gutters:** 30–40px between cards in service grids (`gap: 40px 30px`), 24px in brand-book grids, 12px between chips.

### Grid & Container
- **Container:** ~1248–1256px content width centered at 1440 viewport (≈ 92–96px side margin). Built on MUI with breakpoints 600 / 900 / 1280.
- **Service grid:** 4-up at desktop (Our Services), 3-up for deposits and Market tiles, 2-up for Premier / Solo cards.
- **Product carousels:** card rails bleed off both screen edges with partially visible neighbours and circular prev/next buttons centered underneath.
- **Calculators:** white panel ~1028px wide inside a gray band, split into two columns by a vertical hairline: inputs left, results right.
- **Brand book:** left-aligned single column, ~1036px wide, with a left sticky tab rail (Logotype · Brand architecture · Sub-brands · Typography · Downloads).

### Whitespace Philosophy
Whitespace is moderate, not editorial. Sections are dense with product content, but each band's headline is centered with breathing room above and below. Gray bands replace whitespace as the main separator.

## Elevation & Depth

| Level | Treatment | Use |
|---|---|---|
| Flat | No shadow; contrast between white and `{colors.surface-gray}` | Bands, service cards, product cards, chips |
| Banner lift | `rgba(0,0,0,0.1) 0 4px 8px` | Promo banners (gray, sky, mustard, navy) |
| Business card | `rgba(16,24,40,0.05) 0 1px 2px` + `rgba(0,0,0,0.13) 0 24px 38px` | Business tariff cards |
| Premier glow | `rgba(87,87,87,0.15) 0 10px 30px` | Premier dark cards |
| Mega-menu | Soft drop shadow, white card | Header dropdowns |

The elevation philosophy is **colour-block first, 3D illustration second, shadow last**. Depth comes from glossy rendered objects (physically lit cards, coins, safes, phones) that break out of flat containers, rather than from layered shadows.

Motion follows MUI defaults: `0.25s cubic-bezier(0.4, 0, 0.2, 1)` on background/border/shadow and `0.15s` on colour and margin.

### Decorative Depth
- **3D product renders** in brand materials (magenta lacquer, sky glass, brushed silver, iridescent "?" tokens) are the signature illustration style. Always place them overlapping the top edge of their card.
- **Story strip** at the top of the bank home: 8 tall rounded story cards (~138 × 230px) with a gradient ring border, Instagram-style.
- **Card art**: the physical card designs (sky card with magenta arcs, Solo wine card with copper line-work, coral Travel card) double as decorative motifs.

## Shapes

### Border Radius Scale

| Token | Value | Use |
|---|---|---|
| `{rounded.xs}` | 4px | Tiny tags, small inline elements |
| `{rounded.sm}` | 8px | Brand-book download buttons, small swatches |
| `{rounded.md}` | 12px | Primary / inverse CTAs, inputs, search field, footer icon tiles, mega-menu |
| `{rounded.lg}` | 16px | Segmented toggles, result panels, lockup tiles, story cards, Market tiles |
| `{rounded.xl}` | 24px | Service cards, product cards, promo banners, calculator panels, swatch cards |
| `{rounded.pill}` | 22px | Filter chips (39px tall → full pill), language selector, a11y button |
| `{rounded.full}` | 50% | Carousel arrows, stepper +/- buttons, numbered step bullets |
| `{rounded.business-card}` | 20px | Business tariff cards (bottom-only 20px variant on stacked parts) |
| `{rounded.premier-tile}` / `{rounded.premier-card}` | 30px / 40px | Premier benefit tiles / card showcase panels |

### Photography & Illustration Geometry
3D renders sit transparent on top of card surfaces with no crop. Lifestyle photography (woman against sky) only appears inside a `{rounded.xl}` image CTA card within the footer. Card art keeps the ISO card ratio (85.6 × 54) with ~12px corners.

## Components

> **No hover states documented.** Per the global no-hover policy, components list Default and Active/Selected only. Variants live as separate entries in the `components:` front matter.

**`top-nav`** — A two-tier white header. Left: 64px app-icon logo tile (`{colors.brand-magenta}` gradient tile with white "f", `{rounded.md}`). Tier 1 is segment tabs (For you · For Business · Premier · More) in `{typography.tab}`; the active tab is `{colors.ink}` with a 2px `{colors.brand-magenta}` underline, inactive tabs are `{colors.body-muted}`. A hairline separates tier 2: product links (Cards, Loans, Deposits, Transfers, Solo, Payroll Services, Forex, Mobile, Market, Club) in `{typography.body-md}`; the active link turns `{colors.brand-magenta}`. Right cluster: a 240px gray search field (`{colors.surface-gray}`, `{rounded.md}`, magnifier + mic icons), a circular outline accessibility (eye) button, and an outlined "Eng" language selector. Business adds an outlined "Sign in to Forte Business" button.

**`mega-menu`** — Opens under a tier-2 link. White card, `{rounded.md}`, soft shadow, 24px padding. Columns separated by vertical hairlines; column headings in 16px / 600 ink; items in 14px ink with 20px row rhythm (e.g. Cards | Premium cards | Documents).

**`breadcrumb`** — `{typography.caption}`, "Main / All cards", sitting on white directly above the hero band.

### Buttons

**`button-primary`** — Background `{colors.primary}`, text `{colors.on-primary}`, `{typography.button}`, padding 16 × 20px, height 56px, `{rounded.md}`. Labels: "Open card", "Apply", "Learn more", "Open a deposit". Inside cards it compacts to ~48px height with `{typography.chip}`-to-16px labels. On mobile it stretches full-width.

**`button-inverse`** — White fill, `{colors.primary}` text, 500 weight, same geometry. The only CTA allowed on sky, mustard, navy, gradient and photo surfaces ("Go to", "Learn more" on the navy banner).

**`button-download`** — Brand-book variant: `{colors.primary}` fill, white 16px / 600 label with a leading download icon, `{rounded.sm}`, ~40px tall. Outline variant (white, hairline, wine text) inside download cards.

**`segmented-toggle`** — Paired pills, 36px tall, `{rounded.lg}`, `{typography.chip}`. Active: `{colors.primary}` fill + white text. Inactive: transparent with 1px `{colors.primary}` outline and wine text. Used for Debit / Credit funds, Loan / Deposits.

**`filter-chip`** — White pill with 1px `{colors.hairline}`, `{colors.primary-deep}` text, padding 6 × 12px, `{rounded.pill}`. Active state fills `{colors.primary}` (Selling / Buying, Annuity / In Equal Parts, KZT / US Dollar / EUR).

**`subbrand-chip`** — Brand-book chip row (Forte · Solo · Premier · …): white pill with hairline; the active chip fills `{colors.brand-magenta}` with white text.

**`underline-tab`** — Text tabs with a 2px underline: active `{colors.primary-deep}` text + `{colors.sky-blue}` underline, inactive `{colors.slate}` + gray underline. Used for loan terms ("12 months … 60 months") and binary choices ("Receiving / Not Receiving").

**`icon-button-circular`** — 40 × 40px, `{rounded.full}`. White or light gray fill, gray chevron. Carousel prev/next, calculator −/+ steppers.

**`text-link`** — `{colors.link}` (#185AC5), no underline, 16px. Footer contact values use `{colors.sky-blue}` instead.

### Cards & Containers

**`hero-band`** — `{colors.surface-gray}` full-bleed band holding either a centered display headline + 3D card fan + one `button-primary` (home), or a left headline + subcopy + CTA with a 3D object on the right (product pages). Business swaps to `{colors.business-ice}`.

**`stat-tile`** — Coral (`{colors.coral}`) tile, `{rounded.lg}`, with a cut-out photo and a "500 000+ / Card users" stat, paired with a white feature card split into two icon-led columns.

**`service-card`** — `{colors.surface-gray}`, `{rounded.xl}`, ~282px wide in a 4-up grid. A 3D render overflows the top; below it a centered `{typography.title-lg}` title in `{colors.primary}`, a 2-line `{colors.body-muted}` description, and a compact `button-primary`.

**`product-card`** — Carousel card on `{colors.surface-gray}`, `{rounded.xl}`. Card art (ISO ratio) floats over the top edge; centered product name (`{typography.title-lg}`, wine), a one-line descriptor, and "Learn more".

**`promo-banner`** — Full container width (~1248px), `{rounded.xl}`, ~320–350px tall, banner-lift shadow (`rgba(0,0,0,0.1) 0 4px 8px`). Left: `{typography.banner-title}` headline (max ~520px) and a CTA 64px below. Right: a large 3D object. Variants:
- `promo-banner-gray` — `{colors.surface-gray}`, ink headline, `button-primary`.
- `promo-banner-sky` — `{colors.sky-blue}`, white headline, `button-primary`.
- `promo-banner-mustard` — `{colors.market-mustard}`, white headline, `button-primary`.
- `promo-banner-navy` — `{gradients.business-band}`, white headline, `button-inverse`.

**`category-tile`** — Market grid tiles, ~278 × 600px, `{rounded.lg}`, saturated fills (`{colors.market-cyan}`, magenta gradient, `{colors.market-mustard}`), white 28px / 500 two-line title top-left, a 3D product cluster bottom.

**`calculator-panel`** — White, `{rounded.xl}`, inside a gray band. Left column: label (`{typography.title-md}` at 18–20px ink), range slider (hairline track, white thumb with `{colors.sky-blue}` ring), min/max captions, an outlined `text-input` with the ₸ suffix, then `underline-tab` groups. Right column: a `{colors.surface-gray}` result box (`{rounded.lg}`) with a big value between circular −/+ steppers, then key/value rows (ink label, `{colors.slate}` `{typography.value-lg}` value) separated by hairlines, and an "Apply" `button-primary` aligned right (full-width on deposits).

**`stepper-list`** — Numbered `{colors.primary}` 32px circles joined by a 2px wine vertical line; each step's text sits in a white (or gray) `{rounded.md}` box. Usually paired with a gray "Open in the Forte app" card holding a 3D phone.

**`footer`** — Full-bleed `{gradients.footer}`. Top: a photo CTA card (`{rounded.xl}`, sky-photo with teal overlay, white headline "Thank you for choosing Forte!", `button-inverse` "Go to"). Then the white Forte wordmark between thin coral-tinted hairlines. Left column: contact rows with 56px white `{rounded.md}` icon tiles, a white `{typography.title-md}` label and a `{colors.sky-blue}` `{typography.value-lg}` value (7575, 55575, Write to us, Show). Right: "Forte" link columns in white 16px, then accordions (For you · For Business · Premier) with chevrons and hairline dividers. Bottom: underlined license link and 14px disclaimer.

### Brand Book Components

**`swatch-card`** — `{rounded.xl}` card filled with the colour itself; name in 20px / 600 white, CMYK / HEX / RGB rows in 14px (label at 75% white, value at 600). The master card adds the logo, a translucent `rgba(255,255,255,0.18)` HEX pill, and "Master brand".

**`gradient-bar`** — 8px tall `{rounded.full}` bar showing a gradient, with a caption row underneath ("Primary gradient … Dark Magenta → Coral").

**`lockup-tile`** — White, 1px `{colors.hairline-soft}`, `{rounded.lg}`, ~250 × 120px, centered sub-brand logo. Arranged in a column-per-family masonry.

**`logo-surface-tile`** — Three 120px-tall tiles showing the logo on white, on #270111 and on `{colors.brand-magenta}`.

**`type-specimen`** — `{colors.surface-panel}` panel, `{rounded.xl}`, 40px padding: "Open Sans" at ~72px / 800, a 24px sample sentence, the weight row (Light → Extrabold), then a 3-column Family / Weights / Usage spec under a hairline.

**`download-card`** — `{rounded.xl}` white card with hairline; a gradient cover (Forte hero gradient or Business navy gradient) with the white logo, then a title and an outlined `button-download`.

### Inputs & Forms

**`text-input`** — White, 1px `{colors.hairline}`, `{rounded.md}`, ~48px tall, 12 × 16px padding, `{typography.body-md}`; value suffixed with "₸". Helper text below in `{typography.caption}` `{colors.slate}`.

**`select`** — Same shell as `text-input`, with a leading flag icon (USD / KZT) and a trailing chevron.

**`search-field`** — `{colors.surface-gray}` fill, no border, `{rounded.md}`, 44px tall, leading magnifier, trailing mic, placeholder in `{colors.slate}`.

### Business Dialect (business.forte.kz)
Same skeleton, re-themed: headline colour `{colors.business-navy}`, primary button navy-filled, hero band `{colors.business-ice}`, navy app-icon logo tile, an extra second-tier row (Tariff, Accounts & Transactions, Cards, Loans, Guarantees, Merchant Acquiring, Banking, Deposits, Foreign Trade, Government Services). **`tariff-card`**: white, `{rounded.business-card}`, two-layer shadow, title 28px / 600, a top-right sky-blue corner glow behind a silver 3D coin, "Free transfers / Starting from" stat pairs, and a `{colors.link}` "More" link. The navy gradient band uses `button-inverse`.

### Premier Dialect (premier.forte.kz)
A separate dark site. Page `{colors.premier-night}` (#121A1B), nav `{colors.premier-nav}` with a `{colors.premier-teal}` active link, sub-nav bar #3C3C3C with icon + label items. Type is **Cignika**: 44px / 700 headlines in white. Primary CTA `{colors.premier-cta}` (#98134B) with `{rounded.md}`; secondary is white. Benefit tiles `{colors.premier-tile}` with `{rounded.premier-tile}` and pastel 3D icons; card-showcase panels `{colors.premier-slate}` with `{rounded.premier-card}`. A teal dash is the carousel indicator. Keep Premier's font, darkness and radii together; don't mix them into the bank site.

## Do's and Don'ts

### Do
- Use `{colors.primary}` (#4A0221) for every primary action and section headline. `{colors.brand-magenta}` (#A31551) is for the logo, brand moments and the active nav link.
- Pair every product section with a glossy 3D render that overlaps its container's top edge.
- Alternate white and `{colors.surface-gray}` bands; break the rhythm every one or two screens with a saturated `promo-banner`.
- Use `button-inverse` on any saturated, gradient, photo or dark surface.
- Express selection as **wine fill vs. wine/hairline outline**, consistently across toggles and chips.
- Use `{colors.sky-blue}` for progress and focus cues (slider thumb, active tab underline).
- Re-theme sub-brands by swapping the palette from the sub-brand table, keeping layout, radii and type.
- Keep every displayed amount in tenge format: "1 000 ₸", "4 825,3 ₸".

### Don't
- Don't use pure black for headlines; display type is always wine (`{colors.primary}`) on light surfaces.
- Don't put the full-viewport gradient anywhere but the footer. Gradients elsewhere stay inside a `{rounded.xl}` container.
- Don't recolour the logo outside the approved set (on white, on #270111, on `{colors.brand-magenta}`), and keep clear space around the mark.
- Don't use ghost or translucent buttons on colour; the inverse button stays solid white.
- Don't drop below `{rounded.md}` (12px) on buttons or below `{rounded.lg}` on cards; Forte's shapes are soft.
- Don't mix sub-brand palettes on one surface (no navy Business button on a magenta bank page).
- Don't bring Cignika or the Premier dark surfaces into Bank or Business pages.
- Don't add hover styling beyond what the system already encodes.

## Responsive Behavior

### Breakpoints (MUI)

| Name | Width | Key Changes |
|---|---|---|
| Mobile | < 600px | Header collapses to the coloured "forte" wordmark + eye + "Eng" + hamburger; stories become a horizontal swipe row; CTAs go full-width; service and product cards become horizontal swipe rails with peeking neighbours; section titles drop to ~26px / 700 |
| Tablet | 600–899px | 2-up grids; tier-2 nav hidden behind the menu; calculators stack inputs above results |
| Desktop | 900–1279px | Full two-tier nav; 3–4-up grids; calculator two-column split |
| Wide | ≥ 1280px | Container caps at ~1248–1256px; outer margins grow |

Premier uses the older MUI v4 set: 600 / 960 / 1280 / 1920.

### Touch Targets
- `button-primary` is 56px tall on desktop and ~44px on mobile, at or above WCAG's 44 × 44.
- Header icon buttons (a11y eye, language) are 44px.
- `icon-button-circular` carousel arrows are 40px, slightly under 44.

### Collapsing Strategy
- Grids become **horizontal swipe rails** rather than stacking (Our Services, product cards).
- Promo banners stack the headline + CTA above the 3D object.
- The footer columns stack; link groups become accordions.

## Iteration Guide

1. Pick the sub-brand first (Forte / Solo / Business / Corporate / Leasing / Finance / Premier) and pull its palette from the sub-brand table. Everything else in the system stays the same, except for Premier.
2. Work one component at a time and reference its YAML key (`{component.button-primary}`, `{component.promo-banner}`).
3. Variants (`-active`, `-inactive`, `-gray`, `-sky`, `-navy`) live as separate entries in `components:`, never as nested state objects.
4. Use `{token.refs}` in prose; write a hex code at most once, next to its reference.
5. When adding a section, ask: which band colour comes next in the white/gray/saturated rhythm, and which 3D render anchors it?
6. When in doubt about emphasis: wine colour + weight 700 before size, and a saturated banner before a new accent colour.
7. Run `npx @google/design.md lint DESIGN.md` after edits.

## Known Gaps

- **Pressed/active colours** for buttons were not captured (no click-and-hold sampling). `{colors.primary-deep}` (#270111) is a plausible pressed state but is only confirmed as a text colour.
- Market tile fills (`{colors.market-cyan}`, the magenta tile gradient) and Premier surfaces were **pixel-sampled from screenshots**; promo/banner fills and all brand-book values were read from computed styles.
- The site defines **no CSS custom properties**: styles are MUI/emotion-generated classes, so tokens here are reverse-engineered from computed styles.
- Section padding (~80px) and the container width are measured from screenshots, not from a declared token.
- The `.zip` logo/font package and the two `.pptx` presentation templates on the brand book were **not downloaded**.
- Only the English pages were covered. Russian/Kazakh pages, loans, transfers, Solo, Market, Mobile and Club sub-sites were not individually visited.
- Hover, focus rings and form error states are not documented.
- Some early full-page screenshots captured before webfonts loaded render the fallback system font; computed styles confirm Open Sans everywhere except Premier.
