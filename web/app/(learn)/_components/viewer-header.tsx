import Link from "next/link";
import { SignInButton, UserButton } from "@clerk/nextjs";

export function ViewerHeader({
  slug,
  courseTitle,
  editHref,
  viewingAsAdmin,
  signedIn,
}: {
  slug: string;
  /** Missing when the API couldn't say. */
  courseTitle?: string;
  /** Admins only. */
  editHref?: string;
  /** An admin who isn't enrolled, so nothing they do is recorded. */
  viewingAsAdmin: boolean;
  signedIn: boolean;
}) {
  return (
    <header className="border-b border-dark-rule">
      <div className="flex items-center gap-md px-md py-sm sm:px-lg">
        <Link
          href={`/courses/${encodeURIComponent(slug)}`}
          aria-label="Back to the course page"
          className="type-label-lg -mx-sm px-sm py-xs text-dark-primary hover:text-dark-primary-strong"
        >
          &larr;
        </Link>
        <p className="type-label-lg min-w-0 flex-1 truncate">{courseTitle}</p>

        {editHref && (
          <Link
            href={editHref}
            className="type-label-md whitespace-nowrap text-dark-primary hover:text-dark-primary-strong"
          >
            Edit in admin
          </Link>
        )}
        {signedIn ? (
          <UserButton />
        ) : (
          <SignInButton>
            <button
              type="button"
              className="type-label-md whitespace-nowrap text-dark-primary hover:text-dark-primary-strong"
            >
              Sign in
            </button>
          </SignInButton>
        )}
      </div>

      {viewingAsAdmin && (
        <p className="type-caption border-t border-dark-rule bg-dark-surface px-md py-xs text-dark-on-surface-meta sm:px-lg">
          Viewing as admin: progress isn&rsquo;t recorded
        </p>
      )}
    </header>
  );
}
