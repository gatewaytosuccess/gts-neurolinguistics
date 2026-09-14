import type { Metadata } from "next";
import Link from "next/link";

import { fetchCourses, type CourseSummary } from "@/lib/api";

import { formatPrice } from "../_components/landing/format";

export const metadata: Metadata = {
  title: "Courses",
};

export default async function CoursesPage() {
  let courses: CourseSummary[] | null = null;

  try {
    courses = (await fetchCourses()).results;
  } catch {
    // An unreachable API should degrade to a page that says so, not a 500.
  }

  return (
    <div className="mx-auto max-w-[1200px] px-md py-2xl sm:px-margin lg:py-3xl">
      <p className="type-label-caps text-accent">The catalog</p>
      <h1 className="type-headline-md measure mt-md">Courses</h1>

      <div className="mt-xl">
        {courses === null ? (
          <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
            The course API is not responding, so the catalog is unavailable.
          </p>
        ) : courses.length === 0 ? (
          <p className="type-body-lg measure text-accent-strong">
            No courses are published yet. Check back soon.
          </p>
        ) : (
          <ul className="grid gap-gutter md:grid-cols-2 lg:grid-cols-3">
            {courses.map((course) => (
              <li key={course.id}>
                <CourseCard course={course} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function CourseCard({ course }: { course: CourseSummary }) {
  return (
    <Link
      href={`/courses/${course.slug}`}
      className="group flex h-full flex-col rounded-lg bg-paper-raised p-lg"
    >
      {course.thumbnail_url ? (
        // Thumbnails are admin-pasted URLs on any host, so next/image can't allowlist them.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={course.thumbnail_url}
          alt=""
          className="h-[220px] w-full rounded-xs bg-paper-dim object-cover"
        />
      ) : (
        <div aria-hidden className="h-[220px] rounded-xs bg-paper-dim" />
      )}

      <h2 className="type-headline-sm mt-md group-hover:text-primary">
        {course.title}
      </h2>
      <p className="type-body-md mt-sm line-clamp-3">{course.description}</p>
      <Rating average={course.rating_average} count={course.rating_count} />

      <div className="mt-auto pt-lg">
        <div className="border-t border-rule pt-md">
          <span className="type-data-md">
            {formatPrice(course.price_cents)}
          </span>
        </div>
      </div>
    </Link>
  );
}

function Rating({ average, count }: { average: number | null; count: number }) {
  if (average === null || count === 0) {
    return <p className="type-caption mt-sm text-meta-text">No ratings yet</p>;
  }

  return (
    <p className="type-data-md mt-sm text-meta-text">
      <span aria-hidden className="text-tertiary-strong">
        ★{" "}
      </span>
      <span className="sr-only">Rated </span>
      {average.toFixed(1)}
      <span className="type-caption">
        {" "}
        ({count.toLocaleString("en-US")}
        <span className="sr-only"> ratings</span>)
      </span>
    </p>
  );
}
