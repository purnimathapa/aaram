# AARAM design guide

The target is a calm, quiet, trustworthy mattress brand from Nepal. It should look like a small, real brand designed it by hand, not like a generated template. The reference mockups are in `docs/design/mockups/` (one file per page). They use a mockup format, so copy the look, layout and copy, not the markup.

## Tokens (put these in `static/css/tokens.css` as CSS custom properties)

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | `#F6F1E9` | Page background (linen) |
| `--surface` | `#FFFDF8` | Cards, inputs, panels |
| `--surface-2` | `#EDE4D6` | Picture wells, size-guide band |
| `--line` | `#E4DACB` | Borders, dividers |
| `--line-strong` | `#D9CCB8` | Input borders, unselected options |
| `--ink` | `#24201C` | Main text, footer background |
| `--muted` | `#5C5349` | Secondary text (passes contrast on `--bg`) |
| `--subtle` | `#6B6257` | Small labels, captions |
| `--accent` | `#23395B` | The only accent: buttons, selected state, links, focus ring |
| `--accent-soft` | `#E3E8F0` | Selected option background, info pills |
| `--ok` / `--ok-bg` | `#2F6B3F` / `#E2EFE3` | In stock, delivered, paid |
| `--warn` / `--warn-bg` | `#7A4210` / `#F6E6CF` | Few left, pending, unpaid |
| `--bad` / `--bad-bg` | `#8B2C2C` / `#F5E0DE` | Sold out, cancelled, errors |

Spacing scale: 4, 8, 12, 16, 24, 32, 48, 72 px. Radius: 10 px buttons and inputs, 18 px cards, 999 px pills. Content max width 1200 px with 24 px side padding.

## Type
- Headings: **Newsreader** (serif), weight 500. h1 44–64 px, h2 32–40 px.
- Everything else: **Figtree**, 16 px body, line-height 1.5. Labels 13–15 px.
- Devanagari wordmark "आराम": **Noto Serif Devanagari** 500, only beside the logo.
- Load from Google Fonts with one `<link>`; `font-display: swap`.

## Components (one template partial or CSS block each)
- **Button**: primary = `--accent` fill, white text, 48 px tall; secondary = 1.5 px `--accent` outline. No other button styles.
- **Product card**: surface card, layer illustration on `--surface-2`, category label, stock pill, serif name, feel, "From Rs. X".
- **Layer illustration**: stacked divs (cover, comfort, core, base) drawn with CSS from the product's data. This replaces photos until real photos exist.
- **Option chips** (size, thickness): 2 px `--accent` border + `--accent-soft` fill when selected; show dimensions in inches and cm.
- **Stock pill**: ok / warn / bad colours above, text says the fact ("Only 2 left").
- **Status timeline**: vertical dots and lines; done = filled accent, current = ring, upcoming = grey.
- **Forms**: visible labels above fields, 44 px min height, errors in `--bad` under the field with plain words.
- **Staff area**: dark `--ink` sidebar, light content, tables with a horizontal scroll box on small screens, CSS bar charts or Chart.js with the accent for the one bar that matters and grey for the rest.

## Graphics
- Icons: inline SVG line icons (Lucide style), 1.6–2 px stroke, `currentColor`, `aria-hidden="true"`. Never emoji.
- Size guide: four rectangles drawn to scale (2 px per inch).
- Province map: schematic tile map of the 7 provinces, west to east, clickable, labelled "not to scale".
- Photos (when available): WebP/JPG, about 1600 px wide, under 200 KB, always with alt text.

## What makes it NOT look AI-made (follow strictly)
- No gradients, glows, glassmorphism, blurred blobs, neon or purple/indigo-to-pink colour schemes.
- No emoji anywhere: UI, copy, code, commit messages.
- No Inter, Roboto, Poppins or Arial; use the fonts above.
- No generic hero copy ("Welcome to AARAM", "Unlock your best sleep", "Revolutionize"). Write plain, specific sentences like the mockups.
- No invented testimonials, ratings, "10,000+ happy customers" or trust badges. Real data or nothing.
- No heavy drop shadows or every-card-floats look; use 1 px borders. At most one soft shadow for dropdowns.
- No icon above every heading, no three-identical-feature-cards-with-icons as filler sections.
- No centered-everything layouts; text is left-aligned, sections have a clear reading order.
- No animations except a 150 ms colour/border transition on hover and focus. Respect `prefers-reduced-motion`.
- One accent colour. Status colours only for status.
- Every interactive element is a real `<a>`, `<button>`, `<input>` or `<select>`, keyboard reachable, with a visible focus ring.

## Responsive
Design mobile-first. Layout with flex/grid and `flex-wrap`; the catalogue filters collapse above the grid on phones; tables scroll inside a box; no horizontal page scroll at 360 px.
