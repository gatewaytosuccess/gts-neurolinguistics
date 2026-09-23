import type { Metadata } from "next";
import Form from "next/form";
import Link from "next/link";

import { AutoSubmitSelect } from "@/components/auto-submit-select";
import {
  ApiError,
  fetchAdminCourses,
  isAdminCourseSort,
  isCourseStatus,
  type AdminCourseSort,
  type AdminCourseSummary,
  type CourseStatus,
  type Paginated,
} from "@/lib/api";
import { formatPrice } from "@/lib/format";

import { requireAdmin } from "../_lib/require-admin";
import { STATUS_LABELS, StatusBadge } from "./_components/status-badge";

export const metadata: Metadata = {
  title: "Courses · Admin",
};

const SORT_LABELS: Record<AdminCourseSort, string> = {
  updated: "Recently updated",
  title: "Title",
  created: "Recently created",
};

type Filters = {
  q: string;
  status: CourseStatus | undefined;
  sort: AdminCourseSort;
};

function firstValue(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

function parsePage(value: string): number {
  const page = Number(value);
  return Number.isInteger(page) && page > 1 ? page : 1;
}

function listHref({ q, status, sort }: Filters, page = 1) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  if (sort !== "updated") params.set("sort", sort);
  if (page > 1) params.set("page", String(page));
  return params.size ? `/admin/courses?${params}` : "/admin/courses";
}

export default async function AdminCoursesPage({
  searchParams,
}: PageProps<"/admin/courses">) {
  // Layouts don't re-render on client navigation, and a layout that skips
  // `children` still sends them in the RSC payload.
  if ((await requireAdmin()) !== "admin") return null;

  const params = await searchParams;
  const requestedStatus = firstValue(params.status);
  const requestedSort = firstValue(params.sort);
  const filters: Filters = {
    q: firstValue(params.q).trim(),
    status: isCourseStatus(requestedStatus) ? requestedStatus : undefined,
    sort: isAdminCourseSort(requestedSort) ? requestedSort : "updated",
  };
  const page = parsePage(firstValue(params.page));

  let courses: Paginated<AdminCourseSummary> | "past-last-page" | null;
  try {
    courses = await fetchAdminCourses({ ...filters, page });
  } catch (error) {
    // A stale link can point past the last page once courses are deleted.
    courses =
      error instanceof ApiError && error.status === 404 && page > 1
        ? "past-last-page"
        : null;
  }

  const filtered = Boolean(filters.q || filters.status);

  return (
    <div>
      <p className="type-label-caps text-accent">Admin area</p>
      <div className="mt-md flex flex-wrap items-center justify-between gap-md">
        <h1 className="type-headline-md measure">Courses</h1>
        <Link href="/admin/courses/new" className="button-primary">
          New course
        </Link>
      </div>

      <ListControls filters={filters} />

      <div className="mt-xl">
        {courses === null ? (
          <p className="type-body-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning">
            The course API is not responding, so the course list is unavailable.
          </p>
        ) : courses === "past-last-page" ? (
          <p className="type-body-md">
            There are no courses on this page.{" "}
            <Link href={listHref(filters)} className="text-primary underline">
              Go to the first page
            </Link>
            .
          </p>
        ) : courses.count === 0 && filtered ? (
          <p className="type-body-md">
            No courses match these filters.{" "}
            <Link href="/admin/courses" className="text-primary underline">
              Show every course
            </Link>
            .
          </p>
        ) : courses.count === 0 ? (
          <p className="type-body-md">There are no courses yet.</p>
        ) : (
          <>
            <p className="type-body-sm text-meta-text">
              {courses.count === 1 ? "1 course" : `${courses.count} courses`}
            </p>
            <CourseTable courses={courses.results} />
            <Pagination
              filters={filters}
              page={page}
              hasPrevious={courses.previous !== null}
              hasNext={courses.next !== null}
            />
          </>
        )}
      </div>
    </div>
  );
}

const fieldClassName =
  "type-body-md w-full rounded-sm border border-border-strong bg-paper-raised px-sm py-sm text-accent-strong placeholder:text-meta-text";

