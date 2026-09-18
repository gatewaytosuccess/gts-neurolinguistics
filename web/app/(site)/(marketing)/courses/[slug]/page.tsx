import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ApiError, fetchCourse, type CourseSummary } from "@/lib/api";

import { formatPrice } from "../../_components/landing/format";

/**
 * `null` if the API is unreachable or errors. Throws Next's not-found error on
 * a 404, so it must be awaited in the render path.
 */
async function loadCourse(slug: string): Promise<CourseSummary | null> {
  try {
    return await fetchCourse(slug);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    return null;
  }
}

export async function generateMetadata({
  params,
}: PageProps<"/courses/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const course = await loadCourse(slug);

  return { title: course?.title ?? "Courses" };
}

export default async function CoursePage({
  params,
}: PageProps<"/courses/[slug]">) {
  const { slug } = await params;
  const course = await loadCourse(slug);

  return (
    <div className="mx-auto max-w-[1200px] px-md py-2xl sm:px-margin lg:py-3xl">
      <Link href="/courses" className="type-label-md text-primary underline">
        &larr; All courses
      </Link>

      {course === null ? (
        <p className="type-body-sm mt-xl rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          The course API is not responding, so this course is unavailable.
        </p>
      ) : (
        <article className="mt-xl">
          <p className="type-label-caps text-accent">Coming soon</p>
          <h1 className="type-headline-md measure mt-md">{course.title}</h1>
          {course.description && (
            <p className="type-body-lg measure mt-lg whitespace-pre-line">
              {course.description}
            </p>
          )}
          <p className="type-data-md mt-lg">
            {formatPrice(course.price_cents)}
          </p>
          <p className="type-body-md measure mt-xl border-t border-rule pt-md text-meta-text">
            The full course page is coming soon.
          </p>
        </article>
      )}
    </div>
  );
}
