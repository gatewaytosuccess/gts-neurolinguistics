---
version: alpha
name: GTS Neurolinguistics
description: Course-sales and lesson-delivery site for an academic neurolinguistics course, sharing the GTS credit-services brand lineage (navy, walnut, ledger cream) with its own signature brass accent for teaching and enrollment.

colors:
  # --- Brand core, inherited unchanged from the GTS credit-services site ---
  primary: "#0A2463"
  primary-strong: "#070D41"
  primary-subtle: "#ACCBE1"
  primary-pale: "#CEE5F2"
  primary-muted: "#7C98B3"
  accent: "#3C362A"
  accent-strong: "#261E0F"
  paper: "#F6F3EE"
  paper-raised: "#FCFAF6"
  paper-dim: "#DBD7D0"
  rule: "#C1BDB5"
  border-strong: "#857F74"
  meta-text: "#4A5A68"
  error: "#A12F2F"
  error-subtle: "#FFE3DF"
  success: "#225A31"
  success-subtle: "#DBEEDE"
  warning: "#6E4200"
  warning-subtle: "#F7E5CF"

  # --- The course site's own spin: a signature interaction color ---
  tertiary: "#DB9E38"
  tertiary-strong: "#925100"
  tertiary-pale: "#F5E6CE"

  # --- Dark mode: a separate design for the after-hours lesson dashboard ---
  dark-bg: "#15110B"
  dark-surface: "#211C15"
  dark-surface-overlay: "#302A22"
  dark-rule: "#3E372C"
  dark-border-strong: "#70685B"
  dark-on-surface: "#DCD7CF"
  dark-on-surface-meta: "#948E86"
  dark-primary: "#A0C3DA"
  dark-primary-strong: "#79A4C7"
  dark-tertiary: "#E1AD57"
  dark-tertiary-strong: "#CF9128"
  dark-error: "#DD766D"
  dark-error-subtle: "#391917"
  dark-success: "#69B27A"
  dark-success-subtle: "#122A18"
  dark-warning: "#CD995C"
  dark-warning-subtle: "#331F04"

typography:
  display:
    fontFamily: Fraunces
    fontSize: 96px
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: -0.03em
    fontVariation: "'wght' 600, 'SOFT' 40, 'WONK' 0, 'opsz' 96"
  headline-lg:
    fontFamily: Fraunces
    fontSize: 60px
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: -0.025em
    fontVariation: "'wght' 600, 'SOFT' 40, 'WONK' 0, 'opsz' 60"
  headline-md:
    fontFamily: Fraunces
    fontSize: 42px
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: -0.02em
    fontVariation: "'wght' 600, 'SOFT' 35, 'WONK' 0, 'opsz' 42"
  headline-sm:
    fontFamily: Fraunces
    fontSize: 30px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.015em
    fontVariation: "'wght' 600, 'SOFT' 30, 'WONK' 0, 'opsz' 30"
  quote:
    fontFamily: Fraunces Italic
    fontSize: 26px
    fontWeight: 500
    lineHeight: 1.35
    fontVariation: "'wght' 500, 'SOFT' 55, 'opsz' 26"
  body-lg:
    fontFamily: Source Sans 3
    fontSize: 20px
    fontWeight: 400
    lineHeight: 1.6
  body-md:
    fontFamily: Source Sans 3
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.65
  body-sm:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.6
  label-lg:
    fontFamily: Source Sans 3
    fontSize: 16px
    fontWeight: 600
    lineHeight: 1.3
  label-md:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.3
  label-caps:
    fontFamily: Source Sans 3
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: 0.08em
    fontFeature: "'case' 1"
  caption:
    fontFamily: Source Sans 3
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.45
  data-md:
    fontFamily: Source Sans 3
    fontSize: 15px
    fontWeight: 600
    lineHeight: 1.4
    fontFeature: "'tnum' 1"

rounded:
  xs: 2px
  sm: 4px
  md: 6px
  lg: 10px
  full: 9999px

spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  2xl: 64px
  3xl: 96px
  gutter: 24px
  margin: 64px

