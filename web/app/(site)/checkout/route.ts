import { auth } from "@clerk/nextjs/server";
import { notFound } from "next/navigation";
import { NextResponse, type NextRequest } from "next/server";

import { ApiError, isAccountSuspended, startCheckout } from "@/lib/api";

/**
 * `/checkout?course=<slug>`: starts a checkout and sends the browser on to
 * Stripe. Signed out, it goes through sign-in and comes back here. Already
 * enrolled goes to the course, a suspended account to `/suspended`, and any
 * other failure back to the course page with `?checkout=unavailable`.
 */
export async function GET(request: NextRequest) {
  const { userId, redirectToSignIn } = await auth();
  if (!userId) return redirectToSignIn();

  const slug = request.nextUrl.searchParams.get("course");
  if (!slug) notFound();

  let destination: string;
  try {
    destination = (await startCheckout(slug)).url;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (isAccountSuspended(error)) {
      destination = "/suspended";
    } else if (error instanceof ApiError && error.status === 409) {
      destination = `/learn/${encodeURIComponent(slug)}`;
    } else {
      destination = `/courses/${encodeURIComponent(slug)}?checkout=unavailable`;
    }
  }
  return NextResponse.redirect(new URL(destination, request.url), 303);
}
