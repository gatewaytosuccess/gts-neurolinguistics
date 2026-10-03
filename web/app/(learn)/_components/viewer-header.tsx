import Link from "next/link";
import { SignInButton, UserButton } from "@clerk/nextjs";

export function ViewerHeader({
  slug,
  courseTitle,
  editHref,
  viewingAsAdmin,
  progress,
  signedIn,
  onOpenCurriculum,
}: {
  slug: string;
  /** Missing when the API couldn't say. */
  courseTitle?: string;
  /** Admins only. */
  editHref?: string;
  /** An admin who isn't enrolled, so nothing they do is recorded. */
  viewingAsAdmin: boolean;
  /** Enrolled learners only. */
  progress?: { completed: number; total: number };
  signedIn: boolean;
  /** Opens the drawer below `lg`; missing when there's no curriculum to show. */
  onOpenCurriculum?: () => void;
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
        {onOpenCurriculum && (
          <button
            type="button"
            onClick={onOpenCurriculum}
            aria-haspopup="dialog"
            aria-label="Open the curriculum"
            className="-mx-xs px-xs py-xs text-dark-primary hover:text-dark-primary-strong lg:hidden"
          >
            <svg
              viewBox="0 0 16 16"
              width={18}
              height={18}
              fill="none"
              stroke="currentColor"
              strokeWidth={1.5}
              strokeLinecap="round"
              aria-hidden
            >
              <path d="M2.5 4h11M2.5 8h11M2.5 12h11" />
            </svg>
          </button>
        )}
        <p className="type-label-lg min-w-0 flex-1 truncate">{courseTitle}</p>
        {progress && progress.total > 0 && <ProgressBar {...progress} />}

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

function ProgressBar({
  completed,
  total,
}: {
  completed: number;
  total: number;
}) {
  const done = completed >= total;
  return (
    <div className="flex shrink-0 items-center gap-sm">
      <span
        className={`type-caption whitespace-nowrap tabular-nums ${
          done
            ? "text-dark-success"
            : "hidden text-dark-on-surface-meta sm:inline"
        }`}
      >
        {done ? "Course complete" : `${completed} of ${total} lessons`}
      </span>
      <span
        role="progressbar"
        aria-label="Course progress"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={completed}
        aria-valuetext={
          done ? "Course complete" : `${completed} of ${total} lessons complete`
        }
        className={`h-[6px] w-16 overflow-hidden rounded-full bg-dark-rule sm:w-32 ${
          done ? "hidden sm:block" : ""
        }`}
      >
        <span
          className={`block h-full rounded-full transition-[width] duration-300 ${
            done ? "bg-dark-success" : "bg-dark-tertiary"
          }`}
          style={{ width: `${(completed / total) * 100}%` }}
        />
      </span>
    </div>
  );
}
