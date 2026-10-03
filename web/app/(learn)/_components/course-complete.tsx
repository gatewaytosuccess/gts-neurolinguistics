"use client";

import Link from "next/link";

import { useOutline } from "./outline-context";

const linkClass =
  "type-label-md text-dark-primary underline hover:text-dark-primary-strong";

/** Renders nothing until every current lesson is complete. */
export function CourseComplete({ slug }: { slug: string }) {
  const outline = useOutline();
  if (
    outline?.access !== "enrolled" ||
    outline.lesson_count === 0 ||
    outline.completed_lesson_count < outline.lesson_count
  ) {
    return null;
  }

  return (
    <section
      aria-labelledby="course-complete-heading"
      className="card-dark mt-xl"
    >
      <h2 id="course-complete-heading" className="type-headline-sm">
        You&rsquo;ve completed this course
      </h2>
      <div className="mt-md flex flex-wrap gap-x-lg gap-y-sm">
        <Link
          href={`/courses/${encodeURIComponent(slug)}#my-review-heading`}
          className={linkClass}
        >
          Review the course
        </Link>
        <Link href="/dashboard" className={linkClass}>
          Go to your dashboard
        </Link>
      </div>
    </section>
  );
}
