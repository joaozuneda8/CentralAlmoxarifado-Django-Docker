---
name: clean-design
description: Design and build websites and web apps using the "Clean" design style — a refined, editorial, whitespace-first aesthetic inspired by top-tier SaaS landing pages. Think Grovia, Linear, Stripe, Loom: pure white backgrounds, bold geometric typography, near-black text, ultra-subtle surfaces, SVG line icons, no emojis, and purposeful micro-animations. Use this skill whenever the user asks to design or build anything in "clean" style, a "minimal" or "refined" aesthetic, a "Stripe-like" or "Linear-like" look, or when they say things like "make it clean", "modern SaaS look", "editorial design", "no clutter", "whitespace-forward", or "professional and clean." Always trigger this skill for these requests — do NOT attempt clean design from memory alone.
---

# Clean Design Skill

Build websites and web apps in the Clean design style: editorial, whitespace-first, typographically precise, and free of AI slop. Every output should feel like it was designed by a senior product designer at a world-class SaaS company.

---

## Step 1 — Ask Clarifying Questions

Before writing any code, ask the user these questions. Keep the tone conversational. If they don't know an answer, use the defaults listed.

```
1. What is this for? (landing page, dashboard, app, portfolio, etc.)
2. What is the brand name / product name?
3. Do you have a preferred color palette or accent color?
   → Default: Near-black (#111111) + white (#FFFFFF) + warm gray (#F5F4F0) sections + one accent color (see default palette below)
4. What's the primary audience? (developers, executives, consumers, etc.)
   → Default: "modern professionals / startup teams"
5. Do you have preferred fonts?
   → Default: Geist Sans for headings + DM Sans for body. Prefer the project's local font files when they exist (e.g. self-hosted `.woff2` with `@font-face`); load from Google Fonts only for standalone deliverables with no local fonts
6. What sections / pages do you need?
   → Default: Hero, Social proof / logos, Features, How it works, Pricing, Testimonials, FAQ, CTA, Footer
7. Light mode, dark mode, or both?
   → Default: Light mode only
```

Only ask — **don't code yet**. Once you have the answers (or the user says "use defaults"), proceed to Step 2.

---

## Step 2 — Design Decisions

Before writing code, confirm your design direction internally using this checklist:

### Typography
- **Display / H1–H2**: Geist Sans 700–800, large (clamp 48px–96px), tight leading (1.05–1.1), normal or slightly negative letter-spacing (−0.02em)
- **Subheadings H3–H4**: Same font, 500–600 weight
- **Body**: DM Sans 400, 16–18px, leading 1.65, color `--text-secondary`
- **Labels / Overlines**: DM Sans 500, 11–13px, uppercase, 0.08em letter-spacing, muted color
- **NEVER use**: Inter, Roboto, Arial, system-ui, Space Grotesk — these are cliché

### Color Palette — Default
```css
--bg:           #FFFFFF;
--bg-subtle:    #F7F6F2;   /* warm off-white for alternate sections */
--bg-card:      #FFFFFF;
--border:       #E8E6E1;
--text-primary:   #0F0E0C;
--text-secondary: #6B6760;
--text-muted:     #A8A49F;
--accent:         #1A1A1A;  /* user can override: indigo, green, amber, etc. */
--accent-hover:   #333333;
--accent-text:    #FFFFFF;
```
> If the user provides an accent color (e.g. blue), derive a full accessible palette from it. Keep bg/text unchanged.

### Spacing System
- Base unit: 8px
- Section vertical padding: 96px–128px (`6rem`–`8rem`)
- Container: max-width 1200px, centered, horizontal padding 24px
- Card internal padding: 28–32px
- Consistent 8px grid: 8, 16, 24, 32, 48, 64, 96, 128

### Borders & Radius
- Cards: `border: 1px solid var(--border)` + `border-radius: 12px`
- Buttons: `border-radius: 8px`
- Inputs: `border-radius: 8px`
- Pill tags/badges: `border-radius: 100px`
- NO harsh or decorative borders — just structure

