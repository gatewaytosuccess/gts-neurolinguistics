# The masthead reads the role from Django, not the Clerk session

The masthead's Admin link needs the user's role, and Clerk could carry it in `publicMetadata` and the session token for free. We fetch it from `/api/users/me/` instead, in an async link behind `<Suspense>`, because the role is assigned by the platform and lives only on the local `User`: copying it into Clerk would make Clerk a second source of truth written from our side, reversing the mirror in ADR-0001.

## Consequences

- **Every page with the masthead renders per request, the landing page included.** The link calls `auth()`, which makes the route dynamic even for signed-out visitors; only signed-in renders make the Django call.
- **The link fails closed.** A slow API delays only the link; an unreachable API or a suspended account hides it.
- **Pages that already fetch the current user must not fetch it twice.** `fetchCurrentUser` is deduplicated per request.

## Considered options

- **Role in Clerk `publicMetadata`**, read with `<Show when={{ role: "admin" }}>`. No API call, but two stores for the role.
- **Redirect admins from `/dashboard` to `/admin`.** No masthead fetch, but admins would lose My learning and have a different view than regular users.
- **An "Admin area" link on `/dashboard` only.** Reuses that page's existing fetch, but the admin area is reachable from one page.
