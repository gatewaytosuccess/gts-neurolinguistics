import Link from "next/link";
import { Show, UserButton } from "@clerk/nextjs";

// Navy is structural only; interactive fills use Brass Seal.
export function Masthead() {
  return (
    <header className="bg-primary">
      <nav className="mx-auto flex max-w-[1200px] items-center justify-between gap-md px-md py-md sm:px-margin">
        <Link href="/" className="type-headline-sm text-paper-raised">
          GTS Neurolinguistics
        </Link>

        <div className="flex items-center gap-md">
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
                <Link href="/sign-up" className="button-primary">
                  Enroll
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