### Shadows & Depth
- Cards: `box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.04)` — barely there
- Elevated modals: `box-shadow: 0 8px 30px rgba(0,0,0,0.08)`
- NEVER use heavy, colorful, or "floating" shadows — they break the clean aesthetic

### Buttons
- **Primary**: `background: var(--text-primary); color: #FFF; border-radius: 8px; padding: 12px 24px; font-weight: 500`
- **Secondary / Ghost**: `border: 1px solid var(--border); color: var(--text-primary); background: transparent`
- **Hover**: Primary lightens to `#333`; Ghost background goes to `var(--bg-subtle)`
- Transitions: `transition: all 0.18s ease`

### Icons
- **ALWAYS** use SVG inline icons — Lucide style (1.5px stroke, rounded caps/joins)
- Size: 18–24px for UI, 32–48px for feature highlights
- Color: `currentColor` so they inherit text color naturally
- **NEVER** use emoji as icons. **NEVER** use icon fonts.
- Recommended icon set reference: Lucide (https://lucide.dev) — copy SVG paths inline

---

## Step 3 — Layout Patterns

These are the canonical Clean design layout patterns. Use the right one per section type.

### Hero
- Centered or left-aligned layout
- Overline label above heading (e.g. "Trusted by 9,000+ teams")
- H1: 2–4 lines max, very large, bold
- Subtext: 1–2 sentences, `--text-secondary`
- 2 CTAs: primary (dark button) + ghost (no bg)
- Below fold: social proof strip (logos or avatar cluster + rating)
- Optional: UI screenshot or abstract visual floating below with subtle shadow

### Feature Sections
- **Tab/pill switcher** layout: tabs on left or top, content panel on right
- OR **numbered steps** (01, 02, 03) with alternating text + visual
- Overline: "Features" label in muted, uppercase, small
- Heading: bold, 2–3 lines
- Feature cards: 3-column grid, icon (SVG) + title + 1-sentence description
- NO paragraph walls in feature cards

### Social Proof / Logos
- Muted grayscale logos in a marquee/scroll strip OR static grid
- Opacity: 0.4–0.6 so they don't overpower
- Above or below hero

### Testimonials
- Cards with: quote (no giant quotation marks), name, role/company, small avatar photo or initials circle
- 2–3 column grid or horizontal scroll
- Background: `var(--bg-subtle)` section

### Pricing
- 3-column cards (Starter / Growth / Scale or equivalent)
- Middle card: slight elevation + optional "Most Popular" pill
- Feature checklist: small checkmark SVG icon, left-aligned list

### FAQ
- Accordion pattern: question + expand arrow SVG
- Clean rule lines between items, no card borders

### Footer
- Large email or CTA as visual anchor element (H2 or display size)
- 3–4 column links
- Bottom bar: copyright + legal links
- Social links: SVG icons only

---

## Step 4 — Micro-Animations

These are **mandatory** in every clean design output. They create polish without distraction.

### Scroll Reveal (use Intersection Observer)
```js
// Fade-up on scroll — apply to sections, cards, headings
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('visible'); }
  });
}, { threshold: 0.12 });
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
```
```css
.reveal { opacity: 0; transform: translateY(24px); transition: opacity 0.55s ease, transform 0.55s ease; }
.reveal.visible { opacity: 1; transform: none; }
/* Stagger children */
.reveal-stagger > * { opacity: 0; transform: translateY(20px); transition: opacity 0.45s ease, transform 0.45s ease; }
.reveal-stagger.visible > *:nth-child(1) { opacity:1; transform:none; transition-delay:0s; }
.reveal-stagger.visible > *:nth-child(2) { opacity:1; transform:none; transition-delay:0.08s; }
.reveal-stagger.visible > *:nth-child(3) { opacity:1; transform:none; transition-delay:0.16s; }
.reveal-stagger.visible > *:nth-child(4) { opacity:1; transform:none; transition-delay:0.24s; }
```

### Hover States
```css
/* Card lift */
.card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
.card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.08); }

/* Button press */
button:active { transform: scale(0.98); }

/* Link underline draw */
.nav-link { position: relative; }
.nav-link::after { content:''; position:absolute; bottom:-2px; left:0; width:0; height:1px; background:currentColor; transition:width 0.22s ease; }
.nav-link:hover::after { width:100%; }
```

### Page Load
```css
/* Hero stagger on load */
@keyframes fadeUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:none; } }
.hero-title   { animation: fadeUp 0.6s ease 0.1s both; }
.hero-sub     { animation: fadeUp 0.6s ease 0.22s both; }
.hero-actions { animation: fadeUp 0.6s ease 0.34s both; }
```

### Logo Marquee (if used)
```css
@keyframes marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }
.marquee-track { animation: marquee 28s linear infinite; display:flex; width:max-content; }
.marquee-track:hover { animation-play-state: paused; }
```

### Accordion (FAQ)
```css
.faq-body { max-height: 0; overflow: hidden; transition: max-height 0.35s ease, opacity 0.3s ease; opacity: 0; }
.faq-item.open .faq-body { max-height: 300px; opacity: 1; }
.faq-icon { transition: transform 0.3s ease; }
.faq-item.open .faq-icon { transform: rotate(45deg); }
```

---

## Step 5 — Anti-AI-Slop Rules

These are non-negotiable. Violating any of these breaks the clean aesthetic.

**NEVER do:**
- ❌ Emoji anywhere (not in buttons, not in feature cards, not in lists)
- ❌ Purple-to-blue gradients on white backgrounds
- ❌ Hero sections with giant gradient blobs or abstract colored shapes
- ❌ "✓ Feature one / ✓ Feature two" with checkmark emoji
- ❌ Colorful icon backgrounds (no teal square behind a white icon)
- ❌ Cards with rainbow borders or gradient strokes
- ❌ Three-column feature grids with huge icons and paragraph-length descriptions
- ❌ "AI-generated" stock photo aesthetics
- ❌ Generic "Get Started Today!" hero headlines
- ❌ Font: Inter, Roboto, Arial, system-ui
- ❌ Overuse of `font-weight: 800` everywhere
- ❌ Testimonial cards with oversized quotation mark decorations ("❝")
- ❌ Pricing card with a glowing ring or neon border
- ❌ Excessive use of `border-radius: 24px` or `border-radius: 50px` on everything

**ALWAYS do:**
- ✓ Let whitespace do the work — sections breathe
- ✓ Use SVG icons inline, Lucide-style
- ✓ Stick to the 3-color rule: background, text, one accent
- ✓ Use numbered sections (01, 02, 03) for step-by-step flows
- ✓ Make the footer feel like a design decision, not an afterthought
- ✓ Use overline labels (small caps, muted, uppercase) to introduce sections
- ✓ Typography hierarchy: H1 huge and bold → body comfortable and readable → captions small and muted
- ✓ Every interactive element has a hover and active state
- ✓ Mobile-first responsive — test at 375px, 768px, 1280px

---

## Step 6 — Code Output

**Modifying an existing application:** work inside it. Preserve its templates, layouts, static assets (CSS files, fonts, icons) and its script-loading conventions (e.g. scripts in `<head>` with `defer`), and reuse its existing class vocabulary and tokens instead of inlining new CSS/JS.

**Standalone deliverable** (a one-off page or prototype with no host app): produce a **single-file HTML artifact** (inline CSS + JS) unless the user specifies React or another framework.

Structure of a standalone file:
```
1. CSS reset + variables
2. Global typography + utility classes
3. Animations / transitions
4. Section-by-section HTML with semantic tags (nav, main, section, footer)
5. Intersection Observer JS at bottom
6. Responsive breakpoints (mobile-first)
```

For a new React project, use Tailwind classes mapped to the design tokens above and Framer Motion for animations. In an existing React app, keep its configured styling and animation stack; use Tailwind or Framer Motion only if the project already adopts them.

---

