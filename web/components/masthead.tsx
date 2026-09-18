import Link from "next/link";
import { Suspense } from "react";

import { MastheadAuth } from "@/components/masthead-auth";
import { MastheadLink } from "@/components/masthead-link";

// Navy is structural only; interactive fills use Brass Seal.
export function Masthead() {
  return (
    <header className="bg-primary">
      <nav className="mx-auto flex max-w-[1200px] items-center justify-between gap-md px-md py-md sm:px-margin">
        {/* The full wordmark doesn't fit beside the links below md. */}
        <Link
          href="/"
          aria-label="GTS Neurolinguistics"
          className="type-headline-sm whitespace-nowrap text-paper-raised"
        >
          <span className="md:hidden">GTS</span>
          <span className="hidden md:inline">GTS Neurolinguistics</span>
        </Link>

        <div className="flex items-center gap-sm sm:gap-md">
          <MastheadLink href="/courses">Courses</MastheadLink>
          {/* Wide enough for the signed-out pair, so Courses holds still while the session resolves. */}
          <div className="flex min-w-[184px] items-center justify-end gap-sm sm:gap-md">
            <Suspense fallback={null}>
              <MastheadAuth />
            </Suspense>
          </div>
        </div>
      </nav>
    </header>
  );
}
