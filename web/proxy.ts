import { clerkMiddleware } from "@clerk/nextjs/server";

/*
 * Required for `auth()` in server components.
 *
 * Don't protect routes here: proxy path matching can diverge from Next's
 * routing. Each page and route handler checks its own access.
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
