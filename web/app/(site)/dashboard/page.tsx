import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";

import {
  fetchCurrentUser,
  fetchEnrollments,
  isAccountSuspended,
  type Enrollment,
} from "@/lib/api";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default async function DashboardPage() {
  const { userId, redirectToSignIn } = await auth();
  if (!userId) return redirectToSignIn();

  const [user, enrollments] = await Promise.allSettled([
    fetchCurrentUser(),
    fetchEnrollments(),
  ]);

  if (
    [user, enrollments].some(
      (result) =>
        result.status === "rejected" && isAccountSuspended(result.reason),
    )
  ) {
    redirect("/suspended");
  }

  const name = user.status === "fulfilled" ? user.value?.name : "";
  // Anything else, an unreachable API included, degrades to a page that says so.
  const courses =
    enrollments.status === "fulfilled" ? (enrollments.value ?? []) : null;
  // Ordered by activity, so the first course is the most recent one if any was started.
  const latest = courses?.[0];

  return (
    <main className="mx-auto w-full max-w-[1200px] flex-1 px-md py-2xl sm:px-margin">
      <p className="type-label-caps text-accent">Your dashboard</p>
      <h1 className="type-headline-md measure mt-md">
        {name ? `Welcome back, ${name}.` : "Welcome back."}
      </h1>

      {courses === null ? (
        <p className="type-body-sm mt-xl rounded-sm bg-warning-subtle px-sm py-sm text-warning">
          The course API is not responding, so your courses are unavailable.
        </p>
      ) : courses.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          {latest?.last_activity_at && latest.continue_lesson_id && (
            <ContinueCard enrollment={latest} />
          )}
          <CourseList enrollments={courses} />
        </>
      )}
    </main>
  );
}

function continueHref(enrollment: Enrollment) {
  const slug = encodeURIComponent(enrollment.course_slug);
  return enrollment.continue_lesson_id
    ? `/learn/${slug}/${encodeURIComponent(enrollment.continue_lesson_id)}`
    : `/learn/${slug}`;
}

function isComplete(enrollment: Enrollment) {
  return (
    enrollment.lesson_count > 0 &&
    enrollment.completed_lesson_count >= enrollment.lesson_count
  );
}

function Thumbnail({ url, className }: { url: string; className: string }) {
  return url ? (
    // CloudFront's domain is a Django setting, so next/image has no host to allowlist.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt=""
      className={`${className} rounded-xs bg-paper-dim object-cover`}
    />
  ) : (
    <div aria-hidden className={`${className} rounded-xs bg-paper-dim`} />
  );
}

function ContinueCard({ enrollment }: { enrollment: Enrollment }) {
  return (
    <section
      aria-labelledby="continue-heading"
      className="mt-xl flex flex-col gap-lg rounded-lg bg-paper-raised p-lg sm:flex-row sm:items-center"
    >
      <Thumbnail
        url={enrollment.course_thumbnail_url}
        className="h-[160px] w-full shrink-0 sm:w-[280px]"
      />
      <div className="min-w-0">
        <p id="continue-heading" className="type-label-caps text-accent">
          Continue where you left off
        </p>
        <h2 className="type-headline-sm mt-sm break-words">
          {enrollment.course_title}
        </h2>
        <p className="type-body-md mt-xs break-words text-meta-text">
          {enrollment.continue_lesson_title}
        </p>
        <Link
          href={continueHref(enrollment)}
          className="button-primary mt-lg inline-block"
        >
          Continue
        </Link>
      </div>
    </section>
  );
}

function CourseList({ enrollments }: { enrollments: Enrollment[] }) {
  return (
    <section aria-labelledby="courses-heading" className="mt-2xl">
      <h2 id="courses-heading" className="type-headline-sm">
        Your courses
      </h2>
      <ul className="mt-md">
        {enrollments.map((enrollment) => (
          <li
            key={enrollment.id}
            className="flex flex-col gap-md border-t border-rule py-md sm:flex-row sm:items-center"
          >
            <Thumbnail
              url={enrollment.course_thumbnail_url}
              className="hidden h-[64px] w-[112px] shrink-0 sm:block"
            />
            <div className="min-w-0 flex-1">
              <Link
                href={`/courses/${encodeURIComponent(enrollment.course_slug)}`}
                className="type-label-lg break-words text-accent-strong hover:text-primary hover:underline"
              >
                {enrollment.course_title}
              </Link>
              <CourseProgress enrollment={enrollment} />
            </div>
            <Link
              href={continueHref(enrollment)}
              className="type-label-md shrink-0 text-tertiary-strong hover:underline"
            >
              Continue
              <span className="sr-only"> {enrollment.course_title}</span>{" "}
              <span aria-hidden>→</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function CourseProgress({ enrollment }: { enrollment: Enrollment }) {
  const { completed_lesson_count: completed, lesson_count: total } = enrollment;

  if (total === 0) {
    return <p className="type-caption mt-xs text-meta-text">No lessons yet</p>;
  }

  if (isComplete(enrollment)) {
    return <p className="type-label-md mt-xs text-success">Completed</p>;
  }

  const label = `${completed} of ${total} ${total === 1 ? "lesson" : "lessons"}`;
  return (
    <div className="mt-xs flex items-center gap-sm">
      <span
        role="progressbar"
        aria-label={`${enrollment.course_title} progress`}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={completed}
        aria-valuetext={`${label} complete`}
        className="h-[6px] w-full max-w-[240px] overflow-hidden rounded-full bg-paper-dim"
      >
        <span
          className="block h-full rounded-full bg-tertiary"
          style={{ width: `${(completed / total) * 100}%` }}
        />
      </span>
      <span className="type-caption whitespace-nowrap tabular-nums text-meta-text">
        {label}
      </span>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="measure mt-xl">
      <p className="type-body-lg text-accent-strong">
        You&rsquo;re not enrolled in anything yet.
      </p>
      <Link href="/courses" className="button-primary mt-lg inline-block">
        Browse courses
      </Link>
    </div>
  );
}