components:
  page:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.accent-strong}"
    typography: "{typography.body-md}"
  card:
    backgroundColor: "{colors.paper-raised}"
    textColor: "{colors.accent-strong}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  section-alt:
    backgroundColor: "{colors.paper-dim}"
    textColor: "{colors.accent-strong}"
    padding: "{spacing.lg}"
  media-frame:
    backgroundColor: "{colors.paper-dim}"
    rounded: "{rounded.xs}"
    height: 220px
  divider:
    backgroundColor: "{colors.rule}"
    height: 1px
  divider-strong:
    backgroundColor: "{colors.border-strong}"
    height: 1px
  masthead:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-subtle}"
    typography: "{typography.label-md}"
    padding: "{spacing.md}"
  masthead-link-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.tertiary}"
    typography: "{typography.label-md}"
  wordmark:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.paper-raised}"
    typography: "{typography.headline-sm}"
  stat-band:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-pale}"
    typography: "{typography.display}"
    padding: "{spacing.xl}"
  quote-card:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-pale}"
    typography: "{typography.quote}"
    padding: "{spacing.lg}"
  quote-byline:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-muted}"
    typography: "{typography.caption}"
  eyebrow-label:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.accent}"
    typography: "{typography.label-caps}"
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.accent-strong}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
    typography: "{typography.label-lg}"
  button-primary-hover:
    backgroundColor: "{colors.tertiary-strong}"
    textColor: "{colors.paper-raised}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
    typography: "{typography.label-lg}"
  button-secondary-hover:
    backgroundColor: "{colors.primary-pale}"
    textColor: "{colors.primary-strong}"
  chip:
    backgroundColor: "{colors.tertiary-pale}"
    textColor: "{colors.tertiary-strong}"
    rounded: "{rounded.full}"
    padding: "{spacing.xs}"
    typography: "{typography.label-caps}"
  progress-track:
    backgroundColor: "{colors.paper-dim}"
    rounded: "{rounded.full}"
    height: 8px
  progress-fill:
    backgroundColor: "{colors.tertiary}"
    rounded: "{rounded.full}"
    height: 8px
  input:
    backgroundColor: "{colors.paper-raised}"
    textColor: "{colors.accent-strong}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-md}"
  input-error:
    backgroundColor: "{colors.paper-raised}"
    textColor: "{colors.error}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-sm}"
  alert-error:
    backgroundColor: "{colors.error-subtle}"
    textColor: "{colors.error}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-sm}"
  alert-success:
    backgroundColor: "{colors.success-subtle}"
    textColor: "{colors.success}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-sm}"
  alert-warning:
    backgroundColor: "{colors.warning-subtle}"
    textColor: "{colors.warning}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-sm}"
  tooltip:
    backgroundColor: "{colors.accent-strong}"
    textColor: "{colors.paper-raised}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-sm}"
  text-meta:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.meta-text}"
    typography: "{typography.caption}"

  # --- Dark mode: the lesson dashboard ---
  page-dark:
    backgroundColor: "{colors.dark-bg}"
    textColor: "{colors.dark-on-surface}"
    typography: "{typography.body-md}"
  card-dark:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-on-surface}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  overlay-dark:
    backgroundColor: "{colors.dark-surface-overlay}"
    textColor: "{colors.dark-on-surface}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
  divider-dark:
    backgroundColor: "{colors.dark-rule}"
    height: 1px
  divider-dark-strong:
    backgroundColor: "{colors.dark-border-strong}"
    height: 1px
  button-primary-dark:
    backgroundColor: "{colors.dark-tertiary}"
    textColor: "{colors.dark-bg}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
    typography: "{typography.label-lg}"
  button-primary-dark-hover:
    backgroundColor: "{colors.dark-tertiary-strong}"
    textColor: "{colors.dark-bg}"
  button-secondary-dark:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-primary}"
    rounded: "{rounded.md}"
    padding: "{spacing.md}"
    typography: "{typography.label-lg}"
  button-secondary-dark-hover:
    backgroundColor: "{colors.dark-surface-overlay}"
    textColor: "{colors.dark-primary-strong}"
  input-dark:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-on-surface}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-md}"
  alert-error-dark:
    backgroundColor: "{colors.dark-error-subtle}"
    textColor: "{colors.dark-error}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-sm}"
  alert-success-dark:
    backgroundColor: "{colors.dark-success-subtle}"
    textColor: "{colors.dark-success}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-sm}"
  alert-warning-dark:
    backgroundColor: "{colors.dark-warning-subtle}"
    textColor: "{colors.dark-warning}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-sm}"
  tooltip-dark:
    backgroundColor: "{colors.dark-surface-overlay}"
    textColor: "{colors.dark-on-surface}"
    rounded: "{rounded.sm}"
    padding: "{spacing.sm}"
    typography: "{typography.body-sm}"
  text-meta-dark:
    backgroundColor: "{colors.dark-bg}"
    textColor: "{colors.dark-on-surface-meta}"
    typography: "{typography.caption}"
