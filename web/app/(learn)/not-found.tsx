import Link from "next/link";

// Covers notFound() thrown inside the group; unmatched URLs fall to Next's own page.
export default function LearnNotFound() {
  return (
    <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-2xl sm:px-margin">
      <p className="type-label-caps text-dark-on-surface-meta">404</p>
      <h1 className="type-headline-md measure mt-md">
        This lesson isn&rsquo;t here.
      </h1>
      <p className="type-body-lg measure mt-lg">
        The address may be wrong, or the course may not be open to you.
      </p>

      <div className="mt-xl flex flex-wrap gap-md">
        <Link href="/courses" className="button-primary-dark">
          Browse the courses
        </Link>
        <Link href="/dashboard" className="button-secondary-dark">
          Go to your dashboard
        </Link>
      </div>
    </main>
  );
}
