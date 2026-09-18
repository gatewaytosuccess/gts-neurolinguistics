import { auth } from "@clerk/nextjs/server";
import { notFound } from "next/navigation";
import { cache } from "react";

import { ApiError, fetchCurrentUser } from "@/lib/api";

/**
 * Redirects a signed-out visitor to sign-in and 404s anyone whose role isn't
 * `admin`, suspended and banned accounts included. `"unavailable"` when the
 * API can't answer: render no admin content.
 *
 * Only hides pages; every admin endpoint must enforce the role itself.
 */
export const requireAdmin = cache(
  async (): Promise<"admin" | "unavailable"> => {
    const { userId, redirectToSignIn } = await auth();
    if (!userId) return redirectToSignIn();

    let role: string | undefined;
    try {
      role = (await fetchCurrentUser())?.role;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) notFound();
      return "unavailable";
    }

    if (role !== "admin") notFound();
    return "admin";
  },
);