---

# GTS Neurolinguistics

## Overview

This is a course-sales page and a lesson dashboard for an academic neurolinguistics course — the cognitive science of how language lives in the brain — built for curious self-directed learners, not clinicians or linguists-in-training. Someone lands here from a search or a recommendation, needs to trust the institution behind it within the first few seconds, and then needs to feel like a welcome student rather than a sales lead.

The register is **Modern Collegiate**: the gravity of a university course catalog (a serif masthead, hairline rules, syllabus-style curriculum lists) crossed with the clarity and confidence of a well-made ed-tech sales page. It borrows Editorial Print's typographic authority and Archival Institutional's restraint, but refuses their coldness — this should read as a generous mentor with real credentials, not a library reading room. Where the credit-services parent brand is reserved and transactional, this site is allowed to be warm, because teaching is a different relationship than underwriting.

**The inheritance.** The palette is not new. It's the GTS credit-services brand — Oxford navy, walnut ink, ledger-cream paper — carried over unchanged, because a shared visual lineage across the two properties is a trust signal in itself: a prospective student who has seen the parent brand should recognize this as the same institution, not a spun-off startup. What's new is a single signature color, **Brass Seal**, promoted from a hue that already existed in the parent brand's warning palette but had never been given a real job. Here it gets one: it is the entire visual vocabulary of "start," "continue," and "you're making progress."

**The split.** The site has two distinct surfaces with two distinct lighting conditions. The marketing pages — home, curriculum, enrollment — are light-mode only in spirit: a prospectus, read once, in daylight, meant to persuade. The lesson dashboard, where an enrolled student actually watches lectures and works through modules, supports dark mode, because that's genuinely used at night, in bed, headphones in — the same reason a Kindle has a dark mode and a print catalog does not. Dark mode here is a real second design, not an inverted filter.

**The sacrifice.** This direction gives up the stark, almost punitive seriousness of a pure Archival Institutional system — no shadows, no color, no warmth — in exchange for approachability, because a course that promises to demystify something (how language works in your head) should not itself feel intimidating to open. It also gives up some of the frictionless, indigo-and-gradient energy of a generic SaaS landing page, on purpose: this needs to look like it was built by people who take the subject seriously.

## Colors

