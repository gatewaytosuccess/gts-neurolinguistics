import Link from "next/link";
import { Show, UserButton } from "@clerk/nextjs";

/*
 * Navy is structural here and never an interaction color: the one filled
 * button on the bar is Brass Seal, per DESIGN.md.
 */
export function Masthead() {
  return (
    <header className="bg-primary">
      <nav className="mx-auto flex max-w-[1200px] items-center justify-between px-md py-md sm:px-margin">
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
                  className="type-label-md text-primary-subtle hover:text-paper-raised"
                >
                  Sign in
                </Link>
                <Link
                  href="/sign-up"
                  className="type-label-lg rounded-md bg-tertiary px-md py-sm text-accent-strong hover:bg-tertiary-strong hover:text-paper-raised"
                >
                  Enroll
                </Link>
              </>
            }
          >
            <UserButton />
          </Show>
        </div>
      </nav>
    </header>
  );
}
