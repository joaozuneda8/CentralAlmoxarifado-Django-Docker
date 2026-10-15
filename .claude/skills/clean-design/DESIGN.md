# Design Guidelines — Clean Style
Clean SaaS / Editorial aesthetic*

## Visual Style
- **Aesthetic**: Clean, minimal SaaS — pure white dominant, warm off-white alternate sections, maximum whitespace
- **Mood**: Professional, trustworthy, modern — editorial without being cold
- **Inspiration**: Grovia, Linear, Stripe, Loom — top-tier SaaS landing pages

## Color Palette
- **Primary / CTA**: #0F0E0C — near-black; used for primary buttons, headings, key text
- **Background**: #FFFFFF — pure white
- **Surface / Alternate section**: #F7F6F2 — warm off-white; every other section uses this to create rhythm without using color
- **Card**: #FFFFFF — white with a subtle border, no colored backgrounds
- **Text Primary**: #0F0E0C
- **Text Secondary**: #6B6760 — warm medium gray for body copy and descriptions
- **Text Muted**: #A8A49F — captions, overline labels, placeholders
- **Border**: #E8E6E1 — very light warm gray; 1px on cards and inputs
- **Accent**: User-defined (default: same as Primary). Common overrides: #2563EB (blue), #16A34A (green), #4F46E5 (indigo)
- **No gradients. No colorful backgrounds. No shadows with color.**

## Typography
- **Display / H1**: Manrope or Geist — 700–800 weight, clamp(48px, 6vw, 88px), line-height 1.05, letter-spacing −0.025em
- **H2**: Same family — 700 weight, clamp(28px, 3vw, 44px), line-height 1.15, letter-spacing −0.015em
- **H3 / H4**: Same family — 600 weight, 20–26px, line-height 1.25
- **Body**: DM Sans — 400 weight, 16–18px, line-height 1.65, color `--text-secondary`
- **Labels / Overlines**: DM Sans — 500 weight, 11–13px, uppercase, letter-spacing 0.08em, muted color — used to introduce every section ("Features", "How it works")
- **Monospace**: Geist Mono or JetBrains Mono — for code snippets only
- **Never use**: Inter, Roboto, Arial, system-ui, Space Grotesk

## Spacing & Layout
- **Overall feel**: Extremely airy — sections breathe with generous vertical padding
- **Section padding**: 96–128px top/bottom (`6rem`–`8rem`)
- **Container**: max-width 1200px, centered, 24px horizontal padding
- **Card padding**: 28–32px internal
- **Grid**: 12-column underlying; feature grids use 2–3 columns; max 4 columns on wide screens
- **Base unit**: 8px — all spacing is a multiple of 8
- **Mobile**: Single column below 768px; section padding reduces to ~64px

## Borders & Radius
- **Border radius — cards**: 12px
- **Border radius — buttons**: 8px
- **Border radius — inputs**: 8px
- **Border radius — pill tags/badges**: 100px
- **Borders**: 1px solid #E8E6E1 on cards and inputs — structure only, never decorative
- **No gradient borders. No colored borders. No thick borders.**

## Shadows & Elevation
- **Cards (default)**: `box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.04)` — barely visible
- **Cards (hover)**: `box-shadow: 0 6px 20px rgba(0,0,0,0.08)` — subtle lift
- **Modals / elevated panels**: `box-shadow: 0 8px 30px rgba(0,0,0,0.09)`
- **Flat design overall** — shadows exist only to separate layers, never for decoration

## Buttons
- **Primary**: Near-black background (#0F0E0C), white text, 8px radius, 12px/24px padding, weight 500 — transitions to #333 on hover
- **Secondary / Ghost**: Transparent background, 1px border (#E8E6E1), near-black text — background goes to #F7F6F2 on hover
- **All buttons**: `transition: all 0.18s ease`, `transform: scale(0.98)` on active/press
- **No pill buttons** (except badge/tag elements). No colorful buttons unless accent color is set.

## Icons
- Lucide-style SVG line icons — 24×24 viewBox, stroke="currentColor", stroke-width="1.5", rounded caps/joins, fill="none"
- UI size: 18–24px; feature highlight size: 32–48px
- Color: always `currentColor` — inherits from surrounding text
- **No emoji. No icon fonts. No colored icon backgrounds.**

## Components Spotted

- **Navbar**: Sticky, white background, logo left, nav links center (About / Features / Pricing / Contact), two CTA buttons right (ghost + primary). Clean rule or subtle shadow on scroll.
- **Hero**: Centered layout — overline label → large bold H1 (2–3 lines) → body subtitle → two CTAs → social proof strip below (avatar cluster + star rating + customer count)
- **Logo strip**: Grayscale logos at 40–60% opacity in a horizontal marquee; pauses on hover
- **Numbered steps**: Large muted number (01, 02, 03) as overline → H3 heading → short description → supporting image alongside
- **Feature tabs**: Pill-style tab switcher (Client portal / KPI tracking / Workflow / Team) → large content panel with screenshot right
- **Feature cards**: 3-column grid — small SVG icon → H4 → one-sentence description. No paragraph walls.
- **Testimonial cards**: White card with border, quote text, name + role, small circular avatar — 2–3 column grid on `--bg-subtle` section background
- **Pricing cards**: 3 columns — label overline + plan name + price + description + CTA button + feature checklist (SVG check icon, not emoji). Middle card slightly elevated with "Most Popular" pill badge.
- **FAQ accordion**: Question text + chevron SVG right-aligned; body expands with max-height transition; thin rule between items; no card borders
- **Contact / CTA section**: Full-width section, large display-size email address as visual anchor, name/email/message form inputs, submit button, social proof cluster
- **Footer**: Large display-size email as design element; 3–4 column link grid; bottom bar with copyright; social icons (SVG only — X, Instagram, LinkedIn)

## Imagery & Illustration
- Product UI screenshots in browser or floating panel mockups — no lifestyle photography in the hero
- Real headshot avatars for testimonials and customer lists — small, circular crop
- Abstract soft background images for certain sections (subtle texture, not distracting)
- No stock photo people. No flat vector illustrations. No 3D renders.

## Micro-Animations
- **Scroll reveal**: Fade-up (opacity 0→1, translateY 24px→0) via Intersection Observer, threshold 0.12, duration 0.55s ease
- **Stagger**: Child elements delay 0s / 0.08s / 0.16s / 0.24s for grid cards and feature lists
- **Hero load**: H1 → subtitle → CTAs stagger in on page load with fadeUp, delays 0.1s / 0.22s / 0.34s
- **Card hover**: translateY(−2px) + shadow increase, duration 0.2s ease
- **Button active**: scale(0.98)
- **Nav link hover**: underline draws in from left (width 0→100%, 0.22s ease)
- **Logo marquee**: Continuous scroll, pauses on hover
- **FAQ accordion**: max-height transition 0.35s ease + opacity, chevron rotates 45° when open

## Overall Replication Notes
- Whitespace is the primary design tool — don't crowd elements, ever
- Alternate section backgrounds (#FFF → #F7F6F2 → #FFF) create rhythm without using color
- Overline labels (small, uppercase, muted) introduce every section — this is a signature pattern
- Numbered steps (01, 02, 03) in large muted type are used for process/how-it-works flows
- Keep the color palette tight — 2 neutrals + 1 optional accent; don't introduce new colors
- Typography does the heavy lifting — size contrast between H1 and body is dramatic
- Every interactive element must have a hover state and a transition
- Footer email address rendered at display size is a deliberate editorial choice, not an accident
- No emoji anywhere in the UI — SVG icons handle all visual communication
- Mobile: single column, reduced padding, same typographic hierarchy