function ListControls({ filters }: { filters: Filters }) {
  const { q, status, sort } = filters;

  return (
    // Remounts per URL: uncontrolled fields would keep stale values across client-side back/forward.
    <Form
      key={JSON.stringify([q, status, sort])}
      action="/admin/courses"
      role="search"
      // Stops the browser restoring stale field values on back/forward without JS.
      autoComplete="off"
      className="mt-xl flex flex-col gap-md md:flex-row md:items-end"
    >
      <div className="min-w-0 md:flex-1">
        <label htmlFor="admin-courses-q" className="type-label-md block">
          Search
        </label>
        <input
          id="admin-courses-q"
          type="search"
          name="q"
          defaultValue={q}
          placeholder="Title or slug"
          className={`${fieldClassName} mt-xs`}
        />
      </div>

      <div className="md:w-[160px]">
        <label htmlFor="admin-courses-status" className="type-label-md block">
          Status
        </label>
        <AutoSubmitSelect
          id="admin-courses-status"
          name="status"
          defaultValue={status ?? ""}
          className={`${fieldClassName} mt-xs`}
        >
          <option value="">All</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </AutoSubmitSelect>
      </div>

      <div className="md:w-[200px]">
        <label htmlFor="admin-courses-sort" className="type-label-md block">
          Sort by
        </label>
        <AutoSubmitSelect
          id="admin-courses-sort"
          name="sort"
          defaultValue={sort}
          className={`${fieldClassName} mt-xs`}
        >
          {Object.entries(SORT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </AutoSubmitSelect>
      </div>

      <button type="submit" className="button-secondary">
        Search
      </button>
    </Form>
  );
}

const dateFormat = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

function CourseTable({ courses }: { courses: AdminCourseSummary[] }) {
  const headerClassName = "type-label-md px-sm py-sm text-accent";
  const numericHeaderClassName = `${headerClassName} text-right`;
  const numericCellClassName =
    "type-data-md px-sm py-sm text-right text-meta-text";

  return (
    <div className="mt-sm overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-left">
        <thead>
          <tr className="border-b border-border-strong">
            <th scope="col" className={headerClassName}>
              Course
            </th>
            <th scope="col" className={headerClassName}>
              Status
            </th>
            <th scope="col" className={numericHeaderClassName}>
              Price
            </th>
            <th scope="col" className={numericHeaderClassName}>
              Modules
            </th>
            <th scope="col" className={numericHeaderClassName}>
              Lessons
            </th>
            <th scope="col" className={numericHeaderClassName}>
              Enrolled
            </th>
            <th scope="col" className={numericHeaderClassName}>
              Updated
            </th>
          </tr>
        </thead>
        <tbody>
          {courses.map((course) => (
            <tr key={course.id} className="border-b border-rule align-top">
              <th scope="row" className="px-sm py-sm font-normal">
                <Link
                  href={`/admin/courses/${course.id}`}
                  className="type-label-lg block text-accent-strong hover:text-primary hover:underline"
                >
                  {course.title}
                </Link>
                <span className="type-caption block text-meta-text">
                  {course.slug}
                </span>
              </th>
              <td className="px-sm py-sm">
                <StatusBadge status={course.status} />
              </td>
              <td className={numericCellClassName}>
                {formatPrice(course.price_cents)}
              </td>
              <td className={numericCellClassName}>{course.module_count}</td>
              <td className={numericCellClassName}>{course.lesson_count}</td>
              <td className={numericCellClassName}>
                {course.active_enrollment_count}
              </td>
              <td className={`${numericCellClassName} whitespace-nowrap`}>
                <time dateTime={course.updated_at}>
                  {dateFormat.format(new Date(course.updated_at))}
                </time>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Pagination({
  filters,
  page,
  hasPrevious,
  hasNext,
}: {
  filters: Filters;
  page: number;
  hasPrevious: boolean;
  hasNext: boolean;
}) {
  if (!hasPrevious && !hasNext) return null;

  const linkClassName = "type-label-md text-primary underline";
  const disabledClassName = "type-label-md text-meta-text opacity-60";

  return (
    <nav
      aria-label="Pagination"
      className="mt-lg flex items-center justify-between gap-md"
    >
      {hasPrevious ? (
        <Link href={listHref(filters, page - 1)} className={linkClassName}>
          Previous
        </Link>
      ) : (
        <span className={disabledClassName}>Previous</span>
      )}
      <span className="type-body-sm text-meta-text">Page {page}</span>
      {hasNext ? (
        <Link href={listHref(filters, page + 1)} className={linkClassName}>
          Next
        </Link>
      ) : (
        <span className={disabledClassName}>Next</span>
      )}
    </nav>
  );
}
