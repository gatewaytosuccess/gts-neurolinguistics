import type { Metadata } from "next";
import Form from "next/form";
import Link from "next/link";

import {
  fetchCourses,
  isCourseSort,
  type CourseSort,
  type CourseSummary,
} from "@/lib/api";

import { formatPrice } from "../_components/landing/format";
import { SortSelect } from "./_components/sort-select";

export const metadata: Metadata = {
  title: "Courses",
};

const SORT_LABELS: Record<CourseSort, string> = {
  newest: "Newest",
  price_asc: "Price: low to high",
  price_desc: "Price: high to low",
};

type SearchParams = { [key: string]: string | string[] | undefined };

function firstValue(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

export default async function CoursesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const q = firstValue(params.q).trim();
  const requestedSort = firstValue(params.sort);
  const sort = isCourseSort(requestedSort) ? requestedSort : "newest";

  let courses: CourseSummary[] | null = null;

  try {
    courses = (await fetchCourses({ q, sort })).results;
  } catch {
    // An unreachable API should degrade to a page that says so, not a 500.
  }

  return (
    <div className="mx-auto max-w-[1200px] px-md py-2xl sm:px-margin lg:py-3xl">
      <p className="type-label-caps text-accent">The catalog</p>
      <h1 className="type-headline-md measure mt-md">Courses</h1>

      {courses !== null && (courses.length > 0 || q) && (
        <CatalogControls q={q} sort={sort} />
      )}

      <div className="mt-xl">
        {courses === null ? (
          <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
            The course API is not responding, so the catalog is unavailable.
          </p>
        ) : courses.length === 0 && q ? (
          <div className="measure">
            <p className="type-body-lg text-accent-strong">
              No courses match &ldquo;{q}&rdquo;.
            </p>
            <p className="type-body-md mt-sm">
              Try a different word, or{" "}
              <Link href="/courses" className="text-primary underline">
                browse every course
              </Link>
              .
            </p>
          </div>
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

const fieldClassName =
  "type-body-md w-full rounded-sm border border-border-strong bg-paper-raised px-sm py-sm text-accent-strong placeholder:text-meta-text";

function CatalogControls({ q, sort }: { q: string; sort: CourseSort }) {
  return (
    // Remounts per URL: uncontrolled fields would keep stale values across client-side back/forward.
    <Form
      key={JSON.stringify([q, sort])}
      action="/courses"
      role="search"
      // Stops the browser restoring stale field values on back/forward without JS.
      autoComplete="off"
      className="mt-xl flex flex-col gap-md sm:flex-row sm:items-end"
    >
      <div className="min-w-0 sm:flex-1">
        <label htmlFor="catalog-q" className="type-label-md block">
          Search courses
        </label>
        <input
          id="catalog-q"
          type="search"
          name="q"
          defaultValue={q}
          placeholder="Title or topic"
          className={`${fieldClassName} mt-xs`}
        />
      </div>

      <div className="sm:w-[220px]">
        <label htmlFor="catalog-sort" className="type-label-md block">
          Sort by
        </label>
        <SortSelect
          id="catalog-sort"
          name="sort"
          defaultValue={sort}
          className={`${fieldClassName} mt-xs`}
        >
          {Object.entries(SORT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </SortSelect>
      </div>

      <button type="submit" className="button-secondary">
        Search
      </button>
    </Form>
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
