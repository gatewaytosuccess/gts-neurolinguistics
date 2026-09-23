# Web (Next.js)

The only client for the Django API in `../api`. App Router, Tailwind v4, Clerk
for authentication.

## Setup

```bash
npm install
cp .env.local.example .env.local   # then fill in the Clerk keys
npm run dev                        # http://localhost:3000
```

The Django API must be running too (`../api/README.md`); `API_BASE_URL` points
at it and is **server-only** — the browser never calls Django directly.

## Layout

```
web/
  proxy.ts           Clerk request handling (Next 16's renamed middleware)
  app/
    layout.tsx       fonts + <ClerkProvider>
    globals.css      the DESIGN.md token layer
    (marketing)/     public pages sharing the masthead and footer
      page.tsx       landing page at /; never calls Django
      _components/landing/  one component per landing section
      _content/landing.ts   landing copy as typed data
    dashboard/       signed-in home; reads /api/users/me
    admin/           admin area: shared layout, side nav and access check
    sign-up/[[...sign-up]]/
    sign-in/[[...sign-in]]/
  components/        masthead and its admin link, site footer, auth split panel,
                     auto-submitting select
  lib/
    api.ts           server-side fetch against Django, Clerk token attached
    format.ts        price formatting
    clerk-appearance.ts  DESIGN.md in Clerk's appearance vocabulary
```

## Conventions

**Design tokens.** `../DESIGN.md` is the source of truth and `app/globals.css`
mirrors its names one-for-one: a color called `tertiary` there is
`bg-tertiary` here, and every typography level is a `type-*` utility
(`type-headline-md`, `type-label-caps`) carrying that level's exact size, line
height, tracking and font-variation settings. Don't reach for Tailwind's
default palette or text scale.

Dark mode is deliberately absent. DESIGN.md scopes it to the lesson viewer,
which doesn't exist yet.

**Auth checks belong in pages, not `proxy.ts`.** Clerk deprecated
`createRouteMatcher` in Core 3: path matching in middleware can diverge from
how Next actually routes a request, leaving protected data reachable. Each
page, layout and route handler checks its own access instead.

**Clerk Core 3 removed `<SignedIn>`, `<SignedOut>` and `<Protect>`.** Use
`<Show when="signed-in">`. Your training data probably predates this.

**The platform role comes from Django, not Clerk.** Read it from
`fetchCurrentUser()` (`/api/users/me/`). `<Show when={{ role: "admin" }}>`
checks a Clerk Organization role and doesn't apply. Admin pages call
`requireAdmin()` from `app/(site)/admin/_lib/`.

**Talking to Django.** Use `fetchCurrentUser()` or add a function beside it in
`lib/api.ts`. It runs on the server, attaches the Clerk session token, and
never caches.
