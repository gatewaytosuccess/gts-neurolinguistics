import Link from "next/link";

import type { CourseDetail } from "@/lib/api";
import { formatApproximateDuration, formatPrice } from "@/lib/format";

export type EnrollmentState = "enrolled" | "revoked" | "none";

export function PurchasePanel({
  course,
  enrollment,
  isAdmin,
  checkoutUnavailable,
  className = "",
}: {
  course: CourseDetail;
  enrollment: EnrollmentState;
  isAdmin: boolean;
  /** The last checkout couldn't be started. */
  checkoutUnavailable: boolean;
  className?: string;
}) {
  return (
    <aside
      aria-label={enrollment === "none" ? "Enroll" : "Your enrollment"}
      className={`rounded-lg bg-paper-raised p-lg ${className}`}
    >
      {course.thumbnail_url && (
        // CloudFront's domain is a Django setting, so next/image has no host to allowlist.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={course.thumbnail_url}
          alt=""
          className="mb-lg aspect-video w-full rounded-xs bg-paper-dim object-cover"
        />
      )}

      {enrollment === "enrolled" && (
        <>
          <p className="type-headline-sm">You&rsquo;re enrolled</p>
          <Link
            href={`/learn/${encodeURIComponent(course.slug)}`}
            className="button-primary mt-md"
          >
            Continue
          </Link>
        </>
      )}

      {enrollment === "revoked" && (
        <>
          <p className="type-headline-sm">Your access has ended</p>
          <p className="type-data-md mt-sm">
            {formatPrice(course.price_cents)}
          </p>
          <BuyButton
            slug={course.slug}
            label="Buy again"
            unavailable={checkoutUnavailable}
          />
          <p className="type-caption mt-xs text-meta-text">
            Your progress is saved.
          </p>
          <p className="type-body-sm mt-md">
            Questions?{" "}
            <Link
              href="/contact"
              className="text-primary underline hover:text-primary-strong"
            >
              Contact us
            </Link>
          </p>
        </>
      )}

      {enrollment === "none" && (
        <>
          <p className="type-headline-sm">{formatPrice(course.price_cents)}</p>
          <BuyButton
            slug={course.slug}
            label="Buy now"
            unavailable={checkoutUnavailable}
          />
        </>
      )}

      <CourseStats course={course} />

      {isAdmin && (
        <p className="mt-lg border-t border-rule pt-md">
          <Link
            href={`/admin/courses/${course.id}`}
            className="type-label-md text-primary underline hover:text-primary-strong"
          >
            Edit in admin &rarr;
          </Link>
        </p>
      )}
    </aside>
  );
}

function BuyButton({
  slug,
  label,
  unavailable,
}: {
  slug: string;
  label: string;
  unavailable: boolean;
}) {
  return (
    <>
      {/* Not <Link>: a prefetch of /checkout would start a checkout. */}
      <a
        href={`/checkout?course=${encodeURIComponent(slug)}`}
        className="button-primary mt-md"
      >
        {label}
      </a>
      {unavailable && (
        <p
          role="alert"
          className="type-body-sm mt-sm rounded-sm bg-warning-subtle px-sm py-sm text-warning"
        >
          Payment is unavailable right now. Please try again in a moment.
        </p>
      )}
    </>
  );
}

function CourseStats({ course }: { course: CourseDetail }) {
  const stats: [string, string][] = [
    ["Modules", String(course.module_count)],
    ["Lessons", String(course.lesson_count)],
  ];
  if (course.duration_seconds !== null) {
    stats.push(["Length", formatApproximateDuration(course.duration_seconds)]);
  }
  if (course.preview_lesson_count > 0) {
    stats.push(["Preview lessons", String(course.preview_lesson_count)]);
  }

  return (
    <dl className="mt-lg grid grid-cols-2 gap-x-md gap-y-sm border-t border-rule pt-md">
      {stats.map(([term, value]) => (
        <div key={term}>
          <dt className="type-label-caps text-meta-text">{term}</dt>
          <dd className="type-data-md mt-xs">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
