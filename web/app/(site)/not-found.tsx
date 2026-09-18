import Link from "next/link";

// Covers notFound() thrown inside the group; unmatched URLs fall to Next's own page.
export default function SiteNotFound() {
  return (
    <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-2xl sm:px-margin">
      <p className="type-label-caps text-accent">404</p>
      <h1 className="type-headline-md measure mt-md">
        This page isn&rsquo;t here.
      </h1>
      <p className="type-body-lg measure mt-lg text-accent-strong">
        The address may be wrong, or the page may not be yours to see.
      </p>

      <div className="mt-xl flex flex-wrap gap-md">
        <Link href="/courses" className="button-primary">
          Browse the courses
        </Link>
        <Link href="/" className="button-secondary">
          Back to the home page
        </Link>
      </div>
    </main>
  );
}
