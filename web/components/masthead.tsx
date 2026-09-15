import Link from "next/link";
import { Show, UserButton } from "@clerk/nextjs";

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
                <Link
                  href="/sign-up"
                  className="button-primary whitespace-nowrap"
                >
                  Get started
                </Link>
              </>
            }
          >
            <Link
              href="/dashboard"
              className="type-label-md whitespace-nowrap text-primary-subtle hover:text-paper-raised"
            >
              Dashboard
            </Link>
            <UserButton />
          </Show>
        </div>
      </nav>
    </header>
  );
}
