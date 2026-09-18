# Site chrome lives in a `(site)` route group, not the root layout

The masthead renders on every page the app has today, so the root layout is the obvious home for it. It goes in an `app/(site)/` route group instead, and the root layout keeps only the document shell: `<html>`, `<body>`, fonts, `ClerkProvider`, global CSS and base metadata.

A root layout has no opt-out. The only escape is a second root layout, which needs its own `<html>` and `<body>`, and every navigation that crosses between two root layouts is a full page reload rather than a client-side transition. A route group costs a directory and one layout file, and a surface leaves it by sitting beside it.

The lesson viewer is the surface that will take the opt-out. It is a separate dark design, not an inversion of the light one, and the masthead is a solid Oxford Navy field that does not survive against the dark base. It will sit outside `(site)` with its own chrome, and a learner crossing between their dashboard and a lesson should not reload the document to do it.

All four sections currently in the app are inside the group: `(marketing)` nested unchanged so it keeps `SiteFooter` and its generic `<main>`, plus `dashboard`, `admin`, `sign-in` and `sign-up`. Nothing opts out yet.

## Consequences

- **`app/(site)/not-found.tsx` catches `notFound()` thrown inside the group**, which is what `requireAdmin()` throws at a non-admin, so that 404 renders with the masthead. Unmatched URLs across the whole app are not covered by it: that is `app/not-found.tsx`, which doesn't exist yet.
- **Membership is the opt-out decision.** Adding a route means choosing a side of the boundary, and a route added to `app/` by reflex silently loses the masthead.
- **URLs are unaffected.** Route groups don't appear in paths, so the group can be renamed or a section moved out of it without touching a single URL.

## Considered options

- **A second root layout for the lesson viewer.** No group needed, but it duplicates `<html>`, `<body>`, the fonts and `ClerkProvider`, and turns every dashboard-to-lesson navigation into a full page reload.
- **Keep the masthead per-section.** What the app did before: five call sites, each free to decline. Every new section has to remember to render it, and they had already begun to drift.