- **Primary — Oxford Navy (`#0A2463`):** The GTS brand color, unchanged. Carries structure, not interaction — the masthead, the wordmark, section bands that need institutional weight (enrollment stats, testimonials). It is used broadly, the way a school's official color is used on a letterhead, and *never* as a button fill, because that job belongs to Brass Seal. `primary-strong` (`#070D41`) is its pressed/hover step; `primary-subtle` (`#ACCBE1`), `primary-pale` (`#CEE5F2`), and `primary-muted` (`#7C98B3`) are the tint ramp used for text set directly on a navy field.
- **Accent — Walnut (`#3C362A`) and Walnut, near-black (`#261E0F`):** The GTS ink family, also unchanged — the color of library shelving and lecture-hall paneling. `accent-strong` is body text ink everywhere in light mode; plain `accent` is reserved for small structural labels (eyebrow tags like "MODULE 01") that want to read as understated apparatus rather than brand color.
- **Neutral — Ledger Paper (`#F6F3EE`, `#FCFAF6`, `#DBD7D0`):** The GTS paper stock, unchanged: `paper` is the base page, `paper-raised` a half-step lighter for cards and inputs, `paper-dim` a step darker for banded sections (the curriculum list reads like alternating ledger rows). `rule` (`#C1BDB5`) is the decorative hairline; `border-strong` (`#857F74`) is a new, slightly darker step added specifically so input and table borders clear the 3:1 UI-component contrast floor that a purely decorative rule was never built to meet.
- **Tertiary — Brass Seal (`#DB9E38`):** New to this site. The GTS warning ramp already contained a dark, muted brass ink (`#6E4200`) — the color of a brass fixture gone slightly dull. Brass Seal takes that same hue neighborhood and pushes it to full saturation and a mid lightness, the difference between a tarnished plate and a polished one. It is the *sole* driver of interaction — every primary button, the active nav state, progress fill, "new lesson" badges — and nothing else. `tertiary-strong` (`#925100`) is the text-safe darker step for links and hover states; `tertiary-pale` (`#F5E6CE`) is the tint for badge fills.
- **Meta-text — Slate Ink (`#4A5A68`):** Unchanged from GTS. A cool grey-blue against an otherwise warm palette, reserved for timestamps, bylines, and metadata — the marginal note in a different pen.
- **Semantic (error `#A12F2F` / success `#225A31` / warning `#6E4200`, each with a `-subtle` tint):** All unchanged from GTS. They already sit in the brand's family — brick red, deep pine, dulled brass — rather than reading as an imported Bootstrap triad, which is exactly why they were kept as-is instead of re-derived.
- **Dark mode (`dark-*`):** A separate palette for the lesson dashboard, not an inversion. The base (`#15110B`) is a warm near-black in the same hue family as the paper stock — deliberately *not* the blue-tinted slate that most dark UIs default to, since this system has no blue neutral to begin with. Oxford Navy does not survive against it (a dark navy on near-black reads as mud), so `dark-primary` (`#A0C3DA`) — a lightened, desaturated step off the same primary ramp — carries brand-colored links and secondary actions instead; full-strength navy is retired to light mode only. Brass Seal survives the transition essentially intact, lightened slightly (`dark-tertiary` `#E1AD57`) since dark grounds make saturated color read hotter.

Every color in this system traces to a ramp, not a swatch: the ramps were built in OKLCH with lightness stepped on a perceptual curve, chroma tapering toward both ends, and hue bending a few degrees across each ramp (the given `primary` ramp already does this — it drifts from 232° at `primary-pale` to 264° at `primary`, which is why it reads as ink rather than as a gradient). No neutral in the system has R = G = B; every grey carries the same warm ~80–85° hue as the paper stock.

## Typography

Two families, split by job. **Fraunces** carries the voice — display and headlines — and **Source Sans 3** carries the apparatus — body copy, labels, UI, and data. The pairing is a display serif against a neutral humanist sans, the same structure as an academic press pairing a book face with a wayfinding sans, and the two differ enough in classification that nothing about the combination reads as accidental.

**Fraunces** is doing real work beyond decoration: it's a variable serif with genuine `SOFT` and `opsz` axes, and both are set deliberately here. `SOFT` is dialed to a moderate 30–55 across the headline sizes — enough to round off the severity a pure high-contrast serif would carry, which is the single typographic move that makes "collegiate" read as "warm and encouraging" rather than "archival and stern." `WONK` stays at 0; this system wants character, not whimsy. `opsz` tracks the rendered size at every level so strokes stay confident rather than spindly at 96px and don't over-thicken at 26px. The `quote` level uses the italic cut for testimonials and pull-quotes — an Editorial Print convention borrowed wholesale, because a mentor's voice earns an italic aside. Fallback stack: `Fraunces, "Source Serif 4", Georgia, serif`. SIL Open Font License, self-hosted.

**Source Sans 3** carries everything else: body prose, nav, buttons, form labels, captions, and tabular data (`data-md` enables `tnum` so prices and stats align in columns). It was chosen over the more common Inter/Public Sans defaults specifically for its humanist warmth — closer to the "encouraging" end of the neutral-sans spectrum than the colder grotesques, without giving up institutional legibility. Fallback stack: `"Source Sans 3", -apple-system, "Segoe UI", Helvetica, Arial, sans-serif`. SIL Open Font License, self-hosted.

The scale runs 12 → 96px on roughly a 1.333 (perfect-fourth) ratio through the body and label levels, then breaks intentionally at the top: `headline-lg` to `display` is a bigger jump than the ratio alone would produce, because a hero that's merely proportionally large doesn't read as a hero. Tracking is optical throughout — −0.03em at `display` down to neutral at body sizes, +0.08em on the uppercase `label-caps` (used for eyebrow tags and module numbers) so the caps don't look cramped. Line height moves inversely with size: 1.05 at `display`, 1.65 at `body-md`. Only two weights are used across the whole system — 600 for anything Fraunces touches, 400/600 for Source Sans 3 — and no third weight is permitted; hierarchy comes from family, size, and the SOFT axis, not from a crowded weight ladder.

