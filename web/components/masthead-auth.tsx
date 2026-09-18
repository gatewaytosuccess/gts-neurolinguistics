import Link from "next/link";
import { Suspense } from "react";
import { Show, UserButton } from "@clerk/nextjs";

import { MastheadLink } from "@/components/masthead-link";
import { AdminLink } from "@/components/admin-link";

/*
 * Reads the session, so it renders behind the boundary in `Masthead`. The inner
 * boundary is what keeps the admin role lookup from delaying Dashboard and the
 * user button: collapse the two and every signed-in render waits on Django.
 */
export function MastheadAuth() {
  return (
    <Show
      when="signed-in"
      fallback={
        <>
          <Link
            href="/sign-in"
            className="type-label-md whitespace-nowrap text-primary-subtle hover:text-paper-raised"
          >
            Sign in
          </Link>
          <Link href="/sign-up" className="button-primary whitespace-nowrap">
            Get started
          </Link>
        </>
      }
    >
      <MastheadLink href="/dashboard">Dashboard</MastheadLink>
      <Suspense fallback={null}>
        <AdminLink />
      </Suspense>
      <UserButton />
    </Show>
  );
}
