import { clerkMiddleware } from "@clerk/nextjs/server";

/*
 * Next 16 renamed `middleware.ts` to `proxy.ts`; the contract is unchanged.
 *
 * This runs Clerk's request handling so `auth()` works in server components,
 * and does no route protection of its own. Clerk deprecated
 * `createRouteMatcher` in Core 3 for a good reason: matching paths here can
 * diverge from how Next actually routes a request, which leaves protected
 * data reachable. Pages and route handlers check their own access instead --
 * see `app/page.tsx`.
 */
export default clerkMiddleware();

export const config = {
  matcher: [
    // Everything except static files and Next internals...
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // ...and always on API routes.
    "/(api|trpc)(.*)",
  ],
};