## Layout

A **12-column grid**, 24px gutters, 64px outer margins on desktop, collapsing to a single column under 768px. Body copy — lesson text, the curriculum descriptions — is capped at **68 characters**, because this is read, not scanned.

The layout is asymmetric and flush-left by default, in the Editorial Print tradition: headlines sit against the left edge of the grid with the right margin held open, sometimes for a pull-quote (`quote-card`), sometimes for nothing at all. Nothing on the marketing pages is centered past a single short line — a centered hero is the fastest way for this to read as a generic SaaS template instead of a course catalog.

Spacing runs on an **8px base** (`spacing.xs` through `spacing.3xl`). Density is deliberately uneven and carries real meaning: the curriculum/syllabus list is dense and table-like — a numbered module, a duration, a one-line description, a hairline rule, repeat — because a prospectus's table of contents is supposed to be scannable. The hero, the enrollment CTA band, and testimonial sections are generous by contrast, at `spacing.2xl`–`3xl` rhythm. That density shift is the primary way the page tells you "this part is for browsing" versus "this part is for deciding."

## Elevation & Depth

Depth is carried almost entirely by **tonal layering and hairline rules**, not shadows — consistent with the Editorial/Archival lineage this system draws from. `paper` → `paper-raised` → `paper-dim` is a three-step ladder used to separate page, card, and banded section without a single drop shadow between them. `divider` (`rule`) separates content within a section; `divider-strong` (`border-strong`) marks an actual component boundary, like an input or a table header rule.

The one exception is genuinely floating layers — dropdown menus, the enrollment modal, tooltips — which get a single soft shadow level, warm-tinted from `accent-strong` at low opacity with a top-down light direction (never neutral black). Nothing else in the system casts a shadow; a card sitting on the page is not floating, so it doesn't get one.

In dark mode the elevation logic inverts, as it must: raised surfaces get *lighter*, not shadowed. `dark-bg` → `dark-surface` → `dark-surface-overlay` is the equivalent three-step ladder, and it does the same grouping job the light-mode tonal steps do.

**Motion** is purposeful, not decorative. Overlays (modals, dropdowns, tooltips) enter with a 200ms ease-out fade paired with a small upward shift — the only elements in the system that are "entering" anything, since they're the only ones actually above other content. State changes (button hover, chip selection) are instant to 100ms. `progress-fill` is the one element that animates its own value, easing over 400ms as a lesson completes. Nothing on the marketing pages animates on scroll — headlines, the curriculum list, and testimonials are all present on load. A page that fades everything up as you scroll is the fastest way to make a course catalog feel like a template.

## Shapes

Radius is small and hierarchical, tightening toward the more "documentary" elements and loosening toward the more "friendly" ones: `rounded.xs` (2px) on media frames and thumbnails, keeping imagery reading as content rather than as a UI chrome; `rounded.sm` (4px) on inputs, the sharpest interactive element, matching the precision the parent brand's finance heritage implies; `rounded.md` (6px) on buttons; `rounded.lg` (10px) on cards and overlays, the softest surfaces in the system; `rounded.full` on chips, badges, and progress bars, marking them as a distinct pill-shaped class of object.

Borders are 1px solid `rule` at rest for plain dividers and 1px solid `border-strong` for input and table boundaries, moving to 1px `primary` on focus (2px offset), which clears 3:1 against every light-mode surface. These values are specified here in prose, rather than as component tokens, because the DESIGN.md component schema has no `borderColor` sub-token — the values are normative regardless of where they're written down. In dark mode the same roles are carried by `dark-rule` and `dark-border-strong`.

## Components

**Buttons.** `button-primary` is the only button that uses Brass Seal, and it is the only element on any given screen that should. It's a solid `tertiary` fill with dark `accent-strong` text (7.0:1) — not white text, which fails badly against a mid-lightness gold (2.3:1). Hover darkens to `tertiary-strong` and flips the text to `paper-raised`. `button-secondary` is an outline treatment: `paper` fill, `primary` text and border, for anything that isn't the page's single primary action — "Learn more," "View syllabus." There is no tertiary/ghost button; if a screen needs a third level of emphasis, it has too many competing asks.

