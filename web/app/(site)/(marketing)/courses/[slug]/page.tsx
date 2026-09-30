import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Markdown } from "@/components/markdown";
import {
  ApiError,
  fetchCourse,
  fetchCurrentUser,
  fetchEnrollments,
  type CourseSummary,
} from "@/lib/api";
import { markdownExcerpt } from "@/lib/markdown-excerpt";

import { InstructorCredentials } from "../../_components/landing/instructor-credentials";
import { landing } from "../../_content/landing";
import { PurchasePanel } from "./_components/purchase-panel";

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
  if (course === null) return { title: "Courses" };

  const description = markdownExcerpt(course.description, 160) || undefined;
  return {
    title: course.title,
    description,
    openGraph: {
      title: course.title,
      description,
      images: course.thumbnail_url ? [course.thumbnail_url] : undefined,
    },
  };
}

export default async function CoursePage({
  params,
}: PageProps<"/courses/[slug]">) {
  const { slug } = await params;
  const [course, [enrollments, currentUser]] = await Promise.all([
    loadCourse(slug),
    Promise.allSettled([fetchEnrollments(), fetchCurrentUser()]),
  ]);

  if (course === null) {
    return (
      <div className="mx-auto max-w-[1200px] px-md py-2xl sm:px-margin lg:py-3xl">
        <AllCoursesLink />
        <p className="type-body-sm mt-xl rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          The course API is not responding, so this course is unavailable.
        </p>
      </div>
    );
  }

  // A failed call (suspended account, API error) reads as not enrolled and not an admin.
  const enrolled =
    enrollments.status === "fulfilled" &&
    (enrollments.value ?? []).some(
      (enrollment) => enrollment.course_id === course.id,
    );
  const isAdmin =
    currentUser.status === "fulfilled" && currentUser.value?.role === "admin";

  return (
    <>
      {/* Under md the panel sits between the header and the body, in source order. */}
      <div className="mx-auto grid max-w-[1200px] gap-xl px-md py-2xl sm:px-margin md:grid-cols-12 md:gap-x-gutter lg:py-3xl">
        <header className="min-w-0 md:col-span-7">
          <AllCoursesLink />
          <p className="type-label-caps mt-xl text-accent">Course</p>
          <h1 className="type-headline-sm mt-sm break-words lg:type-headline-md">
            {course.title}
          </h1>
          <CourseRating
            average={course.rating_average}
            count={course.rating_count}
          />
        </header>

        <PurchasePanel
          course={course}
          enrolled={enrolled}
          isAdmin={isAdmin}
          className="min-w-0 md:sticky md:top-lg md:col-span-5 md:col-start-8 md:row-span-2 md:row-start-1 md:self-start lg:col-span-4 lg:col-start-9"
        />

        <div className="min-w-0 md:col-span-7">
          {course.description && (
            <section aria-labelledby="about-heading">
              <h2 id="about-heading" className="type-headline-sm">
                About this course
              </h2>
              <div className="mt-md break-words">
                <Markdown>{course.description}</Markdown>
              </div>
            </section>
          )}
        </div>
      </div>

      <InstructorCredentials instructor={landing.instructor} />
    </>
  );
}

function AllCoursesLink() {
  return (
    <Link href="/courses" className="type-label-md text-primary underline">
      &larr; All courses
    </Link>
  );
}

function CourseRating({
  average,
  count,
}: {
  average: number | null;
  count: number;
}) {
  if (average === null || count === 0) {
    return <p className="type-caption mt-md text-meta-text">No ratings yet</p>;
  }

  return (
    <p className="type-data-md mt-md text-meta-text">
      <span aria-hidden className="text-tertiary-strong">
        ★{" "}
      </span>
      <span className="sr-only">Rated </span>
      {average.toFixed(1)}
      <span className="type-caption">
        {" "}
        from {count.toLocaleString("en-US")}{" "}
        {count === 1 ? "rating" : "ratings"}
      </span>
    </p>
  );
}
