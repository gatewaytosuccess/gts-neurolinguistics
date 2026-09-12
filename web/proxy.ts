import { clerkMiddleware } from "@clerk/nextjs/server";

/*
 * Runs Clerk's request handling so `auth()` works in server components.
 *
 * Route protection deliberately does not happen here. Matching paths in a
 * proxy can diverge from how Next actually routes a request, which leaves
 * protected data reachable; each page and route handler checks its own access
 * instead — see `app/page.tsx`.
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