**Masthead.** Solid `primary` fill, `primary-subtle` link text at rest, `tertiary` text for the active/current nav item — the one place outside a button where Brass Seal is allowed, because "where you are right now" is a form of progress indication, not decoration. The wordmark sits at full `paper-raised` contrast against the same navy field.

**Stat band and quote card.** Two places `primary` is used as a full-bleed field rather than a small highlight, in the Editorial Print sense — an enrollment-stats band (`display` type in `primary-pale`) and a testimonial pull-quote (`quote` type, same treatment, with `primary-muted` for the attribution line). These are the only two components where navy fills more than a thin structural bar; everywhere else it stays a line, not a field.

**Curriculum / syllabus list.** Not a card grid. A numbered list with `divider` rules between rows, `eyebrow-label` module tags, and `text-meta` for duration — styled like a course catalog's table of contents, because that's a more honest representation of "here is a sequence you'll move through" than a wall of icon cards would be.

**Chips.** Pill-shaped, `tertiary-pale` fill, `tertiary-strong` text, `label-caps` type. Used for lesson status ("New," "In Progress") and nothing else — never as a generic tag, so its meaning stays legible at a glance.

**Progress.** `progress-track` in `paper-dim`, `progress-fill` in solid `tertiary`. Course completion is the one place a filled bar belongs; it should never appear as a decorative loading state elsewhere.

**Inputs.** `paper-raised` fill, `border-strong` outline, `accent-strong` text. Error state switches the border and helper text to `error` and is always paired with an inline written message — never color alone, since roughly 8% of men have some form of red/green color vision deficiency.

**Alerts.** `error`/`success`/`warning`, each a tinted-background/ink pair pulled straight from the brand's existing semantic ramp. These are visually adjacent to Brass Seal in hue (`warning` especially) but distinguished by role and saturation — alerts are always a muted ink-on-tint pair, Brass Seal is always a saturated fill, and the two should never be reachable from the same visual context.

**Tooltip.** The one inversion in the system: `accent-strong` fill with `paper-raised` text, matching the same convention in dark mode with `dark-surface-overlay` and `dark-on-surface`.

**Dark-mode dashboard.** `page-dark`, `card-dark`, and `overlay-dark` mirror their light equivalents role-for-role. `button-primary-dark` keeps Brass Seal as the CTA color (lightened to `dark-tertiary`); `button-secondary-dark` swaps `primary` for `dark-primary`, since raw Oxford Navy is illegible on a near-black ground.

## Do's and Don'ts

- **Do** treat Brass Seal (`tertiary`) as the only color that means "click this." If a second color starts appearing on buttons or active states, the accent has stopped being scarce and stopped being useful.
- **Don't** use `primary` (Oxford Navy) as a button fill. It's the brand's structural color — masthead, wordmark, stat bands — never the interaction color. That job belongs to `tertiary`.
- **Do** keep the marketing pages (home, curriculum, enrollment) light-mode only in spirit, even if the dark tokens exist. Dark mode is scoped to the lesson dashboard, where it has a real usage reason.
- **Don't** invert dark mode from the light palette. Every dark-mode color here was independently checked against its own background; reusing a light-mode hex on a dark ground will produce a contrast failure or a muddy navy.
- **Do** pair every error state with a written message, never color alone.
- **Don't** center headlines or hero copy. The system is flush-left and asymmetric throughout — a centered hero is the fastest way to make this look like a generic SaaS template instead of a course catalog.
- **Do** use the curriculum list as a numbered, rule-divided list, not a card grid. Cards are for the stat band and testimonials — genuinely distinct, comparable objects — not for a sequential syllabus.
- **Don't** add a shadow to anything that isn't a dropdown, modal, or tooltip. Depth elsewhere comes from the paper/paper-raised/paper-dim tonal ladder and hairline rules.
- **Do** cap body and lesson text at roughly 68 characters. Course content is read at length, not skimmed.
- **Don't** add a third font weight, or use Fraunces below headline size, or Source Sans 3 above it. The voice/apparatus split is the whole hierarchy system.
