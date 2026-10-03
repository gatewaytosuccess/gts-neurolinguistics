import Link from "next/link";
import { SignInButton } from "@clerk/nextjs";

export function LockedPanel({
  slug,
  signedIn,
}: {
  slug: string;
  signedIn: boolean;
}) {
  return (
    <section className="card-dark measure">
      <h1 className="type-headline-sm">This lesson is for enrolled learners</h1>
      <p className="type-body-md mt-md text-dark-on-surface-meta">
        Enroll in the course to open every lesson, or try one of its preview
        lessons first.
      </p>
      <div className="mt-lg flex flex-wrap gap-md">
        <Link
          href={`/courses/${encodeURIComponent(slug)}`}
          className="button-primary-dark"
        >
          See the course
        </Link>
        {!signedIn && (
          <SignInButton>
            <button type="button" className="button-secondary-dark">
              Sign in
            </button>
          </SignInButton>
        )}
      </div>
    </section>
  );
}
